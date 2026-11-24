# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""Hàm hình học vector hoá (numpy)."""

import numpy as np

TWO_PI = 2.0 * np.pi


def loop_positions(mesh, matrix4=None):
    """Toạ độ từng loop (L,3); nếu có matrix4 thì biến đổi trước."""
    co = mesh.co
    if matrix4 is not None:
        co = co @ matrix4[:3, :3].T + matrix4[:3, 3]
    return co[mesh.loop_vert]


def newell(pl, face_start, face_len):
    """Pháp tuyến đơn vị (F,3) và diện tích (F,) từ toạ độ loop (L,3).

    Mặt suy biến cho pháp tuyến (0,0,1) và diện tích 0.
    """
    n_loops = len(pl)
    if n_loops == 0:
        return np.zeros((0, 3)), np.zeros(0)
    idx = np.arange(n_loops)
    face_of = np.repeat(np.arange(len(face_start)), face_len)
    end = (face_start + face_len)[face_of]
    nxt = np.where(idx + 1 >= end, face_start[face_of], idx + 1)
    cr = np.cross(pl, pl[nxt])
    s = np.add.reduceat(cr, face_start, axis=0)
    ln = np.linalg.norm(s, axis=1)
    ok = ln > 1e-18
    n = np.zeros_like(s)
    n[ok] = s[ok] / ln[ok, None]
    n[~ok] = (0.0, 0.0, 1.0)
    return n, 0.5 * ln


def unwrap_per_face(fr, face_start, face_of_loop):
    """Dồn giá trị góc (đơn vị vòng) về cùng nhánh với loop đầu của mặt."""
    ref = fr[face_start][face_of_loop]
    d = fr - ref
    d = d - (d > 0.5) + (d < -0.5)
    return ref + d


def normalize_rows(a, eps=1e-12):
    ln = np.linalg.norm(a, axis=-1, keepdims=True)
    return a / np.maximum(ln, eps)


def face_points(n):
    """Toạ độ UV chuẩn của mặt n cạnh (kiểu v1): tam giác, vuông, đa giác tròn."""
    if n == 3:
        return np.array([(0, 0), (1, 0), (0, 1)], dtype=float)
    if n == 4:
        return np.array([(0, 0), (1, 0), (1, 1), (0, 1)], dtype=float)
    k = np.arange(n)
    return np.stack([0.5 + 0.5 * np.cos(TWO_PI * k / n),
                     0.5 + 0.5 * np.sin(TWO_PI * k / n)], axis=1)

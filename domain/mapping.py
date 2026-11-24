# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""Sáu kiểu mapping kinh điển (cổng từ UVW Map v1, vector hoá bằng numpy).

Quy ước chung: đầu vào là toạ độ gizmo ĐƠN VỊ (khối [-0.5,0.5]) đã hoán trục theo `align`.
Kết quả UV trong đơn vị tile, tâm gizmo = (0.5, 0.5).
"""

import numpy as np

from .geometry import TWO_PI, face_points, unwrap_per_face


def _planar(x, y, s1, s2, rw, tw, th):
    if rw:
        return x * s1 / tw + 0.5, y * s2 / th + 0.5
    return x + 0.5, y + 0.5


def planar(a, b, sa, sb, rw, tw, th):
    u, v = _planar(a, b, sa, sb, rw, tw, th)
    return np.stack([u, v], axis=1)


def box_legacy(a, b, c, n_al, face_of_loop, sizes, rw, tw, th):
    """Box kiểu v1: mỗi mặt chiếu phẳng theo trục pháp tuyến chính của nó."""
    sa, sb, sc = sizes
    k = np.argmax(np.abs(n_al), axis=1)[face_of_loop]
    neg = n_al[face_of_loop, k] < 0
    x = np.where(k == 2, a, np.where(k == 0, b, a))
    y = np.where(k == 2, b, c)
    s1 = np.where(k == 2, sa, np.where(k == 0, sb, sa))
    s2 = np.where(k == 2, sb, sc)
    x = np.where(neg, -x, x)
    return planar(x, y, s1, s2, rw, tw, th)


def cylindrical(a, b, c, n_al, face_of_loop, face_start, sizes, rw, tw, th, cap):
    sa, sb, sc = sizes
    fr = unwrap_per_face(np.arctan2(b, a) / TWO_PI, face_start, face_of_loop)
    if rw:
        circ = np.pi * (sa + sb) * 0.5
        u = fr * circ / tw
        v = c * sc / th + 0.5
    else:
        u = fr + 0.5
        v = c + 0.5
    uv = np.stack([u, v], axis=1)
    if cap:
        na = np.abs(n_al)
        is_cap = na[:, 2] > np.maximum(na[:, 0], na[:, 1])
        m = is_cap[face_of_loop]
        if m.any():
            uv[m] = planar(a[m], b[m], sa, sb, rw, tw, th)
    return uv


def spherical(a, b, c, face_of_loop, face_start, sizes, rw, tw, th):
    fr = unwrap_per_face(np.arctan2(b, a) / TWO_PI, face_start, face_of_loop)
    lat = np.arctan2(c, np.hypot(a, b))
    if rw:
        r = sum(sizes) / 6.0           # bán kính trung bình (mm)
        u = fr * TWO_PI * r / tw + 0.5
        v = lat * r / th + 0.5
    else:
        u = fr + 0.5
        v = lat / np.pi + 0.5
    return np.stack([u, v], axis=1)


def shrink(a, b, c, sizes, rw, tw, th):
    lat = np.arctan2(c, np.hypot(a, b))
    th_ang = np.arctan2(b, a)
    if rw:
        r = sum(sizes) / 6.0
        rho = (np.pi * 0.5 - lat) * r
        return np.stack([0.5 + rho * np.cos(th_ang) / tw,
                         0.5 + rho * np.sin(th_ang) / th], axis=1)
    rho = (np.pi * 0.5 - lat) / np.pi
    return np.stack([0.5 + rho * np.cos(th_ang), 0.5 + rho * np.sin(th_ang)], axis=1)


def face_unit(face_start, face_len, face_of_loop):
    """Mỗi mặt phủ trọn tile (kiểu v1): tam giác, vuông hoặc đa giác tròn."""
    out = np.zeros((int(face_len.sum()), 2))
    for n in np.unique(face_len):
        faces = np.nonzero(face_len == n)[0]
        pts = face_points(int(n))
        loops = (face_start[faces][:, None] + np.arange(int(n))[None, :]).ravel()
        out[loops] = np.tile(pts, (len(faces), 1))
    return out

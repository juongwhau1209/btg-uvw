# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""Box mapping có hướng vân (Grain Axis).

Với mỗi mặt: e = pháp tuyến hướng ra (đã snap về trục chính),
Gp = G - (e.G)e   (hình chiếu của hướng vân lên mặt phẳng của mặt),
nếu |Gp| ~ 0 (mặt vuông góc với vân = mặt cắt ngang) thì dùng hướng dự phòng F.
U = Gp/|Gp|,  V = e x U  =>  U x V = e, không bao giờ bị lật gương khi nhìn từ ngoài.
Toạ độ (mm): u = P.U , v = P.V  (P đã tính bằng mm).
"""

import numpy as np

from .geometry import normalize_rows

AXES = np.eye(3)
EPS_PARALLEL = 1e-3


def snap_axis_normals(n):
    """Snap pháp tuyến (F,3) về +-trục gần nhất (hoà thì chọn trục đầu, như v1)."""
    k = np.argmax(np.abs(n), axis=1)
    s = np.sign(n[np.arange(len(n)), k])
    s[s == 0] = 1.0
    e = np.zeros_like(n)
    e[np.arange(len(n)), k] = s
    return e, k


def grain_basis(e, grain_vec, fallback_vec):
    """Cặp (U,V) đơn vị (F,3) cho từng mặt từ pháp tuyến e (F,3)."""
    g = np.broadcast_to(np.asarray(grain_vec, float), e.shape)
    f = np.broadcast_to(np.asarray(fallback_vec, float), e.shape)
    gp = g - np.sum(g * e, axis=1, keepdims=True) * e
    fp = f - np.sum(f * e, axis=1, keepdims=True) * e
    bad = np.linalg.norm(gp, axis=1) < EPS_PARALLEL
    u = np.where(bad[:, None], fp, gp)
    u = normalize_rows(u)
    v = np.cross(e, u)
    return u, v


def fallback_for(grain_index):
    """Trục dự phòng khi mặt vuông góc với vân: vân X -> Y ; vân Y/Z -> X."""
    return 1 if grain_index == 0 else 0


def project(pm, face_of_loop, u, v):
    """(u_mm, v_mm) từng loop; pm (L,3) mm; u,v (F,3)."""
    uu = u[face_of_loop]
    vv = v[face_of_loop]
    return np.sum(pm * uu, axis=1), np.sum(pm * vv, axis=1)

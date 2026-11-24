# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""Biến đổi UV sau mapping: lật, xoay, tile, lệch, ngẫu nhiên theo chi tiết."""

import numpy as np


def axes_of(align):
    """(ia, ib, ic): chỉ số trục local cho U, V và hướng chiếu (giống v1)."""
    if align == "Z":
        return 0, 1, 2
    if align == "X":
        return 1, 2, 0
    return 0, 2, 1


def rotate_about_center(u, v, deg, tw, th):
    """Xoay texture quanh tâm tile (0.5,0.5) theo không gian mm (không méo khi tile chữ nhật)."""
    if not deg:
        return u, v
    t = np.radians(deg)
    c, s = np.cos(t), np.sin(t)
    x = (u - 0.5) * tw
    y = (v - 0.5) * th
    xr = x * c + y * s
    yr = -x * s + y * c
    return xr / tw + 0.5, yr / th + 0.5


def part_randoms(n_parts, seed):
    """(n_parts,3) số ngẫu nhiên [0,1) ổn định theo seed: lệch U, lệch V, lật 180."""
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    return rng.random((max(n_parts, 1), 3))


def post_transform(uv, p, tw, th, loop_label=None, n_parts=0):
    """Áp flip -> xoay -> tile -> lệch -> ngẫu nhiên. uv (L,2) trong đơn vị tile."""
    u = uv[:, 0].copy()
    v = uv[:, 1].copy()
    if p.flip_u:
        u = 1.0 - u
    if p.flip_v:
        v = 1.0 - v
    u, v = rotate_about_center(u, v, p.rotation, tw, th)
    if (p.rand_offset or p.rand_rot180) and loop_label is not None and n_parts:
        r = part_randoms(n_parts, p.seed)[loop_label]
        if p.rand_rot180:
            turn = r[:, 2] < 0.5
            u = np.where(turn, 1.0 - u, u)
            v = np.where(turn, 1.0 - v, v)
        u = u * p.tile_u + p.offset_u
        v = v * p.tile_v + p.offset_v
        if p.rand_offset:
            u = u + r[:, 0]
            v = v + r[:, 1]
    else:
        u = u * p.tile_u + p.offset_u
        v = v * p.tile_v + p.offset_v
    return np.stack([u, v], axis=1)

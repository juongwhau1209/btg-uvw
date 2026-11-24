# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""Chia mesh thành "chi tiết" (tấm ván) và tìm khung OBB của từng chi tiết."""

import numpy as np

from .params import PartFrame

COS_SAME_PLANE = np.cos(np.radians(3.0))
PERP_LIMIT = 0.2


# ----------------------------------------------------------------------------
# Chia chi tiết
# ----------------------------------------------------------------------------
def _components(n_verts, a, b):
    """Thành phần liên thông của đồ thị (a-b). Trả gốc (đỉnh nhỏ nhất) từng đỉnh."""
    parent = np.arange(n_verts)
    if len(a) == 0:
        return parent
    while True:
        pa = parent[a]
        pb = parent[b]
        diff = pa != pb
        if not diff.any():
            break
        hi = np.maximum(pa, pb)[diff]
        lo = np.minimum(pa, pb)[diff]
        np.minimum.at(parent, hi, lo)
        while True:
            pp = parent[parent]
            if np.array_equal(pp, parent):
                break
            parent = pp
    return parent


def split_parts(mesh, source):
    """(labels (F,), n_parts). Nhãn đánh số liên tục từ 0."""
    n_faces = mesh.n_faces
    if n_faces == 0:
        return np.zeros(0, dtype=np.int64), 0
    if source == "MATERIAL" and mesh.material_index is not None:
        base = np.asarray(mesh.material_index)
    elif source == "OBJECT":
        base = np.zeros(n_faces, dtype=np.int64)
    else:
        idx = np.arange(mesh.n_loops)
        face_of = mesh.face_of_loop()
        end = (mesh.face_start + mesh.face_len)[face_of]
        nxt = np.where(idx + 1 >= end, mesh.face_start[face_of], idx + 1)
        root = _components(len(mesh.co), mesh.loop_vert, mesh.loop_vert[nxt])
        base = root[mesh.loop_vert[mesh.face_start]]
    uniq, labels = np.unique(base, return_inverse=True)
    return labels.astype(np.int64).ravel(), int(len(uniq))


# ----------------------------------------------------------------------------
# OBB
# ----------------------------------------------------------------------------
def _canonical(v):
    """Đổi dấu để thành phần lớn nhất (theo trị tuyệt đối) dương -> ổn định giữa các chi tiết."""
    k = int(np.argmax(np.abs(v)))
    return -v if v[k] < 0 else v


def _pca_axes(pts):
    c = pts - pts.mean(axis=0)
    cov = c.T @ c / max(len(c), 1)
    w, vec = np.linalg.eigh(cov)
    return vec[:, ::-1].T  # hàng = trục, phương sai giảm dần


def _refine(nrm, area, cand):
    """Trung bình có trọng số diện tích các pháp tuyến cùng phương với cand."""
    d = nrm @ cand
    m = np.abs(d) > COS_SAME_PLANE
    if not m.any():
        return cand
    acc = np.sum((np.sign(d[m]) * area[m])[:, None] * nrm[m], axis=0)
    ln = np.linalg.norm(acc)
    return acc / ln if ln > 1e-12 else cand


def _normal_groups(nrm, area):
    """Nhóm pháp tuyến (bỏ dấu) theo ô ~1.4 độ -> (hướng đại diện, tổng diện tích)."""
    idx = np.argmax(np.abs(nrm), axis=1)
    sgn = np.sign(nrm[np.arange(len(nrm)), idx])
    sgn[sgn == 0] = 1.0
    nc = nrm * sgn[:, None]
    key = np.round(nc * 40).astype(np.int64)
    uniq, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.ravel()
    w = np.bincount(inv, weights=area, minlength=len(uniq))
    gv = np.stack([np.bincount(inv, weights=area * nc[:, c], minlength=len(uniq))
                   for c in range(3)], axis=1)
    ln = np.linalg.norm(gv, axis=1)
    ok = ln > 1e-12
    gn = np.zeros_like(gv)
    gn[ok] = gv[ok] / ln[ok, None]
    return gn, w


def obb_axes(nrm, area, pts):
    """3 trục trực giao (hàng) của chi tiết từ pháp tuyến có trọng số + điểm.

    Hộp/ván: trục = các hướng pháp tuyến chiếm nhiều diện tích nhất.
    Chi tiết cong/không rõ: lùi về PCA toạ độ đỉnh.
    """
    total = float(area.sum())
    if len(nrm) == 0 or total <= 1e-12:
        return _pca_axes(pts)
    gn, w = _normal_groups(nrm, area)
    best = int(np.argmax(w))
    a1 = _refine(nrm, area, gn[best])
    # trục 2: nhóm lớn nhất vuông góc a1
    perp = np.abs(gn @ a1) < PERP_LIMIT
    perp &= w > 0
    a2 = None
    if perp.any():
        cand = int(np.argmax(np.where(perp, w, -1.0)))
        a2 = _refine(nrm, area, gn[cand])
        a2 = a2 - (a2 @ a1) * a1
        ln = np.linalg.norm(a2)
        a2 = a2 / ln if ln > 1e-6 else None
    if a2 is None:
        # PCA: hướng vuông góc a1 nhất
        pca = _pca_axes(pts)
        proj = pca - (pca @ a1)[:, None] * a1[None, :]
        lens = np.linalg.norm(proj, axis=1)
        j = int(np.argmax(lens))
        if lens[j] < 1e-6:
            tmp = np.array([1.0, 0, 0]) if abs(a1[0]) < 0.9 else np.array([0, 1.0, 0])
            a2 = np.cross(a1, tmp)
        else:
            a2 = proj[j]
        a2 = a2 / np.linalg.norm(a2)
    a1 = _canonical(a1)
    a2 = _canonical(a2)
    a3 = np.cross(a1, a2)
    return np.stack([a1, a2, a3])


def part_frames(co_mm, mesh, labels, n_parts, nrm_mm, area_mm):
    """Danh sách PartFrame (toạ độ object-mm), trục sắp xếp dài -> ngắn, hệ tay phải."""
    frames = []
    if n_parts == 0:
        return frames
    face_of = mesh.face_of_loop()
    loop_label = labels[face_of]
    lorder = np.argsort(loop_label, kind="stable")
    lb = np.searchsorted(loop_label[lorder], np.arange(n_parts + 1))
    forder = np.argsort(labels, kind="stable")
    fb = np.searchsorted(labels[forder], np.arange(n_parts + 1))
    for p in range(n_parts):
        loops = lorder[lb[p]:lb[p + 1]]
        faces = forder[fb[p]:fb[p + 1]]
        pts = co_mm[mesh.loop_vert[loops]]
        axes = obb_axes(nrm_mm[faces], area_mm[faces], pts)
        proj = pts @ axes.T
        mn = proj.min(axis=0)
        mx = proj.max(axis=0)
        ext = mx - mn
        order = np.argsort(-ext, kind="stable")
        axes = axes[order]
        ext = ext[order]
        mn = mn[order]
        mx = mx[order]
        # tay phải: trục 3 = a1 x a2 (ngắn nhất)
        if np.linalg.det(axes) < 0:
            axes[2] = -axes[2]
            mn[2], mx[2] = -mx[2], -mn[2]
        center = ((mn + mx) * 0.5) @ axes
        frames.append(PartFrame(label=p, center=center, axes=axes, extent=np.maximum(ext, 1e-3)))
    return frames

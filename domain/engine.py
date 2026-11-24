# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""Engine UVW: MeshData + MapParams + GizmoFrame -> UV từng loop."""

import numpy as np

from . import grain as grain_mod
from . import mapping as mp
from . import parts as parts_mod
from .geometry import newell, normalize_rows
from .params import MapResult
from .uvxform import axes_of, post_transform

AXIS_INDEX = {"X": 0, "Y": 1, "Z": 2}
PART_GRAIN_INDEX = {"LONGEST": (0, 1), "MIDDLE": (1, 0), "SHORTEST": (2, 0)}


def select_faces(mesh, p):
    """Mặt nào thuộc quyền gizmo này (xem scope/uid/mask)."""
    sel = np.ones(mesh.n_faces, dtype=bool)
    owner = mesh.face_owner
    if owner is not None:
        if p.scope == "OWNED":
            sel &= owner == p.uid
        else:
            sel &= (owner == 0) | (owner == p.uid)
    elif p.scope == "OWNED":
        sel[:] = False
    if mesh.face_mask is not None:
        sel &= mesh.face_mask
    return sel


def _tex_size(p):
    if p.real_world:
        return max(float(p.tex_u), 1.0), max(float(p.tex_v), 1.0)
    return 1.0, 1.0


def compute(mesh, p, frame):
    """Tính UV cho mọi loop; chỉ những loop thuộc `loop_sel` nên được ghi."""
    n_faces, n_loops = mesh.n_faces, mesh.n_loops
    face_sel = select_faces(mesh, p)
    if n_faces == 0 or n_loops == 0:
        return MapResult(np.zeros((n_loops, 2)), face_sel, np.zeros(n_loops, bool))
    fol = mesh.face_of_loop()
    tw, th = _tex_size(p)

    labels, n_parts = None, 0
    if p.mapping == "PARTS" or p.rand_offset or p.rand_rot180:
        labels, n_parts = parts_mod.split_parts(mesh, p.part_source)

    frames = []
    if p.mapping == "PARTS":
        uv, frames = _map_parts(mesh, p, frame, fol, labels, n_parts, tw, th)
    else:
        uv = _map_gizmo(mesh, p, frame, fol, tw, th)

    loop_label = labels[fol] if labels is not None else None
    uv = post_transform(uv, p, tw, th, loop_label, n_parts)
    return MapResult(uv, face_sel, face_sel[fol], labels, n_parts, frames)


# ----------------------------------------------------------------------------
# Chế độ gizmo
# ----------------------------------------------------------------------------
def _map_gizmo(mesh, p, frame, fol, tw, th):
    binv = frame.obj_to_gizmo
    size = np.maximum(np.abs(frame.size_mm), 1e-3)
    pg_v = mesh.co @ binv[:3, :3].T + binv[:3, 3]      # (V,3) toạ độ gizmo đơn vị
    pg = pg_v[mesh.loop_vert]
    rw = p.real_world
    mode = p.mapping

    if mode == "BOX" and p.grain != "LEGACY":
        return _box_grain(mesh, p, frame, pg, size, fol, tw, th)
    if mode == "FACE" and rw:
        return _face_projected(mesh, p, frame, pg, size, fol, tw, th)
    if mode == "FACE":
        return mp.face_unit(mesh.face_start, mesh.face_len, fol)

    ia, ib, ic = axes_of(p.align)
    pa = pg[:, [ia, ib, ic]].copy()
    sizes = (size[ia], size[ib], size[ic])
    if p.flip_w:
        pa[:, 0] = -pa[:, 0]
        pa[:, 2] = -pa[:, 2]
    a, b, c = pa[:, 0], pa[:, 1], pa[:, 2]

    if mode == "PLANAR":
        return mp.planar(a, b, sizes[0], sizes[1], rw, tw, th)
    if mode == "BOX":   # LEGACY
        n_al = _normals_gizmo_aligned(mesh, binv, (ia, ib, ic), p.flip_w)
        return mp.box_legacy(a, b, c, n_al, fol, sizes, rw, tw, th)
    if mode == "CYLINDRICAL":
        n_al = _normals_gizmo_aligned(mesh, binv, (ia, ib, ic), False)
        return mp.cylindrical(a, b, c, n_al, fol, mesh.face_start, sizes, rw, tw, th, p.cap)
    if mode == "SPHERICAL":
        return mp.spherical(a, b, c, fol, mesh.face_start, sizes, rw, tw, th)
    if mode == "SHRINK":
        return mp.shrink(a, b, c, sizes, rw, tw, th)
    raise ValueError("Kiểu mapping không hợp lệ: %r" % mode)


def _object_normals(mesh):
    n, _ = newell(mesh.co[mesh.loop_vert], mesh.face_start, mesh.face_len)
    return n


def _normals_gizmo_aligned(mesh, binv, perm, flip_w):
    """Pháp tuyến object -> gizmo (N = B^T như v1) rồi hoán trục theo align."""
    b3 = np.linalg.inv(binv[:3, :3])
    n = _object_normals(mesh) @ b3          # hàng: n^T B  = (B^T n)^T
    n = n[:, list(perm)]
    if flip_w:
        n[:, 0] = -n[:, 0]
        n[:, 2] = -n[:, 2]
    return n


def _normals_gizmo_mm(mesh, binv, size):
    """Pháp tuyến đơn vị trong không gian gizmo-mm (nghịch đảo chuyển vị)."""
    m = np.diag(size) @ binv[:3, :3]
    n = _object_normals(mesh) @ np.linalg.inv(m)   # (M^-T n)^T = n^T M^-1
    return normalize_rows(n)


def _box_grain(mesh, p, frame, pg, size, fol, tw, th):
    gi = AXIS_INDEX.get(p.grain, 0)
    fi = grain_mod.fallback_for(gi)
    n_mm = _normals_gizmo_mm(mesh, frame.obj_to_gizmo, size)
    e, _ = grain_mod.snap_axis_normals(n_mm)
    u_ax, v_ax = grain_mod.grain_basis(e, grain_mod.AXES[gi], grain_mod.AXES[fi])
    pm = pg * size
    u_mm, v_mm = grain_mod.project(pm, fol, u_ax, v_ax)
    if p.real_world:
        return np.stack([u_mm / tw + 0.5, v_mm / th + 0.5], axis=1)
    su = np.sum(np.abs(u_ax) * size, axis=1)[fol]
    sv = np.sum(np.abs(v_ax) * size, axis=1)[fol]
    return np.stack([u_mm / su + 0.5, v_mm / sv + 0.5], axis=1)


def _face_projected(mesh, p, frame, pg, size, fol, tw, th):
    """FACE real-world: chiếu từng mặt theo pháp tuyến thật của nó, vân theo trục gizmo."""
    gi = AXIS_INDEX.get(p.grain, 0) if p.grain != "LEGACY" else 0
    fi = grain_mod.fallback_for(gi)
    e = _normals_gizmo_mm(mesh, frame.obj_to_gizmo, size)
    u_ax, v_ax = grain_mod.grain_basis(e, grain_mod.AXES[gi], grain_mod.AXES[fi])
    u_mm, v_mm = grain_mod.project(pg * size, fol, u_ax, v_ax)
    return np.stack([u_mm / tw + 0.5, v_mm / th + 0.5], axis=1)


# ----------------------------------------------------------------------------
# Chế độ PARTS (tự động theo chi tiết)
# ----------------------------------------------------------------------------
def _map_parts(mesh, p, frame, fol, labels, n_parts, tw, th):
    scale = np.maximum(np.abs(frame.obj_scale_mm), 1e-6)
    co_mm = mesh.co * scale
    pl = co_mm[mesh.loop_vert]
    nrm, area = newell(pl, mesh.face_start, mesh.face_len)
    frames = parts_mod.part_frames(co_mm, mesh, labels, n_parts, nrm, area)
    gi, fi = PART_GRAIN_INDEX.get(p.part_grain, (0, 1))

    axes = np.stack([f.axes for f in frames])             # (P,3,3)
    center = np.stack([f.center for f in frames])         # (P,3)
    extent = np.stack([f.extent for f in frames])         # (P,3)
    for f in frames:
        f.grain_axis = gi

    lab_l = labels[fol]
    q = np.einsum("lij,lj->li", axes[lab_l], pl - center[lab_l])    # toạ độ cục bộ mm
    n_loc = np.einsum("fij,fj->fi", axes[labels], nrm)
    e, _ = grain_mod.snap_axis_normals(n_loc)
    u_ax, v_ax = grain_mod.grain_basis(e, grain_mod.AXES[gi], grain_mod.AXES[fi])
    u_mm, v_mm = grain_mod.project(q, fol, u_ax, v_ax)
    if p.real_world:
        uv = np.stack([u_mm / tw + 0.5, v_mm / th + 0.5], axis=1)
    else:
        ext_l = extent[lab_l]
        su = np.sum(np.abs(u_ax)[fol] * ext_l, axis=1)
        sv = np.sum(np.abs(v_ax)[fol] * ext_l, axis=1)
        uv = np.stack([u_mm / su + 0.5, v_mm / sv + 0.5], axis=1)
    return uv, frames

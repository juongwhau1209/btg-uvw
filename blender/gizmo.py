# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""Gizmo (Empty hình hộp) — toán ma trận, tìm kiếm, tạo, Fit, và dựng tham số cho engine."""

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

from ..core import product
from ..core.errors import GizmoError
from ..core.units import MIN_MM, unit_mm
from ..domain.params import GizmoFrame, MapParams


def scene_unit_mm(scene=None):
    scene = scene or bpy.context.scene
    return unit_mm(scene.unit_settings.scale_length)


def gizmo_world(g):
    """Ma trận world của gizmo, tính trực tiếp để luôn mới nhất (kể cả trong handler)."""
    m = g.matrix_basis.copy()
    if g.parent is not None:
        m = g.parent.matrix_world @ g.matrix_parent_inverse @ m
    return m


def rel_matrix(g, t):
    return t.matrix_world.inverted_safe() @ gizmo_world(g)


def is_gizmo(ob):
    return ob is not None and ob.type == "EMPTY" and ob.btg_uvw.is_gizmo


def gizmos_of(scene, target):
    return [g for g in scene.objects if is_gizmo(g) and g.btg_uvw.target == target]


def all_gizmos(scene):
    return [g for g in scene.objects if is_gizmo(g)]


def find_gizmo(context):
    """Gizmo đang làm việc: Empty đang chọn, hoặc gizmo đầu tiên của mesh đang chọn."""
    o = context.active_object
    if o is None:
        return None
    if is_gizmo(o):
        return o
    if o.type == "MESH":
        found = gizmos_of(context.scene, o)
        if found:
            return found[0]
    return None


def next_uid(target):
    used = {g.btg_uvw.uid for g in bpy.data.objects if is_gizmo(g) and g.btg_uvw.target == target}
    uid = 1
    while uid in used:
        uid += 1
    return uid


# ----------------------------------------------------------------------------
# Cầu nối sang engine
# ----------------------------------------------------------------------------
def params_of(g):
    p = g.btg_uvw
    return MapParams(
        mapping=p.mapping, align=p.align, cap=p.cap, grain=p.grain,
        flip_u=p.flip_u, flip_v=p.flip_v, flip_w=p.flip_w,
        tile_u=p.tile_u, tile_v=p.tile_v, offset_u=p.offset_u, offset_v=p.offset_v,
        rotation=p.rotation, real_world=p.real_world, tex_u=p.tex_u, tex_v=p.tex_v,
        part_source=p.part_source, part_grain=p.part_grain,
        rand_offset=p.rand_offset, rand_rot180=p.rand_rot180, seed=p.seed,
        scope=p.scope, uid=p.uid)


def build_frame(g, t, scene=None):
    G = gizmo_world(g)
    B = t.matrix_world.inverted_safe() @ G
    try:
        binv = B.inverted()
    except ValueError:
        raise GizmoError("Ma trận gizmo suy biến (scale = 0).")
    um = scene_unit_mm(scene)
    size = np.maximum(np.abs(np.array(G.to_scale())) * um, MIN_MM)
    oscale = np.maximum(np.abs(np.array(t.matrix_world.to_scale())) * um, MIN_MM)
    return GizmoFrame(np.array(binv, dtype=np.float64), size, oscale)


def transform_key(g, t, scene=None):
    """Khoá băm của mọi thứ trong biến đổi ảnh hưởng UV (để phát hiện gizmo/object đổi)."""
    B = rel_matrix(g, t)
    um = scene_unit_mm(scene)
    sz = gizmo_world(g).to_scale()
    ts = t.matrix_world.to_scale()
    vals = [B[i][j] for i in range(4) for j in range(4)]
    vals += [abs(s) * um for s in sz] + [abs(s) * um for s in ts]
    return tuple(round(v, 4) for v in vals)


# ----------------------------------------------------------------------------
# Tạo / Fit
# ----------------------------------------------------------------------------
def fit_gizmo(g, scale=True, reset=False, use_selection=True):
    p = g.btg_uvw
    t = p.target
    if t is None:
        return False
    edit = t.mode == "EDIT"
    if edit:
        t.update_from_editmode()
    me = t.data
    n = len(me.vertices)
    if n == 0:
        return False
    co = np.empty(n * 3, dtype=np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(n, 3).astype(np.float64)
    if edit and use_selection:
        sel = np.empty(n, dtype=bool)
        me.vertices.foreach_get("select", sel)
        if sel.any():
            co = co[sel]
    B = t.matrix_world.inverted_safe() @ gizmo_world(g)
    loc, rot, sc = B.decompose()
    if reset:
        rot = Quaternion()
    R = rot.to_matrix()
    Rinv = np.array(R.inverted())
    proj = co @ Rinv.T
    mn, mx = proj.min(axis=0), proj.max(axis=0)
    center = R @ Vector(((mn + mx) * 0.5).tolist())
    if scale or reset:
        sc = Vector([max(float(mx[i] - mn[i]), 1e-4) for i in range(3)])
    g.matrix_world = t.matrix_world @ Matrix.LocRotScale(center, rot, sc)
    return True


def new_gizmo(context, target, mapping="BOX"):
    """Tạo Empty gizmo ôm sát target, gắn parent để đi theo object."""
    g = bpy.data.objects.new(product.GIZMO_PREFIX + target.name, None)
    g.empty_display_type = "CUBE"
    g.empty_display_size = 0.5
    coll = target.users_collection[0] if target.users_collection else context.collection
    coll.objects.link(g)
    g.matrix_world = target.matrix_world.copy()
    g.parent = target
    g.matrix_parent_inverse = target.matrix_world.inverted_safe()
    p = g.btg_uvw
    p.mapping = mapping
    p.target = target
    p.uid = next_uid(target)
    fit_gizmo(g, use_selection=False)
    p.is_gizmo = True
    return g

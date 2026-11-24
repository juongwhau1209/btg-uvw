# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""Đọc/ghi mesh <-> mảng numpy.

Object Mode : foreach_get/foreach_set (nhanh). Edit Mode : bmesh.
Mỗi chỗ phụ thuộc phiên bản API (4.2 -> 5.x) đều có đường lùi (fallback) để không chết.
"""

import bmesh
import numpy as np

from ..core import product
from ..core.errors import MeshError
from ..domain.params import MeshData


# ----------------------------------------------------------------------------
# Đọc
# ----------------------------------------------------------------------------
def _fget(coll, attr, dtype, n, width=1):
    arr = np.empty(n * width, dtype=dtype)
    coll.foreach_get(attr, arr)
    return arr.reshape(n, width) if width > 1 else arr


def read_object(obj):
    """MeshData từ mesh dữ liệu gốc (Object Mode)."""
    me = obj.data
    nv, nl, nf = len(me.vertices), len(me.loops), len(me.polygons)
    if nv == 0 or nf == 0:
        raise MeshError("Mesh rỗng.")
    try:
        co = _fget(me.vertices, "co", np.float32, nv, 3).astype(np.float64)
        loop_vert = _fget(me.loops, "vertex_index", np.int32, nl).astype(np.int64)
        fstart = _fget(me.polygons, "loop_start", np.int32, nf).astype(np.int64)
        flen = _fget(me.polygons, "loop_total", np.int32, nf).astype(np.int64)
    except (TypeError, RuntimeError, AttributeError):
        return _read_via_bmesh(me)
    mat = None
    try:
        mat = _fget(me.polygons, "material_index", np.int32, nf).astype(np.int64)
    except (TypeError, RuntimeError, AttributeError):
        pass
    owner = None
    attr = me.attributes.get(product.FACE_OWNER_ATTR)
    if attr is not None and attr.domain == "FACE" and attr.data_type == "INT":
        owner = _fget(attr.data, "value", np.int32, nf).astype(np.int64)
    return MeshData(co, loop_vert, fstart, flen, mat, owner, None)


def _read_via_bmesh(me):
    bm = bmesh.new()
    try:
        bm.from_mesh(me)
        return _from_bm(bm, False)
    finally:
        bm.free()


def _from_bm(bm, only_selected):
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    co = np.array([v.co[:] for v in bm.verts], dtype=np.float64).reshape(-1, 3)
    loop_vert, flen, mat, mask = [], [], [], []
    for f in bm.faces:
        vs = [l.vert.index for l in f.loops]
        loop_vert.extend(vs)
        flen.append(len(vs))
        mat.append(f.material_index)
        mask.append(f.select)
    flen = np.array(flen, dtype=np.int64)
    fstart = np.concatenate([[0], np.cumsum(flen)[:-1]]).astype(np.int64) if len(flen) else flen
    owner = None
    layer = bm.faces.layers.int.get(product.FACE_OWNER_ATTR)
    if layer is not None:
        owner = np.array([f[layer] for f in bm.faces], dtype=np.int64)
    return MeshData(co, np.array(loop_vert, dtype=np.int64), fstart, flen,
                    np.array(mat, dtype=np.int64), owner,
                    np.array(mask, dtype=bool) if only_selected else None)


def read_edit(obj, only_selected=False):
    """MeshData từ bmesh đang chỉnh (Edit Mode). Chỉ số loop = thứ tự duyệt face -> loops."""
    bm = bmesh.from_edit_mesh(obj.data)
    if len(bm.faces) == 0:
        raise MeshError("Mesh rỗng.")
    return _from_bm(bm, only_selected)


def read(obj, only_selected=False):
    if obj.mode == "EDIT":
        return read_edit(obj, only_selected)
    return read_object(obj)


# ----------------------------------------------------------------------------
# Ghi UV
# ----------------------------------------------------------------------------
def _uv_layer(me, name):
    layer = me.uv_layers.get(name) if name else me.uv_layers.active
    if layer is None:
        layer = me.uv_layers.new(name=name or "UVMap")
    return layer


def _uv_read(layer, n):
    cur = np.empty(n * 2, dtype=np.float32)
    try:
        layer.uv.foreach_get("vector", cur)
    except (AttributeError, TypeError, RuntimeError):
        layer.data.foreach_get("uv", cur)
    return cur.reshape(n, 2)


def _uv_write(layer, arr):
    flat = np.ascontiguousarray(arr, dtype=np.float32).ravel()
    try:
        layer.uv.foreach_set("vector", flat)
    except (AttributeError, TypeError, RuntimeError):
        layer.data.foreach_set("uv", flat)


def write_uv_object(obj, uv_name, uv, loop_sel):
    me = obj.data
    n = len(me.loops)
    if len(uv) != n:
        raise MeshError("Số loop thay đổi (%d != %d); hãy áp dụng lại." % (len(uv), n))
    layer = _uv_layer(me, uv_name)
    cur = _uv_read(layer, n)
    cur[loop_sel] = uv[loop_sel]
    _uv_write(layer, cur)
    me.update()


def write_uv_edit(obj, uv_name, uv, loop_sel):
    me = obj.data
    bm = bmesh.from_edit_mesh(me)
    layer = bm.loops.layers.uv.get(uv_name) if uv_name else bm.loops.layers.uv.active
    if layer is None:
        layer = bm.loops.layers.uv.new(uv_name or "UVMap")
    i = 0
    for f in bm.faces:
        for l in f.loops:
            if loop_sel[i]:
                l[layer].uv = (float(uv[i, 0]), float(uv[i, 1]))
            i += 1
    if i != len(uv):
        raise MeshError("Mesh đổi trong lúc tính UV; hãy áp dụng lại.")
    bmesh.update_edit_mesh(me, loop_triangles=False, destructive=False)


def write_uv(obj, uv_name, uv, loop_sel):
    if obj.mode == "EDIT":
        write_uv_edit(obj, uv_name, uv, loop_sel)
    else:
        write_uv_object(obj, uv_name, uv, loop_sel)


# ----------------------------------------------------------------------------
# Sở hữu mặt (attribute INT / FACE)
# ----------------------------------------------------------------------------
def assign_owner(obj, uid, face_indices=None, selected_only=False):
    """Gán `uid` cho các mặt. face_indices=None & selected_only -> theo chọn Edit Mode.

    uid=0 nghĩa là nhả. Trả về số mặt đã gán.
    """
    me = obj.data
    name = product.FACE_OWNER_ATTR
    if obj.mode == "EDIT":
        bm = bmesh.from_edit_mesh(me)
        layer = bm.faces.layers.int.get(name) or bm.faces.layers.int.new(name)
        count = 0
        for f in bm.faces:
            if (selected_only and f.select) or (face_indices is not None and f.index in face_indices):
                f[layer] = uid
                count += 1
        bmesh.update_edit_mesh(me, loop_triangles=False, destructive=False)
        return count
    nf = len(me.polygons)
    attr = me.attributes.get(name)
    if attr is None:
        attr = me.attributes.new(name, "INT", "FACE")
    cur = _fget(attr.data, "value", np.int32, nf)
    if face_indices is None:
        raise MeshError("Cần danh sách mặt khi ở Object Mode.")
    idx = np.fromiter((i for i in face_indices if 0 <= i < nf), dtype=np.int64)
    cur[idx] = uid
    attr.data.foreach_set("value", cur)
    me.update()
    return int(len(idx))


def release_owner(obj, uid):
    """Nhả mọi mặt đang thuộc `uid` (đặt về 0)."""
    me = obj.data
    name = product.FACE_OWNER_ATTR
    if obj.mode == "EDIT":
        bm = bmesh.from_edit_mesh(me)
        layer = bm.faces.layers.int.get(name)
        if layer is None:
            return 0
        n = 0
        for f in bm.faces:
            if f[layer] == uid:
                f[layer] = 0
                n += 1
        bmesh.update_edit_mesh(me, loop_triangles=False, destructive=False)
        return n
    attr = me.attributes.get(name)
    if attr is None:
        return 0
    nf = len(me.polygons)
    cur = _fget(attr.data, "value", np.int32, nf)
    m = cur == uid
    cur[m] = 0
    attr.data.foreach_set("value", cur)
    me.update()
    return int(m.sum())


def count_owned(obj, uid):
    me = obj.data
    name = product.FACE_OWNER_ATTR
    if obj.mode == "EDIT":
        bm = bmesh.from_edit_mesh(me)
        layer = bm.faces.layers.int.get(name)
        return 0 if layer is None else sum(1 for f in bm.faces if f[layer] == uid)
    attr = me.attributes.get(name)
    if attr is None:
        return 0
    return int((_fget(attr.data, "value", np.int32, len(me.polygons)) == uid).sum())


def topology_signature(obj):
    """(V, L, F) — đủ để phát hiện thêm/bớt hình học."""
    me = obj.data
    if obj.mode == "EDIT":
        bm = bmesh.from_edit_mesh(me)
        return (len(bm.verts), sum(len(f.loops) for f in bm.faces) if len(bm.faces) < 20000 else -1,
                len(bm.faces))
    return (len(me.vertices), len(me.loops), len(me.polygons))

# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""Cập nhật UV trực tiếp: handler chỉ ĐÁNH DẤU, timer mới tính (debounce) -> không ghi mesh
trong depsgraph handler, an toàn với Undo/Redo."""

import time

import bpy
from bpy.app.handlers import persistent

from . import applier, gizmo as gz, meshio, prefs, state

_TICK = 0.02
_registry = set()          # tên các gizmo đang theo dõi


def delay_s():
    return max(0.0, prefs.value("live_delay_ms", 60) / 1000.0)


def request(name, immediate=False):
    """Yêu cầu tính lại UV của gizmo `name` (gộp nhiều yêu cầu liên tiếp)."""
    _registry.add(name)
    state.pending[name] = time.monotonic() - (1e3 if immediate else 0.0)
    _ensure_timer()


def _ensure_timer():
    if not bpy.app.timers.is_registered(_tick):
        bpy.app.timers.register(_tick, first_interval=_TICK, persistent=True)


def _tick():
    now = time.monotonic()
    wait = delay_s()
    due = [n for n, t in list(state.pending.items()) if now - t >= wait]
    for name in due:
        state.pending.pop(name, None)
        g = bpy.data.objects.get(name)
        if g is None or not gz.is_gizmo(g) or g.btg_uvw.target is None:
            continue
        state.applying = True
        try:
            applier.safe_apply(g)
        finally:
            state.applying = False
    return _TICK if state.pending else None


def rescan(scene=None):
    """Dựng lại danh sách gizmo theo dõi (sau load / undo / tạo / xoá).

    Khi add-on đang được bật, bpy.data là _RestrictData (không có .objects) -> bỏ qua,
    việc quét sẽ được hoãn bằng timer (xem _deferred_rescan).
    """
    _registry.clear()
    try:
        objects = bpy.data.objects
    except AttributeError:
        return False
    for ob in objects:
        if gz.is_gizmo(ob):
            _registry.add(ob.name)
    return True


def _deferred_rescan():
    if not rescan():
        return 0.2          # vẫn bị hạn chế: thử lại
    return None


@persistent
def _on_depsgraph(scene, depsgraph):
    if state.applying:
        return
    updated = {u.id.name for u in depsgraph.updates if isinstance(u.id, bpy.types.Object)}
    geom = {u.id.name for u in depsgraph.updates
            if isinstance(u.id, bpy.types.Object) and u.is_updated_geometry}
    if not updated:
        return
    for name in updated:                              # gizmo mới xuất hiện (vd. redo/duplicate)
        ob = bpy.data.objects.get(name)
        if ob is not None and name not in _registry and gz.is_gizmo(ob):
            _registry.add(name)
    for name in list(_registry):
        g = bpy.data.objects.get(name)
        if g is None or not gz.is_gizmo(g):
            _registry.discard(name)
            state.forget(name)
            continue
        p = g.btg_uvw
        t = p.target
        if not p.live or t is None or t.name not in scene.objects:
            continue
        if name not in updated and t.name not in updated:
            continue
        key = gz.transform_key(g, t, scene)
        old = state.keys.get(name)
        if old is None:
            state.keys[name] = key
            continue
        if old != key:
            request(name)
            continue
        if t.name in geom and t.mode != "EDIT":
            now = time.monotonic()
            if now - state.last_apply.get(name, 0.0) > 0.5 and \
                    meshio.topology_signature(t) != state.sigs.get(name):
                request(name)


@persistent
def _on_undo_redo(*_args):
    state.clear()
    rescan()


@persistent
def _on_load(*_args):
    state.clear()
    rescan()


def register():
    h = bpy.app.handlers
    for lst, fn in ((h.depsgraph_update_post, _on_depsgraph), (h.undo_post, _on_undo_redo),
                    (h.redo_post, _on_undo_redo), (h.load_post, _on_load)):
        if fn not in lst:
            lst.append(fn)
    if not rescan():
        bpy.app.timers.register(_deferred_rescan, first_interval=0.2, persistent=True)


def unregister():
    h = bpy.app.handlers
    for lst, fn in ((h.depsgraph_update_post, _on_depsgraph), (h.undo_post, _on_undo_redo),
                    (h.redo_post, _on_undo_redo), (h.load_post, _on_load)):
        if fn in lst:
            lst.remove(fn)
    for fn in (_tick, _deferred_rescan):
        if bpy.app.timers.is_registered(fn):
            bpy.app.timers.unregister(fn)
    state.clear()
    _registry.clear()

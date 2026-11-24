# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""Overlay viewport: mũi tên hướng vân của từng chi tiết / của gizmo.

Dùng POLYLINE_UNIFORM_COLOR (cần viewportSize + lineWidth — chạy được trên OpenGL lẫn Vulkan).
Mọi lỗi vẽ đều bị nuốt và tự tắt overlay để không bao giờ làm treo viewport.
"""

import bpy
import gpu
import numpy as np
from gpu_extras.batch import batch_for_shader

from . import gizmo as gz
from . import prefs, state

_handle = None
_failed = False
COL_GRAIN = (1.0, 0.72, 0.12, 1.0)
COL_CROSS = (0.35, 0.8, 1.0, 0.7)
COL_BOX = (0.9, 0.9, 0.9, 0.35)


def _arrow(a, b, head, out):
    """Thân + 2 cánh mũi tên a->b (toạ độ world, np.array)."""
    d = b - a
    ln = np.linalg.norm(d)
    if ln < 1e-9:
        return
    d = d / ln
    side = np.cross(d, np.array([0.0, 0.0, 1.0]))
    if np.linalg.norm(side) < 1e-6:
        side = np.cross(d, np.array([0.0, 1.0, 0.0]))
    side = side / np.linalg.norm(side)
    h = min(head, ln * 0.25)
    out += [a, b, b, b - d * h + side * h * 0.5, b, b - d * h - side * h * 0.5]


def _part_lines(g, info, grain, cross):
    t = bpy.data.objects.get(info["target"])
    if t is None:
        return
    mw = np.array(t.matrix_world)
    um = gz.scene_unit_mm()
    oscale = np.maximum(np.abs(np.array(t.matrix_world.to_scale())) * um, 1e-9)
    # mm của object -> toạ độ object: chia cho (scale_obj * unit_mm)/|scale| ; ở đây dùng
    # đúng phép nhân dùng khi tính: co_mm = co * (|world scale| * unit_mm)
    for f in info["frames"]:
        def to_world(p_mm):
            p_obj = p_mm / oscale
            return (mw @ np.append(p_obj, 1.0))[:3]
        ax = f.axes[f.grain_axis]
        half = f.extent[f.grain_axis] * 0.5
        a = to_world(f.center - ax * half)
        b = to_world(f.center + ax * half)
        _arrow(a, b, np.linalg.norm(b - a) * 0.2, grain)
        other = f.axes[1 if f.grain_axis == 0 else 0]
        h2 = f.extent[1 if f.grain_axis == 0 else 0] * 0.5
        cross += [to_world(f.center - other * h2), to_world(f.center + other * h2)]


def _gizmo_lines(g, grain, cross):
    p = g.btg_uvw
    G = np.array(gz.gizmo_world(g))
    c = G[:3, 3]
    axis = {"X": 0, "Y": 1, "Z": 2}.get(p.grain, 0)
    col = G[:3, axis]
    a, b = c - col * 0.5, c + col * 0.5
    _arrow(a, b, np.linalg.norm(b - a) * 0.2, grain)


def _draw():
    global _failed
    if _failed or not prefs.value("show_overlay", True):
        return
    try:
        ctx = bpy.context
        active = ctx.active_object
        if active is None:
            return
        g = gz.find_gizmo(ctx)
        if g is None:
            return
        grain, cross = [], []
        info = state.info.get(g.name)
        if g.btg_uvw.mapping == "PARTS" and info and info.get("frames"):
            _part_lines(g, info, grain, cross)
        elif g.btg_uvw.mapping in {"BOX", "FACE"} and g.btg_uvw.grain != "LEGACY":
            _gizmo_lines(g, grain, cross)
        if not grain:
            return
        shader = gpu.shader.from_builtin("POLYLINE_UNIFORM_COLOR")
        gpu.state.blend_set("ALPHA")
        gpu.state.depth_test_set("NONE")
        vp = gpu.state.viewport_get()
        shader.bind()
        shader.uniform_float("viewportSize", (vp[2], vp[3]))
        shader.uniform_float("lineWidth", float(prefs.value("overlay_width", 2.0)))
        for pts, col in ((cross, COL_CROSS), (grain, COL_GRAIN)):
            if not pts:
                continue
            batch = batch_for_shader(shader, "LINES", {"pos": [tuple(map(float, q)) for q in pts]})
            shader.uniform_float("color", col)
            batch.draw(shader)
        gpu.state.blend_set("NONE")
    except Exception:
        _failed = True
        import traceback
        traceback.print_exc()


def register():
    global _handle, _failed
    _failed = False
    if _handle is None:
        _handle = bpy.types.SpaceView3D.draw_handler_add(_draw, (), "WINDOW", "POST_VIEW")


def unregister():
    global _handle
    if _handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_handle, "WINDOW")
        _handle = None

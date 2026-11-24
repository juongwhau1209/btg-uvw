# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""Áp dụng một gizmo lên mesh: đọc mesh -> engine -> ghi UV."""

import time

import bpy

from ..core.errors import BtgUvwError, GizmoError, MeshError
from ..core.i18n import tr
from ..domain import engine
from . import gizmo as gz
from . import meshio, state


def apply_gizmo(g, scene=None):
    """Tính và ghi UV. Trả về dict thống kê; ném BtgUvwError khi không áp dụng được."""
    p = g.btg_uvw
    t = p.target
    if t is None or t.type != "MESH":
        raise GizmoError("Gizmo chưa có object mesh đích.")
    scene = scene or bpy.context.scene
    t0 = time.perf_counter()
    mesh = meshio.read(t, only_selected=p.edit_selected_only)
    frame = gz.build_frame(g, t, scene)
    result = engine.compute(mesh, gz.params_of(g), frame)
    if not result.loop_sel.any():
        raise MeshError("Không có mặt nào thuộc gizmo này.")
    meshio.write_uv(t, p.uv_map, result.uv, result.loop_sel)

    info = {
        "faces": int(result.face_sel.sum()),
        "parts": int(result.n_parts),
        "ms": (time.perf_counter() - t0) * 1000.0,
        "frames": result.frames,
        "target": t.name,
    }
    state.info[g.name] = info
    state.keys[g.name] = gz.transform_key(g, t, scene)
    state.sigs[g.name] = meshio.topology_signature(t)
    state.last_apply[g.name] = time.monotonic()
    return info


def safe_apply(g, report=None):
    """Như apply_gizmo nhưng không ném lỗi: trả info hoặc None (và báo cáo nếu có report)."""
    try:
        return apply_gizmo(g)
    except BtgUvwError as exc:
        if report:
            report({"WARNING"}, str(exc))
    except Exception as exc:                      # lỗi API bất ngờ: không được làm hỏng phiên làm việc
        import traceback
        traceback.print_exc()
        if report:
            report({"ERROR"}, "%s: %s" % (tr("apply"), exc))
    return None

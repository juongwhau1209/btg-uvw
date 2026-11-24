# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""Panel N-sidebar (tab "BTG UVW") + Pie menu."""

import bpy

from ..core import product
from ..core.i18n import tr
from . import gizmo as gz
from . import meshio, state
from .operators import _v1_data

OP = product.op_id


class _Base:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = product.PANEL_CATEGORY


class _SubBase(_Base):
    bl_parent_id = "BTG_UVW_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return gz.find_gizmo(context) is not None


def _gizmo_props(context):
    g = gz.find_gizmo(context)
    return g, g.btg_uvw


# ----------------------------------------------------------------------------
class BTG_UVW_PT_main(_Base, bpy.types.Panel):
    bl_label = product.PRODUCT_NAME
    bl_idname = "BTG_UVW_PT_main"

    def draw_header(self, context):
        self.layout.label(text="", icon="UV")

    def draw(self, context):
        lay = self.layout
        g = gz.find_gizmo(context)
        if g is None:
            o = context.active_object
            if o is not None and o.type == "MESH":
                col = lay.column(align=True)
                col.scale_y = 1.2
                col.operator(OP("create_parts"), text=tr("add_parts"), icon="MOD_BUILD")
                col.operator(OP("create"), text=tr("add_box"), icon="UV").mapping = "BOX"
                lay.operator_menu_enum(OP("create"), "mapping", text=tr("add_menu"))
                lay.label(text=tr("apply_to_selected"), icon="INFO")
            else:
                lay.label(text=tr("pick_mesh"), icon="INFO")
            if any(_v1_data(ob) is not None for ob in bpy.data.objects):
                lay.operator(OP("migrate_v1"), text=tr("migrate_v1"), icon="FILE_REFRESH")
            return

        p = g.btg_uvw
        t = p.target
        row = lay.row(align=True)
        row.label(text=t.name if t else "?", icon="MESH_DATA")
        op = row.operator(OP("select"), text=tr("gizmo"), icon="EMPTY_AXIS")
        op.what = "GIZMO"
        op = row.operator(OP("select"), text=tr("object"))
        op.what = "TARGET"
        if t is not None:
            others = gz.gizmos_of(context.scene, t)
            if len(others) > 1:
                row = lay.row(align=True)
                for og in others:
                    op = row.operator(OP("select"), text=str(og.btg_uvw.uid),
                                      depress=(og == g))
                    op.what = "GIZMO"
                    op.name = og.name
        lay.prop(p, "mapping", text="")
        info = state.info.get(g.name)
        if info:
            txt = "%d mặt · %.0f ms" % (info["faces"], info["ms"])
            if info["parts"]:
                txt = tr("parts_found", info["parts"]) + " · " + txt
            lay.label(text=txt, icon="CHECKMARK")
        row = lay.row(align=True)
        row.scale_y = 1.3
        row.operator(OP("apply"), icon="CHECKMARK", text=tr("apply"))
        row.prop(p, "live", text="", icon="TIME")


class BTG_UVW_PT_board(_SubBase, bpy.types.Panel):
    bl_label = "Khổ ván / Texture"
    bl_idname = "BTG_UVW_PT_board"
    bl_options = set()

    def draw(self, context):
        g, p = _gizmo_props(context)
        lay = self.layout
        lay.prop(p, "real_world", text=tr("real_world"))
        if p.real_world:
            row = lay.row(align=True)
            row.prop(p, "tex_preset", text="")
            row.operator(OP("board_save"), text="", icon="ADD")
            row.operator(OP("board_delete"), text="", icon="REMOVE")
            row = lay.row(align=True)
            row.prop(p, "tex_u", text=tr("length"))
            row.prop(p, "tex_v", text=tr("width"))
        else:
            lay.label(text=tr("fit_gizmo_info"), icon="INFO")
        if p.mapping in {"CYLINDRICAL"}:
            lay.prop(p, "cap", text=tr("cap"))
        if p.mapping in {"PLANAR", "CYLINDRICAL", "SPHERICAL", "SHRINK"} or \
                (p.mapping == "BOX" and p.grain == "LEGACY"):
            row = lay.row(align=True)
            row.label(text=tr("axis"))
            row.prop(p, "align", expand=True)


class BTG_UVW_PT_grain(_SubBase, bpy.types.Panel):
    bl_label = "Vân gỗ & chi tiết"
    bl_idname = "BTG_UVW_PT_grain"

    @classmethod
    def poll(cls, context):
        g = gz.find_gizmo(context)
        return g is not None and g.btg_uvw.mapping in {"BOX", "PARTS", "FACE"}

    def draw(self, context):
        g, p = _gizmo_props(context)
        lay = self.layout
        if p.mapping in {"BOX", "FACE"}:
            lay.prop(p, "grain", text=tr("grain_axis"))
        if p.mapping == "PARTS":
            lay.prop(p, "part_source", text=tr("part_source"))
            lay.prop(p, "part_grain", text=tr("part_grain"))
        else:
            if p.rand_offset or p.rand_rot180:
                lay.prop(p, "part_source", text=tr("part_source"))
        col = lay.column(align=True)
        col.label(text=tr("random"))
        col.prop(p, "rand_offset", text=tr("rand_offset"))
        col.prop(p, "rand_rot180", text=tr("rand_rot180"))
        row = col.row(align=True)
        row.prop(p, "seed", text=tr("seed"))
        row.operator(OP("reroll_seed"), text="", icon="FILE_REFRESH")


class BTG_UVW_PT_transform(_SubBase, bpy.types.Panel):
    bl_label = "Biến đổi UV"
    bl_idname = "BTG_UVW_PT_transform"

    def draw(self, context):
        g, p = _gizmo_props(context)
        lay = self.layout
        row = lay.row(align=True)
        row.prop(p, "tile_u", text=tr("tile_u"))
        row.prop(p, "tile_v", text=tr("tile_v"))
        row = lay.row(align=True)
        row.prop(p, "offset_u", text=tr("offset_u"))
        row.prop(p, "offset_v", text=tr("offset_v"))
        row = lay.row(align=True)
        row.prop(p, "rotation", text=tr("rotation"))
        row.operator(OP("rotate90"), text="90°")
        row = lay.row(align=True)
        row.prop(p, "flip_u", text=tr("flip_u"), toggle=True)
        row.prop(p, "flip_v", text=tr("flip_v"), toggle=True)
        row.prop(p, "flip_w", text=tr("flip_w"), toggle=True)


class BTG_UVW_PT_gizmo(_SubBase, bpy.types.Panel):
    bl_label = "Gizmo (kích thước thật)"
    bl_idname = "BTG_UVW_PT_gizmo"

    @classmethod
    def poll(cls, context):
        g = gz.find_gizmo(context)
        return g is not None and g.btg_uvw.mapping != "PARTS"

    def draw(self, context):
        g, p = _gizmo_props(context)
        lay = self.layout
        col = lay.column(align=True)
        col.prop(p, "length")
        col.prop(p, "width")
        col.prop(p, "height")
        if p.real_world and p.mapping in {"PLANAR", "BOX", "FACE"}:
            lay.label(text=tr("real_world_hint"), icon="INFO")
        row = lay.row(align=True)
        for mode, key in (("FIT", "fit"), ("CENTER", "center"), ("RESET", "reset")):
            row.operator(OP("fit"), text=tr(key)).mode = mode
        row = lay.row(align=True)
        row.operator(OP("normal_align"), text=tr("normal_align"))
        row.operator(OP("view_align"), text=tr("view_align"))


class BTG_UVW_PT_faces(_SubBase, bpy.types.Panel):
    bl_label = "Mặt áp dụng"
    bl_idname = "BTG_UVW_PT_faces"

    def draw(self, context):
        g, p = _gizmo_props(context)
        lay = self.layout
        t = p.target
        n = meshio.count_owned(t, p.uid) if t is not None else 0
        if p.scope == "OWNED":
            lay.label(text=tr("own_faces", n))
        else:
            lay.label(text=tr("all_faces") + (" (+%d)" % n if n else ""))
        lay.prop(p, "scope", text="")
        row = lay.row(align=True)
        sub = row.row(align=True)
        sub.enabled = context.mode == "EDIT_MESH"
        sub.operator(OP("assign_faces"), text=tr("assign_faces")).release = False
        row.operator(OP("assign_faces"), text=tr("release_faces")).release = True
        if context.mode == "EDIT_MESH":
            lay.prop(p, "edit_selected_only", text=tr("only_selected"))
        if t is not None and t.type == "MESH":
            lay.prop_search(p, "uv_map", t.data, "uv_layers", text=tr("uv_map"))
        lay.operator(OP("add_extra"), icon="DUPLICATE")


class BTG_UVW_PT_material(_SubBase, bpy.types.Panel):
    bl_label = "Vật liệu / Texture"
    bl_idname = "BTG_UVW_PT_material"

    def draw(self, context):
        g, p = _gizmo_props(context)
        lay = self.layout
        lay.operator(OP("load_texture"), text=tr("load_texture"), icon="FILE_IMAGE")
        row = lay.row(align=True)
        row.prop(p, "image", text="")
        row.operator(OP("make_material"), text=tr("make_material"))
        lay.operator(OP("bitmap_fit"), text=tr("bitmap_fit"))


class BTG_UVW_PT_tools(_SubBase, bpy.types.Panel):
    bl_label = "Công cụ"
    bl_idname = "BTG_UVW_PT_tools"

    def draw(self, context):
        lay = self.layout
        lay.operator(OP("copy_to_selected"), text=tr("copy_to_selected"), icon="COPYDOWN")
        lay.operator(OP("apply_all"), icon="FILE_REFRESH")
        lay.operator(OP("remove"), text=tr("remove"), icon="X")
        from . import prefs
        p = prefs.get()
        if p is not None:
            lay.prop(p, "show_overlay", text=tr("overlay"))
        lay.label(text="%s %s · %s" % (product.PRODUCT_NAME, product.VERSION_STR, product.COPYRIGHT))


class BTG_UVW_MT_pie(bpy.types.Menu):
    bl_label = product.PRODUCT_NAME
    bl_idname = "BTG_UVW_MT_pie"

    def draw(self, context):
        pie = self.layout.menu_pie()
        g = gz.find_gizmo(context)
        pie.operator(OP("create_parts"), text=tr("add_parts"), icon="MOD_BUILD")
        pie.operator(OP("create"), text=tr("add_box"), icon="UV").mapping = "BOX"
        if g is not None:
            pie.operator(OP("apply"), text=tr("apply"), icon="CHECKMARK")
            pie.operator(OP("rotate90"), text=tr("rotate90"), icon="FILE_REFRESH")
            pie.operator(OP("fit"), text=tr("fit")).mode = "FIT"
            pie.operator(OP("load_texture"), text=tr("load_texture"), icon="FILE_IMAGE")


classes = (
    BTG_UVW_PT_main, BTG_UVW_PT_board, BTG_UVW_PT_grain, BTG_UVW_PT_transform, BTG_UVW_PT_gizmo,
    BTG_UVW_PT_faces, BTG_UVW_PT_material, BTG_UVW_PT_tools, BTG_UVW_MT_pie,
)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

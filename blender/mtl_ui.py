# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""Panel Auto MTL (N-sidebar > BTG UVW)."""

import bpy

from ..core import product
from ..core.i18n import tr
from . import mtl_library, prefs

OP = product.op_id


class BTG_UVW_PT_automtl(bpy.types.Panel):
    bl_label = "Auto MTL"
    bl_idname = "BTG_UVW_PT_automtl"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = product.PANEL_CATEGORY

    def draw_header(self, context):
        self.layout.label(text="", icon="MATERIAL")

    def draw(self, context):
        lay = self.layout
        p = context.scene.btg_uvw_mtl

        # --- thư viện -------------------------------------------------------
        box = lay.box()
        row = box.row(align=True)
        row.prop(p, "lib_dir", text="")
        row.operator(OP("mtl_refresh"), text="", icon="FILE_REFRESH")
        lib = mtl_library.get_library(context.scene)
        if lib.count() == 0:
            root = mtl_library.root_dir(context.scene)
            box.label(text=tr("mtl_lib_pick") if not root else tr("mtl_lib_empty"), icon="INFO")
            fallback = prefs.get()
            if fallback is not None and not p.lib_dir:
                box.prop(fallback, "texture_dir", text=tr("texture_dir"))
        else:
            if lib.truncated:
                box.label(text=tr("mtl_lib_truncated"), icon="ERROR")
            box.prop(p, "category", text="")
            box.template_icon_view(p, "texture", show_labels=True, scale=6.0, scale_popup=5.0)
            entry = mtl_library.selected_entry(p)
            if entry is not None:
                extra = [k.title() for k in entry.maps if k != "DIFFUSE"]
                box.label(text=entry.name + ("  +  " + ", ".join(extra) if extra else ""), icon="IMAGE_DATA")

        # --- chế độ gán -----------------------------------------------------
        lay.prop(p, "mode", text="")
        col = lay.column(align=True)
        if p.mode == "PARTS":
            col.prop(p, "part_source", text=tr("part_source"))
        if p.mode in {"PARTS", "OBJECTS"}:
            col.prop(p, "pool_all")
            col.prop(p, "pool_filter", text=tr("mtl_filter"), icon="VIEWZOOM")
            row = col.row(align=True)
            row.prop(p, "seed")
            row.operator(OP("mtl_reroll"), text="", icon="FILE_REFRESH")
            n = len(mtl_library.pool_entries(p)) if lib.count() else 0
            col.label(text=tr("mtl_pool_count", n), icon="IMAGE_DATA")
        elif p.mode == "RULES":
            col.prop(p, "rule_target", text=tr("mtl_match_by"))
            col.prop(p, "rules", text="", icon="SORTALPHA")
            col.prop(p, "rule_fallback")
        else:
            col.prop(p, "fit_board")
        if p.mode in {"OBJECT", "OBJECTS", "RULES"}:
            col.prop(p, "replace_slots")

        big = lay.column()
        big.scale_y = 1.4
        big.operator(OP("mtl_apply"), text=tr("mtl_apply"), icon="CHECKMARK")

        # --- tuỳ chọn vật liệu ---------------------------------------------------
        sub = lay.box()
        sub.prop(p, "use_maps")
        col = sub.column(align=True)
        col.prop(p, "roughness")
        col.prop(p, "specular")
        col.prop(p, "bump_strength")

        # --- công cụ ---------------------------------------------------------------
        row = lay.row(align=True)
        row.operator(OP("mtl_checkmap"), text=tr("mtl_checkmap"), icon="UV_DATA")
        row.operator(OP("mtl_checkmap_restore"), text="", icon="LOOP_BACK")
        row = lay.row(align=True)
        row.operator(OP("mtl_preview"), text=tr("mtl_preview"), icon="SHADING_TEXTURE")
        row.operator(OP("mtl_cleanup"), text=tr("mtl_cleanup"), icon="TRASH")


classes = (BTG_UVW_PT_automtl,)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""Operator Auto MTL: gán vật liệu hàng loạt, Check Map, dọn dẹp, xem thử."""

import bpy

from ..core import product
from ..core.errors import BtgUvwError
from ..core.i18n import tr
from ..domain import automtl, parts
from . import applier, materials, meshio, mtl_library
from . import gizmo as gz

OP = product.op_id


def _mesh_targets(context):
    objs = [o for o in context.selected_objects if o.type == "MESH"]
    if not objs and context.active_object is not None and context.active_object.type == "MESH":
        objs = [context.active_object]
    return sorted(objs, key=lambda o: o.name)


def _leave_edit_mode(context):
    if context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")


def _uv_name_for(obj, scene):
    """UV Map mà gizmo của object ghi vào (nếu người dùng đặt tên riêng); rỗng = UV active."""
    for g in gz.gizmos_of(scene, obj):
        if g.btg_uvw.uv_map:
            return g.btg_uvw.uv_map
    return ""


def _fit_gizmos(scene, obj, entry, report):
    """Gizmo của object: gắn ảnh vào ô Bitmap và đặt khổ ván theo tỉ lệ ảnh."""
    img = None
    for g in gz.gizmos_of(scene, obj):
        p = g.btg_uvw
        if img is None:
            img = materials.load_image(entry.diffuse)
        p.image = img
        v = automtl.fit_board_v(p.tex_u, img.size[0], img.size[1])
        if v:
            p.tex_v = v


# ----------------------------------------------------------------------------
class BTG_UVW_OT_mtl_apply(bpy.types.Operator):
    bl_idname = OP("mtl_apply")
    bl_label = "Áp dụng vật liệu"
    bl_description = "Tạo vật liệu từ thư viện và gán cho các mesh đang chọn theo chế độ đã chọn"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.scene is not None and (
            any(o.type == "MESH" for o in context.selected_objects)
            or (context.active_object is not None and context.active_object.type == "MESH"))

    # -- chung -------------------------------------------------------------
    def _material(self, entry, obj, settings, scene):
        return materials.get_or_build(entry, _uv_name_for(obj, scene), settings)

    def _warn_material_source(self, scene, obj, props):
        if props.part_source != "ISLAND":
            return
        for g in gz.gizmos_of(scene, obj):
            gp = g.btg_uvw
            if gp.mapping == "PARTS" and gp.part_source == "MATERIAL":
                self.report({"WARNING"}, tr("mtl_warn_gizmo_material", obj.name))
                return

    # -- các chế độ ----------------------------------------------------------
    def _mode_object(self, context, objs, props, settings):
        entry = mtl_library.selected_entry(props)
        if entry is None:
            raise BtgUvwError(tr("mtl_need_texture"))
        for o in objs:
            materials.assign_all(o, self._material(entry, o, settings, context.scene), props.replace_slots)
            if props.fit_board:
                _fit_gizmos(context.scene, o, entry, self.report)
        return len(objs), 1

    def _mode_objects(self, context, objs, props, settings):
        pool = mtl_library.pool_entries(props)
        if not pool:
            raise BtgUvwError(tr("mtl_need_pool"))
        picks = automtl.pick_indices(len(objs), len(pool), props.seed)
        used = set()
        for o, i in zip(objs, picks):
            materials.assign_all(o, self._material(pool[i], o, settings, context.scene), props.replace_slots)
            used.add(i)
            if props.fit_board and len(pool) == 1:
                _fit_gizmos(context.scene, o, pool[i], self.report)
        return len(objs), len(used)

    def _mode_parts(self, context, objs, props, settings):
        pool = mtl_library.pool_entries(props)
        if not pool:
            raise BtgUvwError(tr("mtl_need_pool"))
        n_parts_total, used = 0, set()
        for k, o in enumerate(objs):
            self._warn_material_source(context.scene, o, props)
            mesh = meshio.read_object(o)
            labels, n = parts.split_parts(mesh, props.part_source)
            picks = automtl.pick_indices(n, len(pool), props.seed + k * 7919)
            order, part_to_slot = automtl.build_slots([pool[i].key for i in picks])
            by_key = {e.key: e for e in pool}
            mats = [self._material(by_key[key], o, settings, context.scene) for key in order]
            materials.assign_slots(o, mats, automtl.face_slot_index(labels, part_to_slot))
            n_parts_total += n
            used.update(order)
        return len(objs), len(used), n_parts_total

    def _mode_rules(self, context, objs, props, settings):
        rules = automtl.parse_rules(props.rules)
        if not rules:
            raise BtgUvwError(tr("mtl_need_rules"))
        lib = mtl_library.get_library()
        prefer = mtl_library.real_category(props.category)
        fallback = mtl_library.selected_entry(props) if props.rule_fallback else None
        used, changed = set(), 0

        def resolve(name):
            q = automtl.match_rule(name, rules)
            if q is None:
                return fallback
            e = lib.find(q, prefer)
            if e is None:
                self.report({"WARNING"}, tr("mtl_rule_missing", q))
                return fallback
            return e

        for o in objs:
            if props.rule_target == "SLOT":
                me = o.data
                if len(me.materials) == 0:
                    e = resolve("")
                    if e is not None:
                        me.materials.append(self._material(e, o, settings, context.scene))
                        used.add(e.key)
                        changed += 1
                    continue
                for i in range(len(me.materials)):
                    m = me.materials[i]
                    e = resolve(m.name if m else "")
                    if e is not None:
                        me.materials[i] = self._material(e, o, settings, context.scene)
                        used.add(e.key)
                        changed += 1
            else:
                e = resolve(o.name)
                if e is None:
                    continue
                materials.assign_all(o, self._material(e, o, settings, context.scene), props.replace_slots)
                used.add(e.key)
                changed += 1
                if props.fit_board:
                    _fit_gizmos(context.scene, o, e, self.report)
        return changed, len(used)

    # -- chạy -----------------------------------------------------------------
    def execute(self, context):
        props = context.scene.btg_uvw_mtl
        objs = _mesh_targets(context)
        if not objs:
            self.report({"WARNING"}, tr("mtl_need_mesh"))
            return {"CANCELLED"}
        _leave_edit_mode(context)
        settings = materials.settings_from(props)
        try:
            if props.mode == "OBJECT":
                n_obj, n_mat = self._mode_object(context, objs, props, settings)
            elif props.mode == "OBJECTS":
                n_obj, n_mat = self._mode_objects(context, objs, props, settings)
            elif props.mode == "PARTS":
                n_obj, n_mat, _ = self._mode_parts(context, objs, props, settings)
            else:
                n_obj, n_mat = self._mode_rules(context, objs, props, settings)
        except BtgUvwError as exc:
            self.report({"WARNING"}, str(exc))
            return {"CANCELLED"}
        except OSError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        for o in objs:                       # UV có thể cần tính lại khi vừa khớp khổ ván
            for g in gz.gizmos_of(context.scene, o):
                if g.btg_uvw.live:
                    applier.safe_apply(g)
        self.report({"INFO"}, tr("mtl_done", n_mat, n_obj))
        return {"FINISHED"}


class BTG_UVW_OT_mtl_refresh(bpy.types.Operator):
    bl_idname = OP("mtl_refresh")
    bl_label = "Làm mới thư viện"
    bl_description = "Quét lại thư mục texture và tạo lại ảnh xem trước"

    def execute(self, context):
        mtl_library.invalidate()
        lib = mtl_library.get_library(context.scene)
        if lib.count() == 0:
            self.report({"WARNING"}, tr("mtl_lib_empty"))
        else:
            self.report({"INFO"}, tr("mtl_lib_found", lib.count(), len(lib.categories)))
        return {"FINISHED"}


class BTG_UVW_OT_mtl_reroll(bpy.types.Operator):
    bl_idname = OP("mtl_reroll")
    bl_label = "Đổi seed"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        import random
        context.scene.btg_uvw_mtl.seed = random.randint(0, 99999)
        return {"FINISHED"}


class BTG_UVW_OT_mtl_checkmap(bpy.types.Operator):
    bl_idname = OP("mtl_checkmap")
    bl_label = "Check Map"
    bl_description = ("Gán tạm ảnh kiểm tra (sọc ngang, chữ F, mũi tên +U/+V, bốn góc khác màu) để soi hướng "
                      "và lật gương UV. Vật liệu cũ được nhớ để khôi phục")
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return any(o.type == "MESH" for o in context.selected_objects)

    def execute(self, context):
        _leave_edit_mode(context)
        objs = _mesh_targets(context)
        for o in objs:
            materials.apply_checkmap(o)
        _set_material_preview(context)
        self.report({"INFO"}, tr("mtl_checkmap_on", len(objs)))
        return {"FINISHED"}


class BTG_UVW_OT_mtl_checkmap_restore(bpy.types.Operator):
    bl_idname = OP("mtl_checkmap_restore")
    bl_label = "Khôi phục vật liệu"
    bl_description = "Trả lại các material slot như trước khi dùng Check Map"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        _leave_edit_mode(context)
        n = 0
        for o in bpy.data.objects:
            if o.type == "MESH" and materials.BACKUP_KEY in o:
                n += 1 if materials.restore_slots(o) else 0
        self.report({"INFO"}, tr("mtl_restored", n))
        return {"FINISHED"}


class BTG_UVW_OT_mtl_cleanup(bpy.types.Operator):
    bl_idname = OP("mtl_cleanup")
    bl_label = "Dọn vật liệu thừa"
    bl_description = "Xoá vật liệu và ảnh do Auto MTL tạo mà không còn object nào dùng"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        nm, ni = materials.cleanup()
        self.report({"INFO"}, tr("mtl_cleaned", nm, ni))
        return {"FINISHED"}


def _set_material_preview(context):
    area = context.area if context.area and context.area.type == "VIEW_3D" else None
    if area is None:
        for a in context.screen.areas if context.screen else ():
            if a.type == "VIEW_3D":
                area = a
                break
    if area is not None:
        for sp in area.spaces:
            if sp.type == "VIEW_3D":
                try:
                    sp.shading.type = "MATERIAL"
                except TypeError:          # engine hiện tại (vd. Workbench) không có Material Preview
                    sp.shading.type = "RENDERED" if "RENDERED" in sp.shading.bl_rna.properties["type"].enum_items \
                        else sp.shading.type


class BTG_UVW_OT_mtl_preview(bpy.types.Operator):
    bl_idname = OP("mtl_preview")
    bl_label = "Xem thử"
    bl_description = "Chuyển viewport sang Material Preview để thấy texture"

    def execute(self, context):
        _set_material_preview(context)
        return {"FINISHED"}


classes = (
    BTG_UVW_OT_mtl_apply, BTG_UVW_OT_mtl_refresh, BTG_UVW_OT_mtl_reroll, BTG_UVW_OT_mtl_checkmap,
    BTG_UVW_OT_mtl_checkmap_restore, BTG_UVW_OT_mtl_cleanup, BTG_UVW_OT_mtl_preview,
)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

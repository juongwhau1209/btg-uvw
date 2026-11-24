# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""Toàn bộ operator btg_uvw.*"""

import math
import os
import random

import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty
from mathutils import Matrix, Quaternion, Vector

from ..core import product
from ..core.i18n import tr
from ..domain import boards
from ..domain.v1_compat import convert_v1, is_v1_gizmo
from . import applier, live, materials, meshio, prefs, props, state
from . import gizmo as gz

MAPPING_MENU = [(k, n, d) for k, n, d in props.MAPPING_ITEMS]
_COPY_FIELDS = (
    "mapping", "align", "cap", "grain", "flip_u", "flip_v", "flip_w", "tile_u", "tile_v",
    "offset_u", "offset_v", "rotation", "real_world", "tex_preset", "tex_u", "tex_v",
    "part_source", "part_grain", "rand_offset", "rand_rot180", "seed", "uv_map", "live",
)


def _to_object_mode(context):
    if context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")


def _select_only(context, obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    context.view_layer.objects.active = obj


class _GizmoOp:
    @classmethod
    def poll(cls, context):
        return gz.find_gizmo(context) is not None


# ----------------------------------------------------------------------------
# Tạo / áp dụng / gỡ
# ----------------------------------------------------------------------------
class BTG_UVW_OT_create(bpy.types.Operator):
    bl_idname = product.op_id("create")
    bl_label = "Thêm UVW Map"
    bl_description = "Tạo gizmo UVW Map cho các mesh đang chọn"
    bl_options = {"REGISTER", "UNDO"}

    mapping: EnumProperty(name="Kiểu", items=MAPPING_MENU, default="BOX")

    def execute(self, context):
        _to_object_mode(context)
        targets = [o for o in context.selected_objects if o.type == "MESH"]
        act = context.active_object
        if act and act.type == "MESH" and act not in targets:
            targets.append(act)
        made = []
        for t in targets:
            if gz.gizmos_of(context.scene, t):
                continue
            g = gz.new_gizmo(context, t, self.mapping)
            applier.safe_apply(g, self.report)
            made.append(g)
        if not made:
            self.report({"WARNING"}, tr("nothing_to_add"))
            return {"CANCELLED"}
        live.rescan()
        self.report({"INFO"}, tr("created", len(made)))
        return {"FINISHED"}


class BTG_UVW_OT_create_parts(bpy.types.Operator):
    bl_idname = product.op_id("create_parts")
    bl_label = "Auto theo chi tiết"
    bl_description = "Tự tìm từng tấm ván và cho vân gỗ chạy theo cạnh dài của mỗi tấm"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        return bpy.ops.btg_uvw.create(mapping="PARTS")


class BTG_UVW_OT_add_extra(_GizmoOp, bpy.types.Operator):
    bl_idname = product.op_id("add_extra")
    bl_label = "Thêm gizmo thứ hai"
    bl_description = "Thêm một gizmo nữa cho cùng mesh (dùng với 'Gán mặt' để chia vùng)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        g0 = gz.find_gizmo(context)
        t = g0.btg_uvw.target
        _to_object_mode(context)
        g = gz.new_gizmo(context, t, "BOX")
        g.btg_uvw.scope = "OWNED"
        live.rescan()
        _select_only(context, g)
        return {"FINISHED"}


class BTG_UVW_OT_apply(_GizmoOp, bpy.types.Operator):
    bl_idname = product.op_id("apply")
    bl_label = "Áp dụng lại UV"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        info = applier.safe_apply(gz.find_gizmo(context), self.report)
        if info is None:
            return {"CANCELLED"}
        msg = "%d mặt" % info["faces"]
        if info["parts"]:
            msg += " · " + tr("parts_found", info["parts"])
        self.report({"INFO"}, "%s · %.0f ms" % (msg, info["ms"]))
        return {"FINISHED"}


class BTG_UVW_OT_apply_all(bpy.types.Operator):
    bl_idname = product.op_id("apply_all")
    bl_label = "Áp dụng mọi gizmo trong scene"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        n = 0
        for g in gz.all_gizmos(context.scene):
            if g.btg_uvw.target is not None and applier.safe_apply(g, self.report):
                n += 1
        self.report({"INFO"}, "%d gizmo" % n)
        return {"FINISHED"}


class BTG_UVW_OT_remove(_GizmoOp, bpy.types.Operator):
    bl_idname = product.op_id("remove")
    bl_label = "Gỡ gizmo (giữ UV)"
    bl_description = "Xóa gizmo, giữ nguyên UV hiện tại trên object"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        g = gz.find_gizmo(context)
        t, uid, name = g.btg_uvw.target, g.btg_uvw.uid, g.name
        _to_object_mode(context)
        if t is not None:
            meshio.release_owner(t, uid)
        bpy.data.objects.remove(g, do_unlink=True)
        state.forget(name)
        live.rescan()
        if t is not None:
            _select_only(context, t)
        return {"FINISHED"}


class BTG_UVW_OT_select(_GizmoOp, bpy.types.Operator):
    bl_idname = product.op_id("select")
    bl_label = "Chọn"
    bl_options = {"REGISTER", "UNDO"}

    what: EnumProperty(items=[("GIZMO", "Gizmo", ""), ("TARGET", "Object", "")], default="GIZMO")
    name: StringProperty(default="")

    def execute(self, context):
        g = bpy.data.objects.get(self.name) if self.name else gz.find_gizmo(context)
        if g is None:
            return {"CANCELLED"}
        obj = g if self.what == "GIZMO" else g.btg_uvw.target
        _to_object_mode(context)
        _select_only(context, obj)
        return {"FINISHED"}


# ----------------------------------------------------------------------------
# Hình học gizmo
# ----------------------------------------------------------------------------
class BTG_UVW_OT_fit(_GizmoOp, bpy.types.Operator):
    bl_idname = product.op_id("fit")
    bl_label = "Fit"
    bl_description = "Fit: ôm sát mesh (hoặc phần đang chọn ở Edit Mode); Center: chỉ căn tâm; Reset: bỏ xoay"
    bl_options = {"REGISTER", "UNDO"}

    mode: EnumProperty(items=[("FIT", "Fit", ""), ("CENTER", "Center", ""), ("RESET", "Reset", "")],
                       default="FIT")

    def execute(self, context):
        g = gz.find_gizmo(context)
        if self.mode == "FIT":
            gz.fit_gizmo(g, scale=True)
        elif self.mode == "CENTER":
            gz.fit_gizmo(g, scale=False)
        else:
            gz.fit_gizmo(g, reset=True)
        if g.btg_uvw.live:
            live.request(g.name, immediate=True)
        return {"FINISHED"}


class BTG_UVW_OT_normal_align(_GizmoOp, bpy.types.Operator):
    bl_idname = product.op_id("normal_align")
    bl_label = "Normal Align"
    bl_description = "Đặt gizmo vuông góc với mặt đang chọn (chọn mặt trong Edit Mode)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        g = gz.find_gizmo(context)
        p = g.btg_uvw
        t = p.target
        if t.mode == "EDIT":
            t.update_from_editmode()
        polys = [pl for pl in t.data.polygons if pl.select]
        if not polys:
            self.report({"WARNING"}, tr("need_edit_faces"))
            return {"CANCELLED"}
        n = Vector((0, 0, 0))
        c = Vector((0, 0, 0))
        for pl in polys:
            n += pl.normal
            c += pl.center
        c /= len(polys)
        nw = (t.matrix_world.to_3x3().inverted_safe().transposed() @ n).normalized()
        cw = t.matrix_world @ c
        track, up = {"Z": ("Z", "Y"), "X": ("X", "Z"), "Y": ("Y", "Z")}[p.align]
        q = nw.to_track_quat(track, up)
        loc, rot, sc = gz.gizmo_world(g).decompose()
        g.matrix_world = Matrix.LocRotScale(cw, q, sc)
        if p.live:
            live.request(g.name, immediate=True)
        return {"FINISHED"}


class BTG_UVW_OT_view_align(_GizmoOp, bpy.types.Operator):
    bl_idname = product.op_id("view_align")
    bl_label = "View Align"
    bl_description = "Đặt gizmo song song với góc nhìn hiện tại"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        rv3d = context.region_data
        if rv3d is None:
            return {"CANCELLED"}
        g = gz.find_gizmo(context)
        p = g.btg_uvw
        q = rv3d.view_rotation.copy()
        if p.align == "X":
            q = q @ Quaternion((0, 1, 0), math.radians(-90))
        elif p.align == "Y":
            q = q @ Quaternion((1, 0, 0), math.radians(90))
        loc, rot, sc = gz.gizmo_world(g).decompose()
        g.matrix_world = Matrix.LocRotScale(loc, q, sc)
        if p.live:
            live.request(g.name, immediate=True)
        return {"FINISHED"}


class BTG_UVW_OT_rotate90(_GizmoOp, bpy.types.Operator):
    bl_idname = product.op_id("rotate90")
    bl_label = "Xoay 90°"
    bl_description = "Xoay texture 90° (đổi vân ngang <-> vân dọc)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        p = gz.find_gizmo(context).btg_uvw
        r = (p.rotation + 90.0) % 360.0
        p.rotation = r if r <= 180.0 else r - 360.0
        return {"FINISHED"}


class BTG_UVW_OT_bitmap_fit(_GizmoOp, bpy.types.Operator):
    bl_idname = product.op_id("bitmap_fit")
    bl_label = "Bitmap Fit"
    bl_description = "Lấy tỉ lệ khung theo ảnh texture"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        g = gz.find_gizmo(context)
        p = g.btg_uvw
        img = p.image
        if img is None or img.size[0] == 0:
            self.report({"WARNING"}, tr("need_image"))
            return {"CANCELLED"}
        w, h = img.size
        if p.real_world:
            p.tex_v = p.tex_u * h / w
        else:
            ia, ib = (0, 1) if p.align == "Z" else ((1, 2) if p.align == "X" else (0, 2))
            size_a = abs(gz.gizmo_world(g).to_scale()[ia]) * gz.scene_unit_mm()
            loc, rot, sc = gz.gizmo_world(g).decompose()
            sc[ib] = size_a * h / w / gz.scene_unit_mm()
            g.matrix_world = Matrix.LocRotScale(loc, rot, sc)
        return {"FINISHED"}


class BTG_UVW_OT_reroll_seed(_GizmoOp, bpy.types.Operator):
    bl_idname = product.op_id("reroll_seed")
    bl_label = "Đổi seed"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        gz.find_gizmo(context).btg_uvw.seed = random.randint(0, 99999)
        return {"FINISHED"}


# ----------------------------------------------------------------------------
# Mặt sở hữu
# ----------------------------------------------------------------------------
class BTG_UVW_OT_assign_faces(_GizmoOp, bpy.types.Operator):
    bl_idname = product.op_id("assign_faces")
    bl_label = "Gán mặt"
    bl_description = "Gán các mặt đang chọn (Edit Mode) cho gizmo này; hoặc nhả hết"
    bl_options = {"REGISTER", "UNDO"}

    release: BoolProperty(default=False)

    def execute(self, context):
        g = gz.find_gizmo(context)
        p = g.btg_uvw
        t = p.target
        if self.release:
            meshio.release_owner(t, p.uid)
            p.scope = "ALL"
        else:
            if t.mode != "EDIT":
                self.report({"WARNING"}, tr("need_edit_faces"))
                return {"CANCELLED"}
            n = meshio.assign_owner(t, p.uid, selected_only=True)
            if not n:
                self.report({"WARNING"}, tr("no_face_selected"))
                return {"CANCELLED"}
            p.scope = "OWNED"
        applier.safe_apply(g, self.report)
        return {"FINISHED"}


# ----------------------------------------------------------------------------
# Texture / vật liệu / sao chép
# ----------------------------------------------------------------------------
class BTG_UVW_OT_load_texture(_GizmoOp, bpy.types.Operator):
    bl_idname = product.op_id("load_texture")
    bl_label = "Chọn texture…"
    bl_description = "Nạp ảnh texture, tạo vật liệu và gán cho mesh đích"
    bl_options = {"REGISTER", "UNDO"}

    filepath: StringProperty(subtype="FILE_PATH")
    filter_image: BoolProperty(default=True, options={"HIDDEN"})
    filter_folder: BoolProperty(default=True, options={"HIDDEN"})

    def invoke(self, context, event):
        d = prefs.value("texture_dir", "")
        if d and os.path.isdir(bpy.path.abspath(d)):
            self.filepath = os.path.join(bpy.path.abspath(d), "")
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        g = gz.find_gizmo(context)
        p = g.btg_uvw
        path = bpy.path.abspath(self.filepath)
        if not os.path.isfile(path):
            self.report({"ERROR"}, "Không tìm thấy file: %s" % path)
            return {"CANCELLED"}
        try:
            img = materials.load_image(path)
        except RuntimeError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        p.image = img
        mat = materials.make_material(p.target, img, p.uv_map)
        materials.assign(p.target, mat)
        applier.safe_apply(g, self.report)
        return {"FINISHED"}


class BTG_UVW_OT_make_material(_GizmoOp, bpy.types.Operator):
    bl_idname = product.op_id("make_material")
    bl_label = "Tạo vật liệu"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        p = gz.find_gizmo(context).btg_uvw
        if p.image is None:
            self.report({"WARNING"}, tr("need_image"))
            return {"CANCELLED"}
        materials.assign(p.target, materials.make_material(p.target, p.image, p.uv_map))
        return {"FINISHED"}


class BTG_UVW_OT_copy_to_selected(_GizmoOp, bpy.types.Operator):
    bl_idname = product.op_id("copy_to_selected")
    bl_label = "Sao chép sang mesh khác"
    bl_description = "Tạo gizmo cùng thông số cho các mesh đang chọn (trừ mesh đích)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        src = gz.find_gizmo(context)
        sp = src.btg_uvw
        _to_object_mode(context)
        made = 0
        for t in [o for o in context.selected_objects if o.type == "MESH" and o != sp.target]:
            if gz.gizmos_of(context.scene, t):
                continue
            g = gz.new_gizmo(context, t, sp.mapping)
            gp = g.btg_uvw
            for f in _COPY_FIELDS:
                setattr(gp, f, getattr(sp, f))
            gp.image = sp.image
            if sp.mapping not in {"PARTS"}:
                g.matrix_world = t.matrix_world @ (sp.target.matrix_world.inverted_safe() @ gz.gizmo_world(src))
            applier.safe_apply(g, self.report)
            made += 1
        live.rescan()
        self.report({"INFO"}, tr("created", made))
        return {"FINISHED"} if made else {"CANCELLED"}


# ----------------------------------------------------------------------------
# Khổ ván
# ----------------------------------------------------------------------------
class BTG_UVW_OT_board_save(_GizmoOp, bpy.types.Operator):
    bl_idname = product.op_id("board_save")
    bl_label = "Lưu khổ này"
    bl_description = "Lưu kích thước texture hiện tại thành khổ ván của bạn (~/.btg/btg_uvw)"
    bl_options = {"REGISTER"}

    label: StringProperty(name="Tên", default="")

    def invoke(self, context, event):
        p = gz.find_gizmo(context).btg_uvw
        self.label = "Khổ %g x %g" % (p.tex_u, p.tex_v)
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        p = gz.find_gizmo(context).btg_uvw
        key = boards.board_key(p.tex_u, p.tex_v)
        mine = [b for b in props.user_boards() if b.key != key]
        mine.append(boards.Board(key, self.label or key, float(p.tex_u), float(p.tex_v), False))
        boards.save_user_boards(prefs.boards_file(), mine)
        props.invalidate_user_boards()
        p.tex_preset = key
        return {"FINISHED"}


class BTG_UVW_OT_board_delete(_GizmoOp, bpy.types.Operator):
    bl_idname = product.op_id("board_delete")
    bl_label = "Xóa khổ này"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        g = gz.find_gizmo(context)
        if g is None:
            return False
        b = boards.find_board(g.btg_uvw.tex_preset, props.user_boards())
        return b is not None and not b.builtin

    def execute(self, context):
        p = gz.find_gizmo(context).btg_uvw
        mine = [b for b in props.user_boards() if b.key != p.tex_preset]
        boards.save_user_boards(prefs.boards_file(), mine)
        props.invalidate_user_boards()
        p.tex_preset = boards.BUILTIN[0].key
        return {"FINISHED"}


# ----------------------------------------------------------------------------
# Chuyển từ UVW Map v1
# ----------------------------------------------------------------------------
class BTG_UVW_OT_migrate_v1(bpy.types.Operator):
    bl_idname = product.op_id("migrate_v1")
    bl_label = "Chuyển từ UVW Map v1"
    bl_description = "Đổi gizmo của add-on UVW Map v1 sang BTG.UVW (UV giữ nguyên kết quả)"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return any(_v1_data(o) is not None for o in bpy.data.objects)

    def execute(self, context):
        n = 0
        for ob in list(bpy.data.objects):
            data = _v1_data(ob)
            if data is None:
                continue
            target = data.get("target") if hasattr(data, "get") else None
            if target is None or getattr(target, "type", "") != "MESH":
                continue
            conv = convert_v1(data)
            faces = conv.pop("faces")
            p = ob.btg_uvw
            p.target = target
            p.uid = gz.next_uid(target)
            for k, v in conv.items():
                setattr(p, k, v)
            img = data.get("image") if hasattr(data, "get") else None
            if img is not None:
                p.image = img
            if faces:
                _to_object_mode(context)
                meshio.assign_owner(target, p.uid, face_indices=set(faces))
                p.scope = "OWNED"
            p.is_gizmo = True
            try:
                del ob["uvw"]
            except Exception:
                pass
            n += 1
        live.rescan()
        self.report({"INFO"}, tr("created", n))
        return {"FINISHED"}


def _v1_data(ob):
    if ob.type != "EMPTY" or ob.btg_uvw.is_gizmo:
        return None
    try:
        data = ob["uvw"]
    except KeyError:
        return None
    return data if is_v1_gizmo(data) else None


classes = (
    BTG_UVW_OT_create, BTG_UVW_OT_create_parts, BTG_UVW_OT_add_extra, BTG_UVW_OT_apply,
    BTG_UVW_OT_apply_all, BTG_UVW_OT_remove, BTG_UVW_OT_select, BTG_UVW_OT_fit,
    BTG_UVW_OT_normal_align, BTG_UVW_OT_view_align, BTG_UVW_OT_rotate90, BTG_UVW_OT_bitmap_fit,
    BTG_UVW_OT_reroll_seed, BTG_UVW_OT_assign_faces, BTG_UVW_OT_load_texture,
    BTG_UVW_OT_make_material, BTG_UVW_OT_copy_to_selected, BTG_UVW_OT_board_save,
    BTG_UVW_OT_board_delete, BTG_UVW_OT_migrate_v1,
)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

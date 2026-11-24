# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""PropertyGroup `Object.btg_uvw` — toàn bộ thông số của một gizmo UVW."""

import os

import bpy
from bpy.props import (BoolProperty, EnumProperty, FloatProperty, IntProperty,
                       PointerProperty, StringProperty)
from mathutils import Matrix

from ..domain import boards
from . import gizmo as gz
from . import prefs

_syncing = False
_user_cache = {"mtime": None, "boards": []}
_enum_keep = []


# ----------------------------------------------------------------------------
# Khổ ván
# ----------------------------------------------------------------------------
def user_boards():
    path = prefs.boards_file()
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        mtime = None
    if mtime != _user_cache["mtime"]:
        _user_cache["boards"] = boards.load_user_boards(path) if mtime else []
        _user_cache["mtime"] = mtime
    return _user_cache["boards"]


def invalidate_user_boards():
    _user_cache["mtime"] = -1


def board_items(self, context):
    global _enum_keep
    items = []
    for i, b in enumerate(boards.all_boards(user_boards())):
        num = 999 if b.key == boards.CUSTOM_KEY else i
        desc = "" if b.key == boards.CUSTOM_KEY else "%g x %g mm" % (b.length, b.width)
        items.append((b.key, b.label, desc, "NONE", num))
    _enum_keep = items          # giữ tham chiếu (Blender yêu cầu)
    return items


# ----------------------------------------------------------------------------
# Callback cập nhật
# ----------------------------------------------------------------------------
def _changed(self, context):
    if not self.is_gizmo or not self.live or self.target is None:
        return
    from . import live
    live.request(self.id_data.name)


def _preset_changed(self, context):
    global _syncing
    b = boards.find_board(self.tex_preset, user_boards())
    if b is not None and b.key != boards.CUSTOM_KEY and not _syncing:
        _syncing = True
        try:
            self.tex_u, self.tex_v = b.length, b.width
        finally:
            _syncing = False
    _changed(self, context)


def _tex_changed(self, context):
    global _syncing
    if not _syncing:
        b = boards.find_board(self.tex_preset, user_boards())
        if b is not None and b.key != boards.CUSTOM_KEY and (
                abs(b.length - self.tex_u) > 1e-6 or abs(b.width - self.tex_v) > 1e-6):
            _syncing = True
            try:
                self.tex_preset = boards.CUSTOM_KEY
            finally:
                _syncing = False
    _changed(self, context)


def _size_get(axis):
    def get(self):
        return abs(gz.gizmo_world(self.id_data).to_scale()[axis]) * gz.scene_unit_mm()
    return get


def _size_set(axis):
    def set_(self, value):
        g = self.id_data
        loc, rot, sc = gz.gizmo_world(g).decompose()
        sc[axis] = max(value, 1.0) / gz.scene_unit_mm()
        g.matrix_world = Matrix.LocRotScale(loc, rot, sc)
    return set_


def _target_poll(self, obj):
    return obj.type == "MESH"


MAPPING_ITEMS = [
    ("BOX", "Box (Hộp)", "Mỗi mặt chiếu phẳng theo trục chính; hỗ trợ hướng vân"),
    ("PARTS", "Theo chi tiết (Auto)", "Tự tìm từng tấm ván, vân chạy theo cạnh dài của mỗi tấm"),
    ("PLANAR", "Planar (Phẳng)", ""),
    ("CYLINDRICAL", "Cylindrical (Trụ)", ""),
    ("SPHERICAL", "Spherical (Cầu)", ""),
    ("SHRINK", "Shrink Wrap", ""),
    ("FACE", "Face (Từng mặt)", ""),
]


class BTG_UVW_Props(bpy.types.PropertyGroup):
    is_gizmo: BoolProperty(default=False)
    uid: IntProperty(default=0, description="Mã gizmo, dùng để sở hữu mặt")
    target: PointerProperty(name="Object", type=bpy.types.Object, poll=_target_poll,
                            update=_changed)

    mapping: EnumProperty(name="Kiểu mapping", items=MAPPING_ITEMS, default="BOX",
                          update=_changed)
    align: EnumProperty(name="Trục chiếu", items=[("X", "X", ""), ("Y", "Y", ""), ("Z", "Z", "")],
                        default="Z", update=_changed)
    cap: BoolProperty(name="Cap (nắp trụ)", default=True, update=_changed)

    grain: EnumProperty(
        name="Hướng vân",
        items=[("X", "Dọc theo X", "Vân chạy dọc trục X của gizmo trên mọi mặt"),
               ("Y", "Dọc theo Y", "Vân chạy dọc trục Y của gizmo trên mọi mặt"),
               ("Z", "Dọc theo Z", "Vân chạy dọc trục Z của gizmo trên mọi mặt (cánh tủ đứng)"),
               ("LEGACY", "Kiểu v1 (mỗi mặt một hướng)", "Giống UVW Map v1")],
        default="X", update=_changed)

    flip_u: BoolProperty(name="Lật U", default=False, update=_changed)
    flip_v: BoolProperty(name="Lật V", default=False, update=_changed)
    flip_w: BoolProperty(name="Lật W", default=False, update=_changed,
                         description="Đảo hướng chiếu (không dùng cho Box có hướng vân)")
    tile_u: FloatProperty(name="Tile U", default=1.0, update=_changed)
    tile_v: FloatProperty(name="Tile V", default=1.0, update=_changed)
    offset_u: FloatProperty(name="Lệch U", default=0.0, update=_changed)
    offset_v: FloatProperty(name="Lệch V", default=0.0, update=_changed)
    rotation: FloatProperty(name="Xoay", default=0.0, min=-360.0, max=360.0, step=900,
                            precision=1, update=_changed, description="Độ, quanh tâm tile")

    length: FloatProperty(name="Dài X (mm)", get=_size_get(0), set=_size_set(0), update=_changed)
    width: FloatProperty(name="Rộng Y (mm)", get=_size_get(1), set=_size_set(1), update=_changed)
    height: FloatProperty(name="Cao Z (mm)", get=_size_get(2), set=_size_set(2), update=_changed)

    real_world: BoolProperty(
        name="Kích thước thật (Real-World)", default=True, update=_changed,
        description="Ảnh texture = 1 tấm ván kích thước thật, không phụ thuộc kích thước gizmo")
    tex_preset: EnumProperty(name="Khổ ván", items=board_items, update=_preset_changed)
    tex_u: FloatProperty(name="Texture dài (mm)", default=2440.0, min=1.0, update=_tex_changed)
    tex_v: FloatProperty(name="Texture rộng (mm)", default=1220.0, min=1.0, update=_tex_changed)

    part_source: EnumProperty(
        name="Chia chi tiết theo",
        items=[("ISLAND", "Mảng rời (island)", "Mỗi cụm mặt liền nhau là một chi tiết"),
               ("MATERIAL", "Material", "Mỗi material slot là một chi tiết"),
               ("OBJECT", "Cả object", "Coi cả object là một chi tiết")],
        default="ISLAND", update=_changed)
    part_grain: EnumProperty(
        name="Vân chạy theo cạnh",
        items=[("LONGEST", "Cạnh dài nhất", ""), ("MIDDLE", "Cạnh giữa", ""),
               ("SHORTEST", "Cạnh ngắn nhất", "")],
        default="LONGEST", update=_changed)
    rand_offset: BoolProperty(name="Lệch ngẫu nhiên", default=False, update=_changed,
                              description="Mỗi chi tiết lệch UV ngẫu nhiên để các tấm không giống hệt nhau")
    rand_rot180: BoolProperty(name="Xoay 180° ngẫu nhiên", default=False, update=_changed,
                              description="Mỗi chi tiết có thể lật đầu-đuôi (vân giữ nguyên hướng)")
    seed: IntProperty(name="Seed", default=1, min=0, update=_changed)

    scope: EnumProperty(
        name="Phạm vi",
        items=[("ALL", "Mọi mặt chưa của gizmo khác", "Áp dụng cho mặt tự do và mặt đã gán cho gizmo này"),
               ("OWNED", "Chỉ mặt đã gán", "Chỉ các mặt bạn đã gán cho gizmo này")],
        default="ALL", update=_changed)
    edit_selected_only: BoolProperty(
        name="Chỉ mặt đang chọn (Edit)", default=False, update=_changed,
        description="Trong Edit Mode chỉ ghi UV các mặt đang chọn")
    uv_map: StringProperty(name="UV Map", default="", update=_changed,
                           description="Để trống = UV map đang active")
    image: PointerProperty(name="Bitmap", type=bpy.types.Image)
    live: BoolProperty(name="Cập nhật trực tiếp", default=True,
                       description="Di chuyển/xoay/scale gizmo là UV đổi theo ngay")


classes = (BTG_UVW_Props,)


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Object.btg_uvw = PointerProperty(type=BTG_UVW_Props)


def unregister():
    del bpy.types.Object.btg_uvw
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

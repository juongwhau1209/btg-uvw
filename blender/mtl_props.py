# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""PropertyGroup `Scene.btg_uvw_mtl` — thiết lập của Auto MTL (lưu cùng file .blend)."""

import bpy
from bpy.props import (BoolProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty,
                       StringProperty)

from . import mtl_library

MODE_ITEMS = [
    ("OBJECT", "Cả object", "Cùng một texture đã chọn cho mọi mesh đang chọn"),
    ("PARTS", "Theo chi tiết (ngẫu nhiên)",
     "Mỗi chi tiết (tấm ván) của mesh nhận một texture ngẫu nhiên từ bộ texture"),
    ("OBJECTS", "Mỗi object (ngẫu nhiên)", "Mỗi mesh đang chọn nhận một texture ngẫu nhiên từ bộ texture"),
    ("RULES", "Theo quy tắc tên", "Gán texture theo từ khoá trong tên object hoặc tên material slot"),
]
PART_SOURCE_ITEMS = [
    ("ISLAND", "Mảng rời (island)", "Mỗi cụm mặt liền nhau là một chi tiết"),
    ("MATERIAL", "Material hiện có", "Mỗi material slot hiện có là một chi tiết"),
    ("OBJECT", "Cả object", "Coi cả mesh là một chi tiết"),
]
RULE_TARGET_ITEMS = [
    ("OBJECT", "Tên object", "So khớp từ khoá với tên của từng object đang chọn"),
    ("SLOT", "Tên material slot", "So khớp từ khoá với tên vật liệu hiện có ở từng slot, thay riêng slot đó"),
]


def _lib_changed(self, context):
    mtl_library.invalidate()


class BTG_UVW_MtlProps(bpy.types.PropertyGroup):
    lib_dir: StringProperty(
        name="Thư viện texture", subtype="DIR_PATH", default="", update=_lib_changed,
        description="Thư mục gốc: mỗi thư mục con là một danh mục. Để trống = dùng 'Thư mục texture' "
                    "trong Preferences")
    category: EnumProperty(name="Danh mục", items=mtl_library.category_items)
    texture: EnumProperty(name="Texture", items=mtl_library.texture_items)

    mode: EnumProperty(name="Chế độ gán", items=MODE_ITEMS, default="OBJECT")
    part_source: EnumProperty(name="Chia chi tiết theo", items=PART_SOURCE_ITEMS, default="ISLAND")
    pool_all: BoolProperty(
        name="Cả thư viện", default=False,
        description="Bộ texture ngẫu nhiên lấy từ mọi danh mục (tắt: chỉ danh mục đang chọn)")
    pool_filter: StringProperty(
        name="Lọc tên", default="",
        description="Chỉ dùng texture có tên chứa các từ này (không phân biệt dấu/hoa thường)")
    seed: IntProperty(name="Seed", default=1, min=0)

    rules: StringProperty(
        name="Quy tắc", default="",
        description="Ví dụ: canh=Gỗ 01; than tu=Gỗ 02  (khoá=tên texture, cách nhau bằng ';'). "
                    "Có thể ghi 'Danh mục/Tên'")
    rule_target: EnumProperty(name="So khớp theo", items=RULE_TARGET_ITEMS, default="OBJECT")
    rule_fallback: BoolProperty(
        name="Không khớp: dùng texture đã chọn", default=True,
        description="Object/slot không khớp quy tắc nào sẽ nhận texture đang chọn (tắt: bỏ qua)")

    replace_slots: BoolProperty(
        name="Thay toàn bộ slot", default=True,
        description="Xoá các material slot cũ trước khi gán (tắt: chỉ ghi vào slot đầu tiên)")
    fit_board: BoolProperty(
        name="Khớp khổ ván theo ảnh", default=True,
        description="Gizmo UVW của mesh: đặt tỉ lệ khổ ván (Rộng) theo tỉ lệ ảnh, giữ nguyên Dài")

    use_maps: BoolProperty(
        name="Nối map đi kèm", default=True,
        description="Tự nối các ảnh cùng tên: _normal, _rough, _gloss, _bump/_height, _ao, _metal, _opacity")
    roughness: FloatProperty(name="Roughness", default=0.45, min=0.0, max=1.0, subtype="FACTOR",
                             description="Dùng khi texture không có map roughness/gloss")
    specular: FloatProperty(name="Specular", default=0.5, min=0.0, max=1.0, subtype="FACTOR")
    bump_strength: FloatProperty(name="Bump", default=0.3, min=0.0, max=2.0,
                                 description="Cường độ bump khi có map height/bump")


classes = (BTG_UVW_MtlProps,)


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.btg_uvw_mtl = PointerProperty(type=BTG_UVW_MtlProps)


def unregister():
    del bpy.types.Scene.btg_uvw_mtl
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

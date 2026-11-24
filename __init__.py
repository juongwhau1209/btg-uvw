# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""BTG.UVW — UVW Map kiểu 3ds Max cho nội thất (kích thước ván thật, vân gỗ đúng hướng).

Chủ sở hữu: Trần Duy Dương. Mã gốc thuật toán nằm ở `domain` (thuần numpy, test được không
cần Blender); `blender` là lớp mỏng nối vào bpy.
"""

bl_info = {
    "name": "BTG.UVW",
    "author": "Trần Duy Dương",
    "version": (1, 1, 0),
    "blender": (4, 2, 0),
    "location": "3D Viewport > Sidebar (N) > BTG UVW",
    "description": "UVW Map kiểu 3ds Max: Box/Planar/Cylindrical/Spherical/Shrink/Face + "
                   "kích thước ván thật, vân gỗ đúng hướng, tự động theo chi tiết",
    "category": "UV",
}


def register():
    from .blender import registry
    registry.register()


def unregister():
    from .blender import registry
    registry.unregister()

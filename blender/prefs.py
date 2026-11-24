# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tuỳ chọn người dùng (Edit > Preferences > Add-ons > BTG.UVW)."""

import os

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, StringProperty

from ..core import i18n, product


def _pkg():
    return __package__.rsplit(".", 1)[0]


def data_dir():
    """~/.btg/btg_uvw (tạo khi cần)."""
    return os.path.join(os.path.expanduser("~"), *product.DATA_DIR_NAME.split("/"))


def boards_file():
    return os.path.join(data_dir(), "boards.json")


def get():
    try:
        return bpy.context.preferences.addons[_pkg()].preferences
    except Exception:
        return None


def value(name, default):
    p = get()
    return getattr(p, name, default) if p is not None else default


def _on_language(self, context):
    i18n.set_language(self.language)
    try:
        for win in bpy.context.window_manager.windows:
            for area in win.screen.areas:
                area.tag_redraw()
    except AttributeError:
        pass


class BTG_UVW_Preferences(bpy.types.AddonPreferences):
    bl_idname = _pkg()

    language: EnumProperty(
        name="Ngôn ngữ", items=[("VI", "Tiếng Việt", ""), ("EN", "English", "")],
        default="VI", update=_on_language)
    texture_dir: StringProperty(
        name="Thư mục texture", subtype="DIR_PATH", default="",
        description="Thư mục chứa ảnh vân gỗ/laminate; mở sẵn khi bấm 'Chọn texture…'")
    live_delay_ms: IntProperty(
        name="Độ trễ cập nhật (ms)", default=60, min=0, max=1000,
        description="Chờ yên bao lâu rồi mới tính lại UV khi kéo gizmo (giảm giật với mesh nặng)")
    show_overlay: BoolProperty(name="Hiện hướng vân trên viewport", default=True)
    overlay_width: FloatProperty(name="Độ dày nét", default=2.0, min=1.0, max=8.0)
    keymap_enabled: BoolProperty(
        name="Phím tắt pie menu (Shift+Alt+U)", default=False,
        description="Mặc định TẮT để không đè phím của add-on khác. Đổi xong cần bật lại add-on")

    def draw(self, context):
        col = self.layout.column()
        col.label(text="%s %s  ·  %s %s" % (product.PRODUCT_NAME, product.VERSION_STR,
                                          i18n.tr("author"), product.OWNER))
        col.prop(self, "language")
        col.prop(self, "texture_dir")
        col.prop(self, "live_delay_ms")
        row = col.row()
        row.prop(self, "show_overlay")
        row.prop(self, "overlay_width")
        col.prop(self, "keymap_enabled")


def register():
    bpy.utils.register_class(BTG_UVW_Preferences)
    p = get()
    if p is not None:
        i18n.set_language(p.language)


def unregister():
    bpy.utils.unregister_class(BTG_UVW_Preferences)

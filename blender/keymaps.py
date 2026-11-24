# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""Phím tắt: mặc định TẮT (không đè phím của add-on khác). Bật trong Preferences."""

import bpy

from . import prefs

_items = []


def register():
    if not prefs.value("keymap_enabled", False):
        return
    try:
        kc = bpy.context.window_manager.keyconfigs.addon
    except AttributeError:      # context bị hạn chế lúc bật add-on
        return
    if kc is None:
        return
    km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")
    kmi = km.keymap_items.new("wm.call_menu_pie", "U", "PRESS", shift=True, alt=True)
    kmi.properties.name = "BTG_UVW_MT_pie"
    _items.append((km, kmi))


def unregister():
    for km, kmi in _items:
        try:
            km.keymap_items.remove(kmi)
        except Exception:
            pass
    _items.clear()

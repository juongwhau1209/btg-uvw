# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""Thư viện texture của Auto MTL: quét thư mục, ảnh xem trước (thumbnail) và danh sách enum động."""

import os

import bpy

from ..core.i18n import tr
from ..domain import automtl
from . import prefs

_lib = None
_root = None
_pcoll = None
_cat_items = []        # Blender yêu cầu giữ tham chiếu tới danh sách enum động
_tex_items = {}        # danh mục -> danh sách item (cache để vẽ panel nhanh)
_icon_keys = set()
MAX_PREVIEWS_PER_CATEGORY = 150
NONE_ID = "NONE"


# ----------------------------------------------------------------------------
# Thư mục gốc + quét
# ----------------------------------------------------------------------------
def root_dir(scene=None):
    """Thư mục thư viện: ô trong panel Auto MTL; để trống thì dùng 'Thư mục texture' trong Preferences."""
    scene = scene or getattr(bpy.context, "scene", None)
    d = ""
    props = getattr(scene, "btg_uvw_mtl", None)
    if props is not None:
        d = props.lib_dir
    if not d:
        d = prefs.value("texture_dir", "")
    return bpy.path.abspath(d) if d else ""


def invalidate():
    """Quên bản quét + ảnh xem trước (gọi khi đổi thư mục hoặc bấm Làm mới)."""
    global _lib, _root
    _lib = None
    _root = None
    _tex_items.clear()
    _icon_keys.clear()
    if _pcoll is not None:
        try:
            _pcoll.clear()
        except Exception:
            pass


def get_library(scene=None):
    global _lib, _root
    root = root_dir(scene)
    if _lib is None or _root != root:
        _tex_items.clear()
        _lib = automtl.scan_library(root)
        _root = root
    return _lib


def category_display(cat):
    return cat if cat else tr("mtl_root")


# ----------------------------------------------------------------------------
# Ảnh xem trước
# ----------------------------------------------------------------------------
def _icon_for(entry):
    if _pcoll is None:
        return 0
    k = entry.key
    try:
        if k not in _icon_keys:
            path = entry.thumb if entry.thumb and os.path.isfile(entry.thumb) else entry.diffuse
            if k in _pcoll:
                pass
            else:
                _pcoll.load(k, path, "IMAGE")
            _icon_keys.add(k)
        return _pcoll[k].icon_id
    except Exception:
        return 0


# ----------------------------------------------------------------------------
# Enum động
# ----------------------------------------------------------------------------
def category_items(self, context):
    global _cat_items
    lib = get_library()
    items = []
    for i, c in enumerate(lib.category_names()):
        n = len(lib.categories[c])
        items.append((c if c else "/", "%s (%d)" % (category_display(c), n), "", "FILE_FOLDER", i))
    if not items:
        items = [(NONE_ID, tr("mtl_empty"), "", "ERROR", 0)]
    _cat_items = items
    return items


def real_category(value):
    """Mã enum -> tên danh mục thật ('/' là thư mục gốc)."""
    if value in (NONE_ID, None):
        return None
    return "" if value == "/" else value


def texture_items(self, context):
    lib = get_library()
    cat = real_category(getattr(self, "category", NONE_ID))
    if cat is None or cat not in lib.categories:
        return [(NONE_ID, "—", "", "BLANK1", 0)]
    cached = _tex_items.get(cat)
    if cached is not None:
        return cached
    items = []
    for i, e in enumerate(lib.categories[cat]):
        icon = _icon_for(e) if i < MAX_PREVIEWS_PER_CATEGORY else 0
        desc = ", ".join(sorted(k.lower() for k in e.maps if k != automtl.DIFFUSE)) or ""
        items.append((e.key, e.name, desc, icon or "IMAGE_DATA", i))
    _tex_items[cat] = items
    return items


# ----------------------------------------------------------------------------
# Truy vấn
# ----------------------------------------------------------------------------
def selected_entry(props):
    lib = get_library()
    if props.texture in (NONE_ID, ""):
        return None
    return lib.by_key(props.texture)


def pool_entries(props):
    """Các texture dùng cho chế độ ngẫu nhiên: danh mục đang chọn (hoặc cả thư viện), lọc theo tên."""
    lib = get_library()
    cat = None if props.pool_all else real_category(props.category)
    if not props.pool_all and cat is None:
        return []
    entries = lib.entries(cat)
    flt = automtl.fold(props.pool_filter) if props.pool_filter.strip() else ""
    if flt:
        words = flt.split()
        entries = [e for e in entries if all(w in automtl.fold(e.name) for w in words)]
    return entries


# ----------------------------------------------------------------------------
def register():
    global _pcoll
    import bpy.utils.previews
    _pcoll = bpy.utils.previews.new()


def unregister():
    global _pcoll, _lib, _root
    if _pcoll is not None:
        try:
            bpy.utils.previews.remove(_pcoll)
        except Exception:
            pass
    _pcoll = None
    _lib = None
    _root = None
    _tex_items.clear()
    _icon_keys.clear()

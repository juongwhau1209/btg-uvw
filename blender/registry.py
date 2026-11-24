# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""Đăng ký/huỷ đăng ký toàn bộ add-on theo đúng thứ tự phụ thuộc."""

from . import (keymaps, live, mtl_library, mtl_ops, mtl_props, mtl_ui, operators, overlay, prefs, props, ui)

_MODULES = (prefs, props, mtl_library, mtl_props, operators, mtl_ops, ui, mtl_ui, live, overlay, keymaps)


def register():
    done = []
    try:
        for m in _MODULES:
            m.register()
            done.append(m)
    except Exception:
        for m in reversed(done):
            try:
                m.unregister()
            except Exception:
                pass
        raise


def unregister():
    for m in reversed(_MODULES):
        try:
            m.unregister()
        except Exception:
            import traceback
            traceback.print_exc()

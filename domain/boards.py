# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""Khổ ván: danh sách dựng sẵn + khổ do người dùng lưu (JSON)."""

import json
import os
from collections import namedtuple

Board = namedtuple("Board", "key label length width builtin")

BUILTIN = (
    Board("2440x1220", "An Cường 2440 x 1220", 2440.0, 1220.0, True),
    Board("2800x1220", "An Cường 2800 x 1220", 2800.0, 1220.0, True),
    Board("1830x915", "Ván 1830 x 915", 1830.0, 915.0, True),
)
CUSTOM_KEY = "CUSTOM"
CUSTOM = Board(CUSTOM_KEY, "Tùy chỉnh (nhập số)", 0.0, 0.0, True)


def board_key(length, width):
    return "%gx%g" % (length, width)


def load_user_boards(path):
    """Đọc danh sách khổ ván người dùng; lỗi file -> danh sách rỗng."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return []
    out = []
    for item in data if isinstance(data, list) else []:
        try:
            length = float(item["length"])
            width = float(item["width"])
        except (KeyError, TypeError, ValueError):
            continue
        if length < 1 or width < 1:
            continue
        label = str(item.get("label") or "%g x %g" % (length, width))
        out.append(Board(board_key(length, width), label, length, width, False))
    return out


def save_user_boards(path, boards):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = [{"label": b.label, "length": b.length, "width": b.width}
            for b in boards if not b.builtin]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def all_boards(user_boards=()):
    """Dựng sẵn + người dùng (loại trùng khóa) + 'Tùy chỉnh' ở cuối."""
    seen = set()
    out = []
    for b in list(BUILTIN) + list(user_boards):
        if b.key in seen:
            continue
        seen.add(b.key)
        out.append(b)
    out.append(CUSTOM)
    return out


def find_board(key, user_boards=()):
    for b in all_boards(user_boards):
        if b.key == key:
            return b
    return None

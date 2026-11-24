# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""Trạng thái chạy (runtime) dùng chung giữa live/overlay/applier.

Chỉ lưu TÊN object (không giữ con trỏ) để an toàn khi Undo/Redo làm Blender tạo lại dữ liệu.
"""

keys = {}        # tên gizmo -> khoá biến đổi lần áp dụng gần nhất
pending = {}     # tên gizmo -> thời điểm (monotonic) yêu cầu cập nhật cuối cùng
sigs = {}        # tên gizmo -> chữ ký topo mesh lần áp dụng gần nhất
info = {}        # tên gizmo -> dict kết quả gần nhất (n_parts, n_faces, ms, frames...)
last_apply = {}  # tên gizmo -> thời điểm áp dụng gần nhất
applying = False


def forget(name):
    for d in (keys, pending, sigs, info, last_apply):
        d.pop(name, None)


def clear():
    global applying
    for d in (keys, pending, sigs, info, last_apply):
        d.clear()
    applying = False

# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""Hệ thống lỗi của BTG.UVW."""


class BtgUvwError(Exception):
    """Lỗi gốc; thông điệp đã sẵn sàng để hiển thị cho người dùng."""


class MeshError(BtgUvwError):
    """Không đọc/ghi được mesh (rỗng, thiếu UV, sai chế độ...)."""


class GizmoError(BtgUvwError):
    """Gizmo không hợp lệ (mất target, ma trận suy biến...)."""

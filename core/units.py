# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""Đơn vị: 1 đơn vị Blender = bao nhiêu mm (theo scene.unit_settings.scale_length)."""

MIN_MM = 1e-3


def unit_mm(scale_length):
    """1 đơn vị Blender bằng bao nhiêu mm."""
    return float(scale_length) * 1000.0


def fmt_mm(value):
    """Định dạng gọn: 2440 -> '2440 mm', 18.5 -> '18.5 mm'."""
    if abs(value - round(value)) < 1e-6:
        return "%d mm" % round(value)
    return "%.1f mm" % value

# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""Chuyển dữ liệu gizmo của add-on cũ "UVW Map (kiểu 3ds Max)" v1.0.0 sang BTG.UVW.

v1 lưu property group `Object.uvw` (IDProperty `obj["uvw"]`); enum được lưu dạng số nguyên
theo thứ tự khai báo trong v1.
"""

V1_MAPPING = ("PLANAR", "CYLINDRICAL", "SPHERICAL", "SHRINK", "BOX", "FACE")
V1_ALIGN = ("X", "Y", "Z")
V1_PRESET = ("2440x1220", "2800x1220", "1830x915", "CUSTOM")

# giá trị mặc định của v1 (khi IDProperty chưa được ghi)
V1_DEFAULTS = {
    "is_gizmo": False, "mapping": 4, "cap": True, "align": 2,
    "flip_u": False, "flip_v": False, "flip_w": False,
    "tile_u": 1.0, "tile_v": 1.0, "real_world": True,
    "tex_preset": 0, "tex_u": 2440.0, "tex_v": 1220.0,
    "uv_map": "", "faces": "", "live": True,
}


def _pick(seq, idx, default):
    try:
        return seq[int(idx)]
    except (IndexError, TypeError, ValueError):
        return default


def is_v1_gizmo(data):
    """data: dict-like của obj["uvw"]."""
    try:
        return bool(data.get("is_gizmo", False))
    except AttributeError:
        return False


def convert_v1(data):
    """dict-like v1 -> dict các trường BTG.UVW (không gồm target/image: là con trỏ ID).

    BOX được chuyển thành grain=LEGACY để UV GIỮ NGUYÊN như đã làm ở v1.
    """
    d = dict(V1_DEFAULTS)
    for k in V1_DEFAULTS:
        try:
            if k in data:
                d[k] = data[k]
        except TypeError:
            pass
    faces = []
    for tok in str(d["faces"]).split():
        try:
            faces.append(int(tok))
        except ValueError:
            faces = []
            break
    return {
        "mapping": _pick(V1_MAPPING, d["mapping"], "BOX"),
        "align": _pick(V1_ALIGN, d["align"], "Z"),
        "cap": bool(d["cap"]),
        "grain": "LEGACY",
        "flip_u": bool(d["flip_u"]), "flip_v": bool(d["flip_v"]), "flip_w": bool(d["flip_w"]),
        "tile_u": float(d["tile_u"]), "tile_v": float(d["tile_v"]),
        "real_world": bool(d["real_world"]),
        "tex_preset": _pick(V1_PRESET, d["tex_preset"], "CUSTOM"),
        "tex_u": float(d["tex_u"]), "tex_v": float(d["tex_v"]),
        "uv_map": str(d["uv_map"]),
        "live": bool(d["live"]),
        "faces": faces,
    }

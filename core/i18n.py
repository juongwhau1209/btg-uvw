# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""Đa ngôn ngữ VI/EN. Mặc định Tiếng Việt (giống các add-on BTG khác)."""

_LANG = "VI"

# key -> (VI, EN)
STR = {
    "panel.main": ("BTG.UVW — UVW Map", "BTG.UVW — UVW Map"),
    "pick_mesh": ("Chọn một mesh để bắt đầu", "Select a mesh to start"),
    "add_box": ("Thêm UVW Map (Box)", "Add UVW Map (Box)"),
    "add_parts": ("Auto theo chi tiết (ván)", "Auto per part (board)"),
    "add_menu": ("Thêm UVW Map…", "Add UVW Map…"),
    "apply_to_selected": ("Áp dụng cho các mesh đang chọn", "Applies to all selected meshes"),
    "migrate_v1": ("Chuyển từ UVW Map v1", "Migrate from UVW Map v1"),
    "target": ("Đối tượng", "Target"),
    "gizmo": ("Gizmo", "Gizmo"),
    "object": ("Object", "Object"),
    "mapping": ("Kiểu mapping", "Mapping type"),
    "axis": ("Trục chiếu", "Projection axis"),
    "cap": ("Cap (nắp trụ)", "Cap"),
    "board": ("Khổ ván / Texture", "Board / Texture"),
    "real_world": ("Kích thước thật (Real-World)", "Real-World size"),
    "fit_gizmo_info": ("Texture phủ vừa khít gizmo", "Texture fits the gizmo"),
    "rotate90": ("Xoay 90°", "Rotate 90°"),
    "length": ("Dài", "Length"),
    "width": ("Rộng", "Width"),
    "grain": ("Vân gỗ", "Wood grain"),
    "grain_axis": ("Hướng vân", "Grain direction"),
    "part_source": ("Chia chi tiết theo", "Split parts by"),
    "part_grain": ("Vân chạy theo cạnh", "Grain follows edge"),
    "random": ("Ngẫu nhiên mỗi chi tiết", "Random per part"),
    "rand_offset": ("Lệch ngẫu nhiên", "Random offset"),
    "rand_rot180": ("Xoay 180° ngẫu nhiên", "Random 180° turn"),
    "seed": ("Seed", "Seed"),
    "reroll": ("Đổi seed", "Reroll"),
    "transform": ("Biến đổi UV", "UV Transform"),
    "tile_u": ("Tile U", "Tile U"),
    "tile_v": ("Tile V", "Tile V"),
    "offset_u": ("Lệch U", "Offset U"),
    "offset_v": ("Lệch V", "Offset V"),
    "rotation": ("Xoay", "Rotation"),
    "flip_u": ("Lật U", "Flip U"),
    "flip_v": ("Lật V", "Flip V"),
    "flip_w": ("Lật W", "Flip W"),
    "gizmo_box": ("Gizmo (kích thước thật)", "Gizmo (real size)"),
    "real_world_hint": ("Real-World: kích thước gizmo không ảnh hưởng UV",
                        "Real-World: gizmo size does not affect UV"),
    "fit": ("Fit", "Fit"),
    "center": ("Center", "Center"),
    "reset": ("Reset", "Reset"),
    "normal_align": ("Normal Align", "Normal Align"),
    "view_align": ("View Align", "View Align"),
    "bitmap_fit": ("Bitmap Fit", "Bitmap Fit"),
    "faces": ("Mặt áp dụng", "Faces"),
    "all_faces": ("Tất cả các mặt", "All faces"),
    "own_faces": ("Chỉ %d mặt được gán", "Only %d assigned faces"),
    "assign_faces": ("Gán mặt đang chọn", "Assign selected"),
    "release_faces": ("Nhả mặt", "Release faces"),
    "only_selected": ("Chỉ mặt đang chọn (Edit)", "Selected faces only (Edit)"),
    "uv_map": ("UV Map", "UV Map"),
    "material": ("Vật liệu / Texture", "Material / Texture"),
    "load_texture": ("Chọn texture…", "Load texture…"),
    "make_material": ("Tạo vật liệu", "Make material"),
    "tools": ("Công cụ", "Tools"),
    "copy_to_selected": ("Sao chép sang mesh khác", "Copy to other meshes"),
    "apply": ("Áp dụng lại UV", "Re-apply UV"),
    "remove": ("Gỡ gizmo (giữ UV)", "Remove gizmo (keep UV)"),
    "live": ("Cập nhật trực tiếp", "Live update"),
    "settings": ("Thiết lập", "Settings"),
    "overlay": ("Hiện hướng vân trên viewport", "Show grain overlay in viewport"),
    "save_board": ("Lưu khổ này", "Save this board"),
    "del_board": ("Xóa khổ này", "Delete this board"),
    "parts_found": ("%d chi tiết", "%d parts"),
    "created": ("Đã tạo %d UVW Map", "Created %d UVW Map(s)"),
    "nothing_to_add": ("Không có mesh nào cần thêm (hoặc đã có UVW Map).",
                       "No mesh to add (or already has a UVW Map)."),
    "need_edit_faces": ("Vào Edit Mode và chọn mặt trước.", "Enter Edit Mode and select faces first."),
    "no_face_selected": ("Chưa chọn mặt nào.", "No face selected."),
    "need_image": ("Chọn ảnh (Bitmap) trước.", "Pick an image first."),
    "language": ("Ngôn ngữ", "Language"),
    "texture_dir": ("Thư mục texture", "Texture folder"),
    "live_delay": ("Độ trễ cập nhật (ms)", "Update delay (ms)"),
    "keymap": ("Phím tắt pie menu (Shift+Alt+U)", "Pie menu hotkey (Shift+Alt+U)"),
    "author": ("Tác giả", "Author"),
    "mtl_root": ("(Thư mục gốc)", "(Root folder)"),
    "mtl_empty": ("(thư viện trống)", "(empty library)"),
    "mtl_lib_pick": ("Chọn thư mục chứa texture (mỗi thư mục con là một danh mục).",
                     "Pick a texture folder (each sub-folder is a category)."),
    "mtl_lib_empty": ("Không tìm thấy ảnh trong thư mục này.", "No images found in this folder."),
    "mtl_lib_truncated": ("Thư mục quá lớn, chỉ quét một phần. Hãy chọn thư mục nhỏ hơn.",
                          "Folder too large: scanned partially. Pick a smaller folder."),
    "mtl_lib_found": ("Thư viện: %d texture trong %d danh mục", "Library: %d textures in %d categories"),
    "mtl_filter": ("Lọc tên", "Name filter"),
    "mtl_pool_count": ("Bộ texture: %d", "Texture set: %d"),
    "mtl_match_by": ("So khớp theo", "Match by"),
    "mtl_apply": ("Áp dụng vật liệu", "Apply materials"),
    "mtl_checkmap": ("Check Map", "Check Map"),
    "mtl_preview": ("Xem thử", "Preview"),
    "mtl_cleanup": ("Dọn vật liệu thừa", "Clean unused"),
    "mtl_need_mesh": ("Chọn ít nhất một mesh.", "Select at least one mesh."),
    "mtl_need_texture": ("Chọn một texture trong thư viện trước.", "Pick a texture from the library first."),
    "mtl_need_pool": ("Không có texture nào trong bộ (kiểm tra danh mục hoặc ô lọc tên).",
                      "No textures in the set (check the category or name filter)."),
    "mtl_need_rules": ("Chưa có quy tắc. Ví dụ: canh=Gỗ 01; than tu=Gỗ 02",
                       "No rules. Example: door=Wood 01; carcass=Wood 02"),
    "mtl_rule_missing": ("Không tìm thấy texture '%s' cho quy tắc.", "Texture '%s' not found for a rule."),
    "mtl_warn_gizmo_material": ("%s: gizmo Auto đang chia chi tiết theo Material; sau khi gán, hãy đổi sang Island.",
                                "%s: the Auto gizmo splits parts by Material; switch it to Island afterwards."),
    "mtl_done": ("Đã gán %d vật liệu cho %d object", "Assigned %d material(s) on %d object(s)"),
    "mtl_checkmap_on": ("Check Map đang gán cho %d object", "Check Map applied to %d object(s)"),
    "mtl_restored": ("Đã khôi phục %d object", "Restored %d object(s)"),
    "mtl_cleaned": ("Đã dọn %d vật liệu, %d ảnh", "Removed %d material(s), %d image(s)"),
}


def set_language(lang):
    global _LANG
    _LANG = "EN" if str(lang).upper().startswith("EN") else "VI"


def get_language():
    return _LANG


def tr(key, *args):
    pair = STR.get(key)
    text = key if pair is None else pair[1 if _LANG == "EN" else 0]
    if args:
        try:
            return text % args
        except (TypeError, ValueError):
            return text
    return text

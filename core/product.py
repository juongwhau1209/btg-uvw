# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""Nguồn sự thật duy nhất về danh tính sản phẩm BTG.UVW.

Mọi chỗ khác (manifest, panel, log, tên operator, thư mục dữ liệu) đều đọc từ đây.
"""

PRODUCT_ID = "btg_uvw"
PRODUCT_NAME = "BTG.UVW"
PRODUCT_TAGLINE = "UVW Map kiểu 3ds Max cho nội thất: kích thước ván thật, vân gỗ đúng hướng"
VERSION = (1, 1, 0)
VERSION_STR = ".".join(str(v) for v in VERSION)

OWNER = "Trần Duy Dương"
OWNER_EMAIL = "ktsduongtran.architect@gmail.com"
COPYRIGHT = "© 2026 Trần Duy Dương"
LICENSE_SPDX = "GPL-3.0-or-later"

OPERATOR_PREFIX = "btg_uvw"          # bl_idname: btg_uvw.xxx
PROP_PREFIX = "btg_uvw_"             # thuộc tính/attribute do add-on tạo
PANEL_CATEGORY = "BTG UVW"           # tab trong N-panel
DATA_DIR_NAME = ".btg/btg_uvw"       # nằm dưới thư mục home của người dùng

FACE_OWNER_ATTR = "btg_uvw_id"       # INT / FACE: gizmo nào sở hữu mặt này (0 = chưa ai)
GIZMO_PREFIX = "UVW_"                # tiền tố tên Empty gizmo
MATERIAL_PREFIX = "BTG_UVW_"         # tiền tố tên material do add-on tạo


def op_id(name):
    """Tên đầy đủ của operator: op_id('apply') -> 'btg_uvw.apply'."""
    return "%s.%s" % (OPERATOR_PREFIX, name)

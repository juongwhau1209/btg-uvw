# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""Auto MTL — logic thuần (không bpy): quét thư viện texture, nhận diện các map đi kèm,
quy tắc gán theo tên, chia ngẫu nhiên ổn định, và ảnh Check Map.

Thư viện là THƯ MỤC CỦA NGƯỜI DÙNG: mỗi thư mục con là một danh mục; ảnh cùng "tên gốc" được gộp
thành một vật liệu (vd. `Gỗ 01.jpg` + `Gỗ 01_normal.jpg` + `Gỗ 01_rough.jpg`).
"""

import os
import random
import re
import time
import unicodedata
from dataclasses import dataclass, field

import numpy as np

IMAGE_EXTS = frozenset({".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".tga", ".webp", ".exr", ".hdr"})
THUMB_DIRS = frozenset({"thumbnail", "thumbnails", "thumb", "thumbs", "preview", "previews"})
MAX_DEPTH = 4
MAX_ENTRIES = 5000
MAX_DIRS = 2500            # chặn quét nhầm vào thư mục khổng lồ (vd. cả ổ đĩa)
TIME_BUDGET_S = 4.0

DIFFUSE, NORMAL, ROUGHNESS, GLOSS, BUMP, AO, METALLIC, OPACITY = (
    "DIFFUSE", "NORMAL", "ROUGHNESS", "GLOSS", "BUMP", "AO", "METALLIC", "OPACITY")

_SUFFIX = {
    DIFFUSE: ("diff", "diffuse", "albedo", "color", "colour", "col", "basecolor", "base_color", "bc"),
    NORMAL: ("nor", "nrm", "norm", "normal", "normalgl", "normaldx", "normal_gl", "normal_dx", "nor_gl", "nor_dx"),
    ROUGHNESS: ("rough", "roughness", "rgh"),
    GLOSS: ("gloss", "glossiness", "glos"),
    BUMP: ("bump", "height", "disp", "displacement", "hgt"),
    AO: ("ao", "occlusion", "ambientocclusion", "ambient_occlusion"),
    METALLIC: ("metal", "metallic", "metalness", "met"),
    OPACITY: ("opacity", "alpha", "mask", "transparency"),
}
_TOKEN_KIND = {tok: kind for kind, toks in _SUFFIX.items() for tok in toks}

COLORSPACE = {DIFFUSE: "sRGB", NORMAL: "Non-Color", ROUGHNESS: "Non-Color", GLOSS: "Non-Color",
              BUMP: "Non-Color", AO: "Non-Color", METALLIC: "Non-Color", OPACITY: "Non-Color"}

_SEP = re.compile(r"[\s_\-.]+")


# ----------------------------------------------------------------------------
# Chuẩn hoá tên
# ----------------------------------------------------------------------------
def fold(text):
    """Chữ thường, bỏ dấu tiếng Việt, gộp khoảng trắng: để so khớp tên không phân biệt dấu/hoa thường."""
    text = unicodedata.normalize("NFD", str(text).replace("đ", "d").replace("Đ", "D"))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return " ".join(_SEP.split(text.lower().strip())).strip()


def natural_key(text):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", fold(text))]


def classify(stem):
    """'Gỗ 01_normal' -> ('Gỗ 01', NORMAL); không có hậu tố -> (stem, DIFFUSE)."""
    stem = re.sub(r"[\s_\-.]+map$", "", stem, flags=re.I) or stem     # 'wood_normal_map' -> 'wood_normal'
    parts = [p for p in re.split(r"([\s_\-.]+)", stem)]
    toks = [(i, p) for i, p in enumerate(parts) if p and not _SEP.fullmatch(p)]
    if len(toks) >= 2:
        for n in (2, 1):                          # thử hậu tố 2 từ ('base_color') rồi 1 từ
            if len(toks) <= n:
                continue
            tail = toks[-n:]
            key = "_".join(t.lower() for _, t in tail)
            kind = _TOKEN_KIND.get(key) or _TOKEN_KIND.get(key.replace("_", ""))
            if kind:
                base = "".join(parts[:tail[0][0]]).rstrip(" _-.")
                if base:
                    return base, kind
    return stem, DIFFUSE


# ----------------------------------------------------------------------------
# Thư viện
# ----------------------------------------------------------------------------
@dataclass
class Entry:
    name: str
    category: str
    maps: dict = field(default_factory=dict)      # kind -> đường dẫn ảnh
    thumb: str = ""

    @property
    def diffuse(self):
        return self.maps.get(DIFFUSE, "")

    @property
    def key(self):
        return "%s::%s" % (self.category, self.name)


@dataclass
class Library:
    root: str = ""
    categories: dict = field(default_factory=dict)  # tên danh mục -> [Entry]
    truncated: bool = False                          # quét dừng sớm vì quá lớn

    def category_names(self):
        return sorted(self.categories, key=natural_key)

    def entries(self, category=None):
        if category is None:
            return [e for c in self.category_names() for e in self.categories[c]]
        return list(self.categories.get(category, ()))

    def count(self):
        return sum(len(v) for v in self.categories.values())

    def by_key(self, key):
        cat, _, name = str(key).partition("::")
        for e in self.categories.get(cat, ()):
            if e.name == name:
                return e
        return None

    def find(self, query, prefer_category=None):
        """Tìm theo 'Danh mục/Tên' hoặc chỉ 'Tên' (khớp đúng, rồi khớp chứa); ưu tiên danh mục đang chọn."""
        q = str(query).strip()
        if not q:
            return None
        cat_q = None
        if "/" in q or "\\" in q:
            cat_q, _, q = q.replace("\\", "/").rpartition("/")
        fq = fold(q)
        pool = self.entries()
        if cat_q:
            fc = fold(cat_q)
            pool = [e for e in pool if fold(e.category).endswith(fc)]
        pool.sort(key=lambda e: (e.category != prefer_category, natural_key(e.category), natural_key(e.name)))
        for e in pool:
            if fold(e.name) == fq:
                return e
        for e in pool:
            if fq and fq in fold(e.name):
                return e
        return None


def scan_library(root, max_depth=MAX_DEPTH, max_entries=MAX_ENTRIES, max_dirs=MAX_DIRS,
                 time_budget=TIME_BUDGET_S):
    """Quét `root`: mỗi thư mục chứa ảnh là một danh mục (đường dẫn tương đối, '' = thư mục gốc).

    Thư mục tên Thumbnail/Preview... không thành danh mục; ảnh trong đó cùng tên với texture được dùng làm
    ảnh xem trước. Bỏ qua mục chỉ có normal/rough... mà không có ảnh màu.
    """
    lib = Library(root=str(root))
    if not root or not os.path.isdir(root):
        return lib
    root = os.path.abspath(root)
    base_depth = root.rstrip(os.sep).count(os.sep)
    thumbs = {}
    groups = {}
    total = 0
    visited = 0
    t_end = time.monotonic() + time_budget
    for cur, dirs, files in os.walk(root):
        visited += 1
        if visited > max_dirs or time.monotonic() > t_end:
            lib.truncated = True
            break
        depth = cur.rstrip(os.sep).count(os.sep) - base_depth
        dirs[:] = sorted(d for d in dirs if not d.startswith(".")) if depth < max_depth else []
        imgs = sorted(f for f in files if os.path.splitext(f)[1].lower() in IMAGE_EXTS)
        if not imgs:
            continue
        leaf = os.path.basename(cur).lower()
        if leaf in THUMB_DIRS:
            parent = os.path.dirname(cur)
            for f in imgs:
                thumbs[(parent, fold(os.path.splitext(f)[0]))] = os.path.join(cur, f)
            continue
        rel = os.path.relpath(cur, root)
        category = "" if rel == "." else rel.replace(os.sep, "/")
        for f in imgs:
            base, kind = classify(os.path.splitext(f)[0])
            g = groups.setdefault((cur, category, fold(base)), {"name": base, "maps": {}})
            g["maps"].setdefault(kind, os.path.join(cur, f))
            total += 1
        if total >= max_entries:
            lib.truncated = True
            break
    for (cur, category, fname), g in groups.items():
        if DIFFUSE not in g["maps"]:
            continue
        e = Entry(name=g["name"], category=category, maps=g["maps"],
                  thumb=thumbs.get((cur, fname), ""))
        lib.categories.setdefault(category, []).append(e)
    for v in lib.categories.values():
        v.sort(key=lambda e: natural_key(e.name))
    return lib


# ----------------------------------------------------------------------------
# Quy tắc gán theo tên
# ----------------------------------------------------------------------------
def parse_rules(text):
    """'door=Wood 01; carcass: Gỗ/Sồi 02' -> [('door','Wood 01'), ('carcass','Gỗ/Sồi 02')].

    Phân tách bằng xuống dòng hoặc ';'. Dấu phân khoá/giá trị: '=', ':' hoặc '->'.
    """
    rules = []
    for chunk in re.split(r"[\n;]+", str(text or "")):
        chunk = chunk.strip()
        if not chunk:
            continue
        m = re.match(r"^(.*?)\s*(?:->|=|:)\s*(.+)$", chunk)
        if not m or not m.group(1).strip():
            continue
        rules.append((fold(m.group(1)), m.group(2).strip()))
    return rules


def match_rule(name, rules):
    """Giá trị của quy tắc đầu tiên mà khoá nằm trong `name` (không phân biệt dấu/hoa thường); hoặc None."""
    f = fold(name)
    for key, value in rules:
        if key and key in f:
            return value
    return None


# ----------------------------------------------------------------------------
# Chia ngẫu nhiên ổn định
# ----------------------------------------------------------------------------
def pick_indices(count, n_choices, seed):
    """`count` lựa chọn trong [0, n_choices): cân bằng (dùng hết mọi mẫu trước khi lặp), không trùng
    liền kề khi có thể, cùng seed cho cùng kết quả."""
    if count <= 0 or n_choices <= 0:
        return []
    rng = random.Random(int(seed))
    out = []
    while len(out) < count:
        perm = list(range(n_choices))
        rng.shuffle(perm)
        if out and n_choices > 1 and perm[0] == out[-1]:
            perm[0], perm[1] = perm[1], perm[0]
        out.extend(perm)
    return out[:count]


def build_slots(keys):
    """Danh sách khoá vật liệu theo từng chi tiết -> (khoá duy nhất theo thứ tự xuất hiện, chỉ số slot mỗi chi tiết)."""
    order, index = [], {}
    part_to_slot = []
    for k in keys:
        if k not in index:
            index[k] = len(order)
            order.append(k)
        part_to_slot.append(index[k])
    return order, part_to_slot


def face_slot_index(labels, part_to_slot):
    return np.asarray(part_to_slot, dtype=np.int32)[np.asarray(labels, dtype=np.int64)]


def fit_board_v(tex_u, img_w, img_h):
    """Texture rộng = dài × (cao ảnh / rộng ảnh): khung ván cùng tỉ lệ với ảnh."""
    if img_w <= 0 or img_h <= 0:
        return None
    return float(tex_u) * img_h / img_w


def material_name(prefix, name, category="", uv_name="", clash=False):
    base = prefix + name
    if clash and category:
        base = prefix + category.replace("/", " ") + " " + name
    return base + ("@" + uv_name if uv_name else "")


# ----------------------------------------------------------------------------
# Ảnh Check Map
# ----------------------------------------------------------------------------
def checkmap_pixels(width=1024, height=512):
    """Ảnh kiểm tra hướng UV (float32 (H, W, 4), hàng 0 = đáy ảnh như Blender):

    nền sọc ngang + lưới 8×4 ô vuông, mỗi ô có một chữ F nhỏ (bất đối xứng nên lật gương hay xoay đều
    thấy ngay), bốn góc tô bốn màu khác nhau (đáy-trái đen, đáy-phải đỏ, đỉnh-trái xanh lá, đỉnh-phải
    xanh dương), mũi tên đỏ chỉ +U dọc đáy và mũi tên xanh chỉ +V dọc cạnh trái.
    """
    h, w = int(height), int(width)
    yy, xx = np.mgrid[0:h, 0:w]
    u = (xx + 0.5) / w
    v = (yy + 0.5) / h
    stripe = ((yy // max(h // 64, 1)) % 2).astype(np.float32)
    g = 0.86 + 0.10 * stripe
    img = np.stack([g, g, g, np.ones_like(g)], axis=-1).astype(np.float32)

    grid = ((np.abs(u * 8 - np.round(u * 8)) < 0.0035) | (np.abs(v * 4 - np.round(v * 4)) < 0.007))
    img[grid, :3] = (0.55, 0.62, 0.72)

    def paint(mask, rgb):
        img[mask, :3] = rgb

    # lưới 8×4 ô vuông (mỗi ô 1/8 tile): ô xen kẽ hơi tối + một chữ F nhỏ trong MỖI ô,
    # nên chi tiết nhỏ chỉ chiếm một phần tile vẫn thấy rõ hướng và lật gương
    ci, cj = np.floor(u * 8).astype(int), np.floor(v * 4).astype(int)
    img[((ci + cj) % 2 == 1), :3] *= 0.93
    cu, cv = (u * 8) % 1.0, (v * 4) % 1.0
    stem = (cu >= 0.30) & (cu <= 0.42) & (cv >= 0.16) & (cv <= 0.84)
    top = (cu >= 0.30) & (cu <= 0.74) & (cv >= 0.70) & (cv <= 0.84)
    mid = (cu >= 0.30) & (cu <= 0.62) & (cv >= 0.46) & (cv <= 0.58)
    paint(stem | top | mid, (0.10, 0.10, 0.12))

    # mũi tên +U (đỏ) dọc đáy
    shaft = (v >= 0.045) & (v <= 0.065) & (u >= 0.08) & (u <= 0.30)
    head = (u >= 0.30) & (u <= 0.36) & (np.abs(v - 0.055) <= (0.36 - u) * 0.55)
    paint(shaft | head, (0.85, 0.12, 0.10))
    # mũi tên +V (xanh lá) dọc cạnh trái
    shaft = (u >= 0.0225) & (u <= 0.0425) & (v >= 0.18) & (v <= 0.62)
    head = (v >= 0.62) & (v <= 0.74) & (np.abs(u - 0.0325) <= (0.74 - v) * 0.22)
    paint(shaft | head, (0.12, 0.65, 0.20))

    # bốn góc
    cs, cv = 0.07, 0.14
    paint((u < cs) & (v < cv), (0.05, 0.05, 0.05))
    paint((u > 1 - cs) & (v < cv), (0.85, 0.12, 0.10))
    paint((u < cs) & (v > 1 - cv), (0.12, 0.65, 0.20))
    paint((u > 1 - cs) & (v > 1 - cv), (0.12, 0.30, 0.85))

    # viền ngoài (ranh giới một tile)
    edge = (xx < 2) | (xx >= w - 2) | (yy < 2) | (yy >= h - 2)
    paint(edge, (0.1, 0.1, 0.1))
    return np.clip(img, 0.0, 1.0)

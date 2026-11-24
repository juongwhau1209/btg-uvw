# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tạo vật liệu từ ảnh texture: UV Map -> Image Texture -> Principled BSDF."""

import os

import bpy

from ..core import product


def load_image(filepath):
    return bpy.data.images.load(filepath, check_existing=True)


def _uv_name(obj, uv_name):
    if uv_name:
        return uv_name
    layer = obj.data.uv_layers.active
    return layer.name if layer else "UVMap"


def make_material(obj, image, uv_name=""):
    """Material 'BTG_UVW_<ảnh>' dùng đúng UV map của gizmo; tái sử dụng nếu đã có."""
    base = os.path.splitext(image.name)[0]
    name = product.MATERIAL_PREFIX + base
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    try:
        mat.use_nodes = True           # Blender 5.x: deprecated nhưng vẫn hợp lệ
    except Exception:
        pass
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    tex = nt.nodes.new("ShaderNodeTexImage")
    uvn = nt.nodes.new("ShaderNodeUVMap")
    uvn.uv_map = _uv_name(obj, uv_name)
    tex.image = image
    tex.extension = "REPEAT"
    try:
        bsdf.inputs["Roughness"].default_value = 0.45
    except KeyError:
        pass
    uvn.location = (-700, 0)
    tex.location = (-450, 0)
    bsdf.location = (-150, 0)
    out.location = (150, 0)
    nt.links.new(uvn.outputs["UV"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def assign(obj, mat):
    mats = obj.data.materials
    if len(mats):
        mats[0] = mat
    else:
        mats.append(mat)


# ============================================================================
# Auto MTL: vật liệu PBR từ một Entry của thư viện
# ============================================================================
import json
from dataclasses import dataclass

import numpy as np

from ..domain import automtl

CHECKMAP_NAME = product.MATERIAL_PREFIX + "CheckMap"
BACKUP_KEY = "btg_uvw_mtl_bak"
AUTO_FLAG = "btg_uvw_auto"


@dataclass(frozen=True)
class MtlSettings:
    use_maps: bool = True
    roughness: float = 0.45
    specular: float = 0.5
    bump_strength: float = 0.3

    def sig(self):
        return "%d|%.3f|%.3f|%.3f" % (self.use_maps, self.roughness, self.specular, self.bump_strength)


def settings_from(props):
    return MtlSettings(bool(props.use_maps), float(props.roughness), float(props.specular),
                       float(props.bump_strength))


def _set_input(node, names, value):
    for n in names:
        sock = node.inputs.get(n)
        if sock is not None:
            sock.default_value = value
            return True
    return False


def _image(path, kind):
    img = load_image(path)
    img[AUTO_FLAG] = 1
    try:
        img.colorspace_settings.name = automtl.COLORSPACE[kind]
    except (TypeError, KeyError):
        pass
    return img


def _entry_sig(entry, settings, uv_name):
    return "|".join([uv_name, settings.sig()] + ["%s=%s" % (k, entry.maps[k]) for k in sorted(entry.maps)])


def _build_pbr(mat, entry, uv_name, settings):
    try:
        mat.use_nodes = True
    except Exception:
        pass
    nt = mat.node_tree
    nt.nodes.clear()
    new = nt.nodes.new
    link = nt.links.new
    out = new("ShaderNodeOutputMaterial")
    bsdf = new("ShaderNodeBsdfPrincipled")
    uvn = new("ShaderNodeUVMap")
    uvn.uv_map = uv_name
    out.location, bsdf.location, uvn.location = (300, 0), (0, 0), (-1000, 0)
    link(bsdf.outputs["BSDF"], out.inputs["Surface"])
    _set_input(bsdf, ("Roughness",), settings.roughness)
    _set_input(bsdf, ("Specular IOR Level", "Specular"), settings.specular)

    maps = dict(entry.maps) if settings.use_maps else {automtl.DIFFUSE: entry.diffuse}
    row = [0]

    def tex(kind):
        n = new("ShaderNodeTexImage")
        n.image = _image(maps[kind], kind)
        n.extension = "REPEAT"
        n.location = (-700, -row[0] * 300)
        row[0] += 1
        link(uvn.outputs["UV"], n.inputs["Vector"])
        return n

    color_src = tex(automtl.DIFFUSE).outputs["Color"]
    if automtl.AO in maps:
        mix = new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.location = (-420, 120)
        mix.inputs[0].default_value = 1.0
        rgba = [s for s in mix.inputs if s.type == "RGBA"]
        link(color_src, rgba[0])
        link(tex(automtl.AO).outputs["Color"], rgba[1])
        color_src = [s for s in mix.outputs if s.type == "RGBA"][0]
    link(color_src, bsdf.inputs["Base Color"])

    if automtl.ROUGHNESS in maps:
        link(tex(automtl.ROUGHNESS).outputs["Color"], bsdf.inputs["Roughness"])
    elif automtl.GLOSS in maps:
        inv = new("ShaderNodeInvert")
        inv.location = (-420, -300)
        link(tex(automtl.GLOSS).outputs["Color"], inv.inputs["Color"])
        link(inv.outputs["Color"], bsdf.inputs["Roughness"])
    if automtl.METALLIC in maps:
        link(tex(automtl.METALLIC).outputs["Color"], bsdf.inputs["Metallic"])
    if automtl.OPACITY in maps:
        link(tex(automtl.OPACITY).outputs["Color"], bsdf.inputs["Alpha"])

    normal_out = None
    if automtl.NORMAL in maps:
        nm = new("ShaderNodeNormalMap")
        nm.location = (-420, -600)
        link(tex(automtl.NORMAL).outputs["Color"], nm.inputs["Color"])
        normal_out = nm.outputs["Normal"]
    if automtl.BUMP in maps:
        bump = new("ShaderNodeBump")
        bump.location = (-200, -700)
        bump.inputs["Strength"].default_value = settings.bump_strength
        link(tex(automtl.BUMP).outputs["Color"], bump.inputs["Height"])
        if normal_out is not None:
            link(normal_out, bump.inputs["Normal"])
        normal_out = bump.outputs["Normal"]
    if normal_out is not None:
        link(normal_out, bsdf.inputs["Normal"])


def get_or_build(entry, uv_name="", settings=None, clash=False):
    """Vật liệu PBR của `entry`; dùng lại nếu đã tạo với đúng nội dung, dựng lại nếu khác."""
    settings = settings or MtlSettings()
    name = automtl.material_name(product.MATERIAL_PREFIX, entry.name, entry.category, uv_name, clash)
    mat = bpy.data.materials.get(name)
    sig = _entry_sig(entry, settings, uv_name)
    if mat is not None and mat.get(AUTO_FLAG) and mat.get("btg_uvw_sig") != sig \
            and mat.get("btg_uvw_src") != entry.diffuse and not clash:
        # trùng tên nhưng khác ảnh (danh mục khác): dùng tên có danh mục
        return get_or_build(entry, uv_name, settings, clash=True)
    if mat is None:
        mat = bpy.data.materials.new(name)
    if mat.get("btg_uvw_sig") != sig or mat.node_tree is None:
        _build_pbr(mat, entry, uv_name, settings)
        mat[AUTO_FLAG] = 1
        mat["btg_uvw_sig"] = sig
        mat["btg_uvw_src"] = entry.diffuse
    return mat


# ----------------------------------------------------------------------------
# Gán vật liệu / chỉ số slot
# ----------------------------------------------------------------------------
def assign_all(obj, mat, replace=True):
    me = obj.data
    if replace:
        me.materials.clear()
        me.materials.append(mat)
        set_face_slots(obj, np.zeros(len(me.polygons), dtype=np.int32))
    else:
        assign(obj, mat)


def set_face_slots(obj, idx):
    me = obj.data
    if len(me.polygons):
        me.polygons.foreach_set("material_index", np.asarray(idx, dtype=np.int32))
        me.update()


def assign_slots(obj, mats, face_idx):
    """Thay toàn bộ slot bằng `mats` và gán chỉ số slot theo từng mặt."""
    me = obj.data
    me.materials.clear()
    for m in mats:
        me.materials.append(m)
    set_face_slots(obj, face_idx)


# ----------------------------------------------------------------------------
# Check Map
# ----------------------------------------------------------------------------
def checkmap_image():
    img = bpy.data.images.get(CHECKMAP_NAME)
    if img is None:
        w, h = 1024, 512
        img = bpy.data.images.new(CHECKMAP_NAME, w, h, alpha=False)
        img.pixels.foreach_set(automtl.checkmap_pixels(w, h).ravel())
        img.update()
        try:
            img.pack()
        except Exception:
            pass
    img[AUTO_FLAG] = 1
    return img


def checkmap_material():
    mat = bpy.data.materials.get(CHECKMAP_NAME)
    if mat is None:
        mat = bpy.data.materials.new(CHECKMAP_NAME)
    if mat.node_tree is None or not mat.get(AUTO_FLAG):
        try:
            mat.use_nodes = True
        except Exception:
            pass
        nt = mat.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        emi = nt.nodes.new("ShaderNodeEmission")
        tex = nt.nodes.new("ShaderNodeTexImage")
        uvn = nt.nodes.new("ShaderNodeUVMap")
        tex.image = checkmap_image()
        tex.extension = "REPEAT"
        out.location, emi.location, tex.location, uvn.location = (300, 0), (50, 0), (-300, 0), (-600, 0)
        nt.links.new(uvn.outputs["UV"], tex.inputs["Vector"])
        nt.links.new(tex.outputs["Color"], emi.inputs["Color"])
        nt.links.new(emi.outputs["Emission"], out.inputs["Surface"])
        mat[AUTO_FLAG] = 1
    return mat


def backup_slots(obj):
    """Nhớ tên các material slot hiện có (chỉ lần đầu, để bấm Check Map nhiều lần không mất bản gốc)."""
    if BACKUP_KEY in obj:
        return False
    obj[BACKUP_KEY] = json.dumps([m.name if m else "" for m in obj.data.materials])
    return True


def restore_slots(obj):
    raw = obj.get(BACKUP_KEY)
    if raw is None:
        return False
    names = json.loads(raw)
    me = obj.data
    me.materials.clear()
    for n in names:
        me.materials.append(bpy.data.materials.get(n) if n else None)
    del obj[BACKUP_KEY]
    return True


def apply_checkmap(obj):
    me = obj.data
    backup_slots(obj)
    mat = checkmap_material()
    if len(me.materials) == 0:
        me.materials.append(mat)
    else:
        for i in range(len(me.materials)):
            me.materials[i] = mat


# ----------------------------------------------------------------------------
# Dọn dẹp
# ----------------------------------------------------------------------------
def cleanup(include_images=True):
    """Xoá vật liệu (và ảnh) do Auto MTL tạo mà không còn ai dùng. Trả về (số vật liệu, số ảnh)."""
    mats = [m for m in bpy.data.materials
            if m.get(AUTO_FLAG) and m.users == 0 and not m.use_fake_user]
    for m in mats:
        bpy.data.materials.remove(m)
    n_img = 0
    if include_images:
        imgs = [i for i in bpy.data.images if i.get(AUTO_FLAG) and i.users == 0 and not i.use_fake_user]
        for i in imgs:
            bpy.data.images.remove(i)
        n_img = len(imgs)
    return len(mats), n_img

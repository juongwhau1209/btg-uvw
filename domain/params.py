# SPDX-FileCopyrightText: 2026 Trần Duy Dương
# SPDX-License-Identifier: GPL-3.0-or-later
"""Cấu trúc dữ liệu vào/ra của engine UVW (thuần Python + numpy)."""

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

MAPPINGS = ("BOX", "PLANAR", "CYLINDRICAL", "SPHERICAL", "SHRINK", "FACE", "PARTS")
GRAINS = ("LEGACY", "X", "Y", "Z")
PART_SOURCES = ("ISLAND", "MATERIAL", "OBJECT")
PART_GRAINS = ("LONGEST", "MIDDLE", "SHORTEST")


@dataclass
class MapParams:
    mapping: str = "BOX"
    align: str = "Z"            # trục chiếu cho Planar/Cylindrical/Spherical/Shrink
    cap: bool = True            # Cylindrical: nắp trụ chiếu phẳng
    grain: str = "X"            # Box: hướng vân theo trục gizmo (LEGACY = kiểu v1)
    flip_u: bool = False
    flip_v: bool = False
    flip_w: bool = False
    tile_u: float = 1.0
    tile_v: float = 1.0
    offset_u: float = 0.0
    offset_v: float = 0.0
    rotation: float = 0.0       # độ, quanh tâm tile
    real_world: bool = True
    tex_u: float = 2440.0       # mm
    tex_v: float = 1220.0       # mm
    part_source: str = "ISLAND"
    part_grain: str = "LONGEST"
    rand_offset: bool = False
    rand_rot180: bool = False
    seed: int = 1
    scope: str = "ALL"          # ALL | OWNED
    uid: int = 0                # mã gizmo trong attribute sở hữu mặt


@dataclass
class GizmoFrame:
    """Khung gizmo so với object.

    obj_to_gizmo: ma trận 4x4 (object -> toạ độ gizmo đơn vị, khối [-0.5, 0.5]).
    size_mm:      kích thước gizmo theo 3 trục, mm (đã lấy trị tuyệt đối, kẹp tối thiểu).
    obj_scale_mm: tỉ lệ object -> mm theo 3 trục object (cho chế độ PARTS).
    """
    obj_to_gizmo: np.ndarray = field(default_factory=lambda: np.eye(4))
    size_mm: np.ndarray = field(default_factory=lambda: np.array([1000.0, 1000.0, 1000.0]))
    obj_scale_mm: np.ndarray = field(default_factory=lambda: np.array([1000.0, 1000.0, 1000.0]))


@dataclass
class MeshData:
    """Mesh dạng mảng phẳng (đa giác bất kỳ, loop liên tục theo từng mặt)."""
    co: np.ndarray                      # (V,3) float64, toạ độ object
    loop_vert: np.ndarray               # (L,) int
    face_start: np.ndarray              # (F,) int
    face_len: np.ndarray                # (F,) int
    material_index: Optional[np.ndarray] = None   # (F,) int
    face_owner: Optional[np.ndarray] = None       # (F,) int
    face_mask: Optional[np.ndarray] = None        # (F,) bool: giới hạn thêm (vd. mặt đang chọn)

    @property
    def n_faces(self):
        return int(len(self.face_start))

    @property
    def n_loops(self):
        return int(len(self.loop_vert))

    def face_of_loop(self):
        return np.repeat(np.arange(self.n_faces), self.face_len)


@dataclass
class PartFrame:
    """Khung OBB của một chi tiết, trong không gian object-mm."""
    label: int
    center: np.ndarray       # (3,)
    axes: np.ndarray         # (3,3) hàng = trục đơn vị, đã sắp: dài, giữa, ngắn
    extent: np.ndarray       # (3,) mm theo từng trục
    grain_axis: int = 0


@dataclass
class MapResult:
    uv: np.ndarray                      # (L,2)
    face_sel: np.ndarray                # (F,) bool
    loop_sel: np.ndarray                # (L,) bool
    labels: Optional[np.ndarray] = None
    n_parts: int = 0
    frames: List[PartFrame] = field(default_factory=list)

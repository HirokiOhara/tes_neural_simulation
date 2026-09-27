"""
神経線維パス情報の管理（COMSOL座標系）

パスCSVは MATLAB で生成され、arc_length（累積距離[mm]）を含む。
COMSOL CSV とパスCSV はデータ行が同順で対応する。
"""
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict
from pathlib import Path

MM_TO_UM = 1e3

# パスCSVの列名
COL_UNIT_ID = "fiber_id"
COL_ARC_LENGTH = "arc_length"
COL_X = "x"
COL_Y = "y"
COL_Z = "z"


@dataclass
class FiberPathData:
    """
    神経線維のパス情報

    Attributes
    ----------
    unit_ids : (N,) 各データ行の fiber_id
    arc_length_mm : (N,) 各データ行の累積距離 [mm]
    xyz : (N, 3) 各データ行の3D座標 [mm]
    """
    unit_ids: np.ndarray
    arc_length_mm: np.ndarray
    xyz: np.ndarray

    _point_indices: Dict[int, np.ndarray] = field(default_factory=dict, repr=False)
    _cumulative_dx_um: Dict[int, np.ndarray] = field(default_factory=dict, repr=False)
    _fiber_lengths_um: Dict[int, float] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        uids = np.unique(self.unit_ids).astype(int)
        for uid in uids:
            uid = int(uid)
            idx = np.where(self.unit_ids == uid)[0]
            self._point_indices[uid] = idx

            arc_um = self.arc_length_mm[idx] * MM_TO_UM
            self._cumulative_dx_um[uid] = arc_um
            self._fiber_lengths_um[uid] = float(arc_um[-1]) if len(arc_um) else float("nan")

    # ---- factory ----
    @classmethod
    def from_csv(cls, filepath) -> "FiberPathData":
        """パスCSV（ヘッダー付き）を読み込む"""
        df = pd.read_csv(filepath, encoding="utf-8-sig")
        return cls(
            unit_ids=df[COL_UNIT_ID].to_numpy(dtype=int),
            arc_length_mm=df[COL_ARC_LENGTH].to_numpy(dtype=float),
            xyz=df[[COL_X, COL_Y, COL_Z]].to_numpy(dtype=float),
        )

    # ---- accessors ----
    def get_unit_ids(self) -> np.ndarray:
        return np.array(sorted(self._fiber_lengths_um.keys()))

    def get_point_indices(self, unit_id: int) -> np.ndarray:
        """指定unit_idのデータ行インデックス（COMSOL配列スライス用）"""
        return self._point_indices.get(unit_id, np.array([], dtype=int))

    def get_cumulative_dx_um(self, unit_id: int) -> np.ndarray:
        return self._cumulative_dx_um.get(unit_id, np.array([]))

    def get_fiber_length_um(self, unit_id: int) -> float:
        return self._fiber_lengths_um.get(unit_id, float("nan"))

    def get_all_fiber_lengths_um(self) -> Dict[int, float]:
        return self._fiber_lengths_um.copy()

    def get_xyz_coords(self, unit_id: int) -> np.ndarray:
        """指定unit_idの3D座標 (P, 3) [mm]"""
        idx = self.get_point_indices(unit_id)
        return self.xyz[idx].copy() if len(idx) else np.empty((0, 3))

    def interpolate_1d_to_3d(self, unit_id: int, positions_1d_um: np.ndarray) -> np.ndarray:
        """1D軸索位置[um] → 3D座標[mm]（線形補間）"""
        dx = self.get_cumulative_dx_um(unit_id)
        xyz = self.get_xyz_coords(unit_id)

        pos = np.asarray(positions_1d_um, dtype=float).ravel()
        if len(dx) == 0 or len(xyz) == 0:
            return np.full((len(pos), 3), np.nan)

        pos_clamped = np.clip(pos, dx[0], dx[-1])
        coords_3d = np.zeros((len(pos), 3), dtype=float)
        for axis in range(3):
            coords_3d[:, axis] = np.interp(pos_clamped, dx, xyz[:, axis])
        return coords_3d

    def truncate_by_y(self, y_cut_mm: float) -> "FiberPathData":
        """
        各線維を arc_length 始点(遠位, y小)から辿り、
        y <= y_cut_mm を満たす連続区間だけを残した FiberPathData を返す。

        始点から初めて y > y_cut_mm になった点で打ち切る。
        行を間引くだけなので point_indices が短くなり、FreqPotentials 側の行参照も自動的に整合する。
        """
        keep_row_mask = np.zeros(len(self.unit_ids), dtype=bool)

        for uid in self.get_unit_ids():
            idx = self.get_point_indices(uid)   # arc_length 昇順(始点=遠位)
            y = self.xyz[idx, 1]

            # 始点から連続して y <= y_cut を満たす点数
            n_keep = int(np.argmax(y > y_cut_mm))       # 最初に条件を破る位置
            if not np.any(y > y_cut_mm):
                n_keep = len(y)                          # 全点が条件を満たす

            if n_keep < 2:
                continue                                 # 補間に2点必要

            keep_row_mask[idx[:n_keep]] = True

        if not keep_row_mask.any():
            raise ValueError(f"No fiber survived truncation at y={{y_cut_mm}} mm")

        return FiberPathData(
            unit_ids=self.unit_ids[keep_row_mask],
            arc_length_mm=self.arc_length_mm[keep_row_mask],
            xyz=self.xyz[keep_row_mask],
        )

if __name__ == "__main__":
    PROJECT_DIR = Path(__file__).resolve().parent.parent
    CONFIG_DIR = PROJECT_DIR / "data" / "config"

    path = FiberPathData.from_csv(
        CONFIG_DIR / "fiber_points_csape_RA1-RA2-SA1_toTip-toDIP_palmar_seed12.csv"
    )
    uids = path.get_unit_ids()
    print(f"n_units={len(uids)}, unit_ids(first10)={uids[:10]}")
    uid = uids[0]
    print(f"unit {uid}: len={path.get_fiber_length_um(uid):.1f} um, "
          f"n_points={len(path.get_point_indices(uid))}")
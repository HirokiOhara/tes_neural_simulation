from neuron import h
from typing import List, Tuple
import numpy as np

# コンパートメントタイプ定数
TYPE_NODE = 0

TYPE_NAMES = {
    TYPE_NODE: "node",
}


class ThioAxon:
    """Thio unmyelinated C-fiber model wrapper."""

    TYPE_NODE = TYPE_NODE

    def __init__(
        self,
        fiber_diameter: float = 1.0,
        length_um: float = 5000.0,
        temperature: float = 37.0,
        segment_length_um: float = 50.0 / 6.0,
        particle_index: int = 1,
    ):
        # cFiberBuilderのtypeは現状使用されないが、従来どおり1を渡す。
        fiber_type = 1

        self._fiber = h.cFiberBuilder(
            fiber_diameter,
            length_um,
            fiber_type,
            temperature,
            segment_length_um,
            particle_index,
        )

        self._all_sections = [sec for sec in self._fiber.sl]
        self._compartment_positions_um = None

    # ---- geometry info ----
    @property
    def fiber_diameter(self) -> float:
        return float(self._fiber.fiberD)

    @property
    def total_length_um(self) -> float:
        """
        hoc内で生成された実際の線維長 [um]。

        要求長はセグメント長の整数倍へ切り下げられる。
        """
        return float(self._fiber.Length)

    @property
    def dx(self) -> float:
        """セグメント長 [um]。"""
        return float(self._fiber.dx)

    @property
    def n_segments(self) -> int:
        return int(self._fiber.nsegments)

    @property
    def nodes(self) -> List:
        """Thioモデルでは全セクションがnode。"""
        return self._all_sections

    @property
    def n_compartments(self) -> int:
        return int(self._fiber.nsegments)

    @property
    def section_list_all(self):
        return self._fiber.sl

    def get_compartment(self, k: int):
        k = max(0, min(k, self.n_compartments - 1))
        return self._all_sections[k]

    def get_compartment_info(self, k: int) -> Tuple[int, int]:
        k = max(0, min(k, self.n_compartments - 1))
        return self.TYPE_NODE, k

    def get_compartment_positions_um(self) -> np.ndarray:
        """
        全コンパートメント中心の軸索起点からの距離 [um]。

        cFiberBuilderのsection_coordは線維中心を原点とした[m]表現
        なので、左端を0とする[um]表現へ変換する。
        """
        if self._compartment_positions_um is None:
            length_um = self.total_length_um
            self._compartment_positions_um = np.array(
                [
                    float(self._fiber.section_coord.x[i]) * 1e6
                    + length_um / 2.0
                    for i in range(self.n_compartments)
                ],
                dtype=np.float64,
            )
        return self._compartment_positions_um.copy()

    def get_node_compartment_indices(self) -> np.ndarray:
        """Thioモデルでは全コンパートメントがnode。"""
        return np.arange(self.n_compartments, dtype=int)

    def __repr__(self):
        return (
            f"ThioAxon(D={self.fiber_diameter}um, "
            f"L={self.total_length_um}um, "
            f"dx={self.dx}um, "
            f"n_compartments={self.n_compartments})"
        )

    def __len__(self):
        return self.n_compartments
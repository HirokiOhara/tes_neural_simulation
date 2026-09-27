from neuron import h
from typing import List, Tuple
import numpy as np

# コンパートメントタイプ定数（唯一の定義元）
TYPE_NODE = 0
TYPE_MYSA = 1
TYPE_FLUT = 2
TYPE_STIN = 3

TYPE_NAMES = {
    TYPE_NODE: 'node',
    TYPE_MYSA: 'mysa',
    TYPE_FLUT: 'flut',
    TYPE_STIN: 'stin',
}


class MRGaxon:
    """MRG 2002 (McIntyre et al.) myelinated axon model wrapper."""

    TYPE_NODE = TYPE_NODE
    TYPE_MYSA = TYPE_MYSA
    TYPE_FLUT = TYPE_FLUT
    TYPE_STIN = TYPE_STIN

    def __init__(self, fiber_diameter: float = 8.7, length_um: float = None):
        if length_um is None:
            self._fiber = h.MRGaxonBuilder(fiber_diameter)
        else:
            self._fiber = h.MRGaxonBuilder(fiber_diameter, length_um)

        self._all_sections = [sec for sec in self._fiber.sl_all]
        self._compartment_positions_um = None

    # ---- geometry info ----
    @property
    def fiber_diameter(self) -> float:
        return float(self._fiber.fiberD)

    @property
    def total_length_um(self) -> float:
        return float(self._fiber.total_length_um)

    @property
    def deltax(self) -> float:
        return float(self._fiber.deltax)

    @property
    def n_internodes(self) -> int:
        return int(self._fiber.axonnodes) - 1

    @property
    def nodes(self) -> List:
        return [self._fiber.node[i] for i in range(int(self._fiber.axonnodes))]

    @property
    def n_compartments(self) -> int:
        return int(self._fiber.axontotal)

    @property
    def section_list_all(self):
        return self._fiber.sl_all

    def get_compartment(self, k: int):
        k = max(0, min(k, self.n_compartments - 1))
        return self._all_sections[k]

    def get_compartment_info(self, k: int) -> Tuple[int, int]:
        typ = int(self._fiber.get_compartment_type(k))
        li = int(self._fiber.get_compartment_local_index(k))
        return typ, li

    def get_compartment_positions_um(self) -> np.ndarray:
        """全コンパートメント中心の軸索起点からの距離 [um]"""
        if self._compartment_positions_um is None:
            self._compartment_positions_um = np.array([
                float(self._fiber.coord_all_x_m.x[i]) * 1e6
                for i in range(self.n_compartments)
            ])
        return self._compartment_positions_um.copy()

    def get_node_compartment_indices(self) -> np.ndarray:
        """nodeコンパートメントのインデックス配列を返す。"""
        return np.array(
            [
                k for k in range(self.n_compartments)
                if self.get_compartment_info(k)[0] == self.TYPE_NODE
            ],
            dtype=int,
        )

    def __repr__(self):
        return (
            f"MRGaxon(D={self.fiber_diameter}um, "
            f"L={self.total_length_um}um, "
            f"n_internodes={self.n_internodes}, "
            f"n_compartments={self.n_compartments})"
        )

    def __len__(self):
        return self.n_compartments
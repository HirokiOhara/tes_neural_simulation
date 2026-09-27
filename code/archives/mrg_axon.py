from neuron import h
from typing import List, Sequence, Tuple
import numpy as np

class MRGaxon:
    """
    MRG 2002 (McIntyre et al.) myelinated axon model wrapper.
    
    Parameters
    ----------
    fiber_diameter : float
        Fiber diameter in um. Valid values: 5.7, 7.3, 8.7, 10.0, 11.5, 12.8, 14.0, 15.0, 16.0
    length_um : float, optional
        Desired axon length in um. Actual length will be rounded up to complete internodes.
        If not specified, defaults to 20 internodes.
    
    Examples
    --------
    >>> fiber = MRGaxon(8.7)                    # 8.7um diameter, default length
    >>> fiber = MRGaxon(8.7, length_um=20000)   # 8.7um diameter, ~20mm length
    """

    TYPE_NODE = 0
    TYPE_MYSA = 1
    TYPE_FLUT = 2
    TYPE_STIN = 3

    def __init__(self, fiber_diameter: float = 8.7, length_um: float = None):
        if length_um is None:
            self._fiber = h.MRGaxonBuilder(fiber_diameter)
        else:
            self._fiber = h.MRGaxonBuilder(fiber_diameter, length_um)
        
        self._all_sections = self._build_all_sections_list()
        # キャッシュ：座標計算は一度だけ
        self._node_positions_um: np.ndarray = None
        self._node_positions_m: np.ndarray = None

    def _build_all_sections_list(self) -> List:
        sections = []
        for sec in self._fiber.sl_all:
            sections.append(sec)
        return sections

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

    # ---- group arrays ----
    @property
    def nodes(self) -> List:
        return [self._fiber.node[i] for i in range(int(self._fiber.axonnodes))]

    @property
    def mysas(self) -> List:
        return [self._fiber.MYSA[i] for i in range(int(self._fiber.paranodes1))]

    @property
    def fluts(self) -> List:
        return [self._fiber.FLUT[i] for i in range(int(self._fiber.paranodes2))]

    @property
    def stins(self) -> List:
        return [self._fiber.STIN[i] for i in range(int(self._fiber.axoninter))]

    # ---- all-compartments unified indexing ----
    @property
    def n_compartments(self) -> int:
        return int(self._fiber.axontotal)

    @property
    def section_list_all(self):
        return self._fiber.sl_all

    @property
    def section_list_nodes(self):
        return self._fiber.sl_nodes

    @property
    def coord_all_x_m(self):
        return self._fiber.coord_all_x_m

    def get_compartment(self, k: int):
        if k < 0:
            k = 0
        if k >= self.n_compartments:
            k = self.n_compartments - 1
        return self._all_sections[k]

    def get_compartment_info(self, k: int) -> Tuple[int, int]:
        typ = int(self._fiber.get_compartment_type(k))
        li = int(self._fiber.get_compartment_local_index(k))
        return typ, li
    
    def get_node_positions_um(self) -> np.ndarray:
        """
        Get all compartment center positions in [um].
        
        Returns
        -------
        positions : (n_compartments,) array
            Distance from axon start to compartment center [um]
        
        Note
        ----
        coord_all_x_m in hoc is stored in [m], converted here to [um].
        """
        if self._node_positions_um is None:
            # hoc stores in meters, convert to um
            self._node_positions_um = np.array([
                float(self._fiber.coord_all_x_m.x[i]) * 1e6 
                for i in range(self.n_compartments)
            ])
        return self._node_positions_um.copy()
    
    def get_node_positions_m(self) -> np.ndarray:
        """
        Get all compartment center positions in [m].
        
        Returns
        -------
        positions : (n_compartments,) array
            Distance from axon start to compartment center [m]
        """
        if self._node_positions_m is None:
            self._node_positions_m = np.array([
                float(self._fiber.coord_all_x_m.x[i])
                for i in range(self.n_compartments)
            ])
        return self._node_positions_m.copy()

    def __repr__(self):
        return (
            f"MRGaxon(D={self.fiber_diameter}um, "
            f"L={self.total_length_um}um, "
            f"n_internodes={self.n_internodes}, "
            f"n_compartments={self.n_compartments})"
        )

    def __len__(self):
        return self.n_compartments


if __name__ == '__main__':
    import os
    from pathlib import Path

    PROJECT_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = PROJECT_DIR / 'data'
    MODEL_DIR = DATA_DIR / 'mrg-model'

    os.chdir(MODEL_DIR)
    h.nrn_load_dll(str(MODEL_DIR / "nrnmech.dll"))
    h.load_file("nrngui.hoc")
    h.xopen("MRGaxonBuilder.hoc")

    # Test 1: default length
    print("=== Test 1: Default length ===")
    fiber1 = MRGaxon(8.7)
    print(fiber1)
    print(f"  deltax = {fiber1.deltax} um")
    
    # Test 2: specified length
    print("\n=== Test 2: length_um=20000 ===")
    fiber2 = MRGaxon(8.7, length_um=20000)
    print(fiber2)
    print(f"  requested: 20000 um")
    print(f"  actual:    {fiber2.total_length_um} um")
    
    # Test 3: coordinate positions
    print("\n=== Test 3: Coordinate positions ===")
    fiber = MRGaxon(8.7, length_um=5000)
    print(fiber)
    positions_um = fiber.get_node_positions_um()
    positions_m = fiber.get_node_positions_m()
    print(f"  First 5 positions [um]: {positions_um[:5]}")
    print(f"  First 5 positions [m]:  {positions_m[:5]}")
    print(f"  Last position [um]: {positions_um[-1]}")
    
    # Test 4: compartment info
    print("\n=== Test 4: Compartment info ===")
    type_names = ['node', 'MYSA', 'FLUT', 'STIN']
    for k in [0, 1, 2, 5, 10, fiber.n_compartments-1]:
        sec = fiber.get_compartment(k)
        typ, idx = fiber.get_compartment_info(k)
        pos = positions_um[k]
        print(f"  k={k:3d}: {sec.name():20s} type={type_names[typ]:4s} local_idx={idx} pos={pos:.2f}um")

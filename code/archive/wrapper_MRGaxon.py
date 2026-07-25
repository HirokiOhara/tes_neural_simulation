from neuron import h
from typing import List, Sequence, Tuple

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
        
        # self._veplays: List[Tuple[h.Vector, h.Vector]] = []
        self._all_sections = self._build_all_sections_list()

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

    def distance_to_node_center_from_end(self, index: int) -> float:
        """
        指定ノード中心までの端からの距離[um]を返す。
        """
        x_center_m = float(self.coord_all_x_m.x[index])
        return x_center_m



    # ---- extracellular injection ----
    # def set_extracellular_trace(
    #     self,
    #     compartment_index: int,
    #     t_ms: Sequence[float],
    #     vext_mV: Sequence[float],
    #     loc: float = 0.5,
    # ):
    #     sec = self.get_compartment(compartment_index)
    #     tvec = h.Vector(t_ms)
    #     vvec = h.Vector(vext_mV)

    #     sec.push()
    #     try:
    #         vvec.play(h._ref_e_extracellular, tvec, 1)
    #     finally:
    #         h.pop_section()

    #     self._veplays.append((tvec, vvec))

    # def clear_extracellular_plays(self):
    #     self._veplays.clear()

    # def __repr__(self):
    #     return (f"MRGaxon(D={self.fiber_diameter}um, "
    #             f"L={self.total_length_um}um, "
    #             f"n_internodes={self.n_internodes}, "
    #             f"n_compartments={self.n_compartments})")


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
    print(repr(fiber1))
    print(f"  deltax = {fiber1.deltax} um")
    
    # Test 2: specified length
    print("\n=== Test 2: length_um=20000 ===")
    fiber2 = MRGaxon(8.7, length_um=20000)
    print(repr(fiber2))
    print(f"  requested: 20000 um")
    print(f"  actual:    {fiber2.total_length_um} um")
    
    # Test 3: specified length (non-exact)
    print("\n=== Test 3: length_um=15500 (should round up) ===")
    fiber3 = MRGaxon(8.7, length_um=15500)
    print(repr(fiber3))
    print(f"  requested: 15500 um")
    print(f"  actual:    {fiber3.total_length_um} um")
    
    # Test 4: different diameter
    print("\n=== Test 4: fiberD=5.7, length_um=10000 ===")
    fiber4 = MRGaxon(5.7, length_um=10000)
    print(repr(fiber4))
    print(f"  deltax = {fiber4.deltax} um")
    
    # Test 5: compartment info
    print("\n=== Test 5: Compartment info ===")
    fiber = MRGaxon(8.7, length_um=5000)
    print(repr(fiber))
    type_names = ['node', 'MYSA', 'FLUT', 'STIN']
    for k in [0, 1, 5, 10, fiber.n_compartments-1]:
        sec = fiber.get_compartment(k)
        typ, idx = fiber.get_compartment_info(k)
        print(f"  k={k:3d}: {sec.name():20s} type={type_names[typ]:4s} local_idx={idx}")
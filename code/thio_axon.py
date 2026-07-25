"""
thio_axon.py

Thio C-fiber (unmyelinated axon) model wrapper.
Based on Tigerholm et al. model for unmyelinated sensory neurons.

This wrapper provides an interface consistent with MRGaxon for unified simulation.
"""

from neuron import h
from typing import List, Tuple
import numpy as np


class ThioAxon:
    """
    Thio unmyelinated C-fiber model wrapper.
    
    Parameters
    ----------
    fiber_diameter : float
        Fiber diameter in um. Typical range: 0.2 - 1.5 um for C-fibers.
    length_um : float
        Desired axon length in um.
    temperature : float
        Temperature in Celsius. Default: 37.0
    seg_density : float
        Segment density (segments per um). Default: 50/6 ≈ 8.33
    particle_index : int
        Index for conductance parameter set. Default: 1
    
    Examples
    --------
    >>> fiber = ThioAxon(0.8, length_um=20000)  # 0.8um diameter, 20mm length
    >>> fiber = ThioAxon(1.0, length_um=50000)  # 1.0um diameter, 50mm length
    """

    # コンパートメントタイプ（MRGaxonとの互換性のため）
    # Thioモデルは無髄神経なので全てnodeタイプ
    TYPE_NODE = 0

    def __init__(
        self,
        fiber_diameter: float = 1.0,
        length_um: float = 20000.0,
        temperature: float = 37.0,
        seg_density: float = 50/6,
        particle_index: int = 1,
    ):
        # cFiberBuilderのfiber_typeは常に1（node only）
        fiber_type = 1
        
        self._fiber = h.cFiberBuilder(
            fiber_diameter,
            length_um,
            fiber_type,
            temperature,
            seg_density,
            particle_index
        )
        
        # セクションリストをキャッシュ
        self._all_sections = self._build_all_sections_list()
        
        # 座標キャッシュ（遅延計算）
        self._node_positions_um: np.ndarray = None
        self._node_positions_m: np.ndarray = None

    def _build_all_sections_list(self) -> List:
        """全セクションをリストとして取得"""
        sections = []
        for sec in self._fiber.sl:
            sections.append(sec)
        return sections

    # =========================================================================
    # Geometry Properties
    # =========================================================================
    
    @property
    def fiber_diameter(self) -> float:
        """Fiber diameter [um]"""
        return float(self._fiber.fiberD)
    
    @property
    def total_length_um(self) -> float:
        """Total axon length [um]"""
        return float(self._fiber.Length)
    
    @property
    def dx(self) -> float:
        """Segment length [um]"""
        return float(self._fiber.dx)
    
    @property
    def n_segments(self) -> int:
        """Number of segments"""
        return int(self._fiber.nsegments)

    # =========================================================================
    # Compartment Access (MRGaxon compatible interface)
    # =========================================================================
    
    @property
    def n_compartments(self) -> int:
        """
        Total number of compartments.
        For Thio model: n_compartments = n_segments = n_nodes
        """
        return int(self._fiber.nsegments)
    
    @property
    def n_nodes(self) -> int:
        """
        Number of nodes.
        For Thio model (unmyelinated): all compartments are nodes.
        """
        return int(self._fiber.nsegments)
    
    @property
    def nodes(self) -> List:
        """List of all node sections"""
        return self._all_sections
    
    @property
    def section_list_all(self):
        """NEURON SectionList containing all sections"""
        return self._fiber.sl
    
    @property
    def section_list_nodes(self):
        """
        NEURON SectionList containing node sections.
        For Thio model: same as section_list_all
        """
        return self._fiber.sl

    def get_compartment(self, k: int):
        """
        Get compartment (section) by global index.
        
        Parameters
        ----------
        k : int
            Compartment index (0 to n_compartments-1)
        
        Returns
        -------
        section : NEURON section
        """
        k = max(0, min(k, self.n_compartments - 1))
        return self._all_sections[k]

    def get_compartment_info(self, k: int) -> Tuple[int, int]:
        """
        Get compartment type and local index.
        
        Parameters
        ----------
        k : int
            Compartment index
        
        Returns
        -------
        (type, local_index) : tuple
            type: always TYPE_NODE (0) for Thio model
            local_index: same as k for Thio model
        
        Note
        ----
        This method exists for compatibility with MRGaxon.
        For Thio model, all compartments are nodes.
        """
        k = max(0, min(k, self.n_compartments - 1))
        return (self.TYPE_NODE, k)

    # =========================================================================
    # Coordinate Methods
    # =========================================================================
    
    def get_node_positions_um(self) -> np.ndarray:
        """
        Get all compartment center positions in [um].
        Positions are relative to axon start (left end = 0).
        
        Returns
        -------
        positions : (n_compartments,) array
            Distance from axon start to compartment center [um]
        
        Note
        ----
        cFiberBuilder stores coordinates relative to center.
        This method converts to left-end reference (same as MRGaxon).
        """
        if self._node_positions_um is None:
            # hoc stores center-referenced coordinates in [m]
            # Convert to left-end reference in [um]
            L_um = self.total_length_um
            self._node_positions_um = np.array([
                float(self._fiber.section_coord.x[i]) * 1e6 + L_um / 2
                for i in range(self.n_compartments)
            ])
        return self._node_positions_um.copy()
    
    def get_node_positions_m(self) -> np.ndarray:
        """
        Get all compartment center positions in [m].
        Positions are relative to axon start (left end = 0).
        
        Returns
        -------
        positions : (n_compartments,) array
            Distance from axon start to compartment center [m]
        """
        if self._node_positions_m is None:
            self._node_positions_m = self.get_node_positions_um() * 1e-6
        return self._node_positions_m.copy()

    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def __repr__(self):
        return (
            f"ThioAxon(D={self.fiber_diameter}um, "
            f"L={self.total_length_um}um, "
            f"n_compartments={self.n_compartments})"
        )

    def __len__(self):
        return self.n_compartments
    
    def __iter__(self):
        """Iterate over all sections"""
        return iter(self._all_sections)


# =============================================================================
# Test
# =============================================================================

if __name__ == '__main__':
    import os
    from pathlib import Path

    PROJECT_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = PROJECT_DIR / 'data'
    MODEL_DIR = DATA_DIR / 'thio-model'

    # NEURON setup
    os.chdir(MODEL_DIR)
    h.nrn_load_dll(str(MODEL_DIR / 'nrnmech.dll'))
    h.load_file('nrngui.hoc')
    h.xopen('cFiberBuilder.hoc')
    h.load_file('balance.hoc')

    print("=" * 60)
    print("Test 1: Basic creation")
    print("=" * 60)
    fiber1 = ThioAxon(fiber_diameter=0.8, length_um=1000)
    print(fiber1)
    print(f"  dx = {fiber1.dx} um")
    print(f"  n_segments = {fiber1.n_segments}")
    print(f"  n_compartments = {fiber1.n_compartments}")
    print(f"  n_nodes = {fiber1.n_nodes}")

    print("\n" + "=" * 60)
    print("Test 2: Longer fiber")
    print("=" * 60)
    fiber2 = ThioAxon(fiber_diameter=0.8, length_um=20000)
    print(fiber2)
    print(f"  requested: 20000 um")
    print(f"  actual:    {fiber2.total_length_um} um")

    print("\n" + "=" * 60)
    print("Test 3: Coordinate positions (left-end reference)")
    print("=" * 60)
    fiber3 = ThioAxon(fiber_diameter=0.8, length_um=100)
    print(fiber3)
    positions_um = fiber3.get_node_positions_um()
    positions_m = fiber3.get_node_positions_m()
    print(f"  Total length: {fiber3.total_length_um} um")
    print(f"  dx: {fiber3.dx} um")
    print(f"  n_compartments: {fiber3.n_compartments}")
    print(f"  First 5 positions [um]: {positions_um[:5]}")
    print(f"  Last 5 positions [um]:  {positions_um[-5:]}")
    print(f"  Position range: [{positions_um.min():.2f}, {positions_um.max():.2f}] um")
    
    # 座標の検証
    expected_first = fiber3.dx / 2  # 最初のセグメント中心
    expected_last = fiber3.total_length_um - fiber3.dx / 2  # 最後のセグメント中心
    print(f"  Expected first: {expected_first:.2f} um, actual: {positions_um[0]:.2f} um")
    print(f"  Expected last:  {expected_last:.2f} um, actual: {positions_um[-1]:.2f} um")

    print("\n" + "=" * 60)
    print("Test 4: Compartment info (MRGaxon compatibility)")
    print("=" * 60)
    fiber4 = ThioAxon(fiber_diameter=0.8, length_um=100)
    type_names = {0: 'node'}
    
    for k in [0, 1, 5, fiber4.n_compartments - 1]:
        sec = fiber4.get_compartment(k)
        typ, local_idx = fiber4.get_compartment_info(k)
        pos = fiber4.get_node_positions_um()[k]
        print(f"  k={k:3d}: {sec.name():20s} type={type_names[typ]:4s} local_idx={local_idx} pos={pos:.2f}um")

    print("\n" + "=" * 60)
    print("Test 5: Balance function")
    print("=" * 60)
    fiber5 = ThioAxon(fiber_diameter=0.8, length_um=1000)
    
    # balance() 実行前の状態
    print("Before balance():")
    first_node = fiber5.get_compartment(0)
    print(f"  v = {first_node.v} mV")
    
    # balance() を実行
    h.finitialize(-55)  # 初期化（Thioモデルの静止電位は約-55mV）
    h.balance()
    print("After balance():")
    print(f"  v = {first_node.v} mV")

    print("\n" + "=" * 60)
    print("Test 6: Iteration")
    print("=" * 60)
    fiber6 = ThioAxon(fiber_diameter=0.8, length_um=50)
    print(f"Iterating over {len(fiber6)} sections:")
    for i, sec in enumerate(fiber6):
        if i < 3 or i >= len(fiber6) - 2:
            print(f"  [{i}] {sec.name()}")
        elif i == 3:
            print("  ...")

    print("\n=== All tests completed ===")
from dataclasses import dataclass
from typing import Any, Dict

import numpy as np
from neuron import h

from model_mrg import MRGaxon


@dataclass
class SimulationConfigMRG:
    """MRGシミュレーション設定"""
    dt_ms: float = 0.01
    tstop_ms: float = 100.0
    v_init_mV: float = -80.0
    ap_threshold_mV: float = 0.0
    fiber_diameter_um: float = 8.7


def simulate_single_mrg_fiber(
    fiber: MRGaxon,
    V_extracellular: np.ndarray,
    config: SimulationConfigMRG,
    t_ms: np.ndarray
) -> Dict[str, Any]:
    """
    MRG線維1本のNEURONシミュレーション。

    V_extracellular : (n_compartments, n_steps) 膜外電位 [mV]
    Returns: v_membrane (n_comp, n_steps), ap_count, spike_times_ms
    """
    V_extracellular = np.asarray(V_extracellular, dtype=np.float64)
    n_comp = fiber.n_compartments
    n_steps = V_extracellular.shape[1]

    if V_extracellular.shape[0] != n_comp:
        raise ValueError(
            f"V_extracellular shape[0]={V_extracellular.shape[0]} "
            f"!= n_comp={n_comp}"
        )

    h.v_init = config.v_init_mV
    h.dt = config.dt_ms
    h.tstop = config.tstop_ms

    t_vec = h.Vector(t_ms.tolist())

    stim_vectors = []
    rec_vectors = []
    for i, sec in enumerate(fiber.section_list_all):
        v_stim = h.Vector(V_extracellular[i].tolist())
        v_stim.play(sec(0.5)._ref_e_extracellular, t_vec, False)
        stim_vectors.append(v_stim)

        v_rec = h.Vector()
        v_rec.record(sec(0.5)._ref_v)
        rec_vectors.append(v_rec)

    apc = h.APCount(fiber.nodes[-1](0.5))
    apc.thresh = config.ap_threshold_mV

    spike_times_vec = h.Vector()
    apc.record(spike_times_vec)

    h.finitialize(h.v_init)
    h.continuerun(h.tstop)

    v_membrane = np.zeros((n_comp, n_steps), dtype=np.float64)
    for i, vec in enumerate(rec_vectors):
        arr = np.asarray(vec.as_numpy(), dtype=np.float64)
        v_membrane[i, :len(arr)] = arr[:n_steps]

    return {
        'v_membrane': v_membrane,
        'ap_count': int(apc.n),
        'spike_times_ms': np.asarray(spike_times_vec.as_numpy(), dtype=np.float64).copy(),
    }


def make_mrg_result_record(
    unit_id: int,
    fiber: MRGaxon,
    fiber_length_um: float,
    fiber_path,
    simulation_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    MRG結果を共通形式へ変換する。

    node コンパートメントのみを抽出し、
    その1D位置に対応する3D座標も付与する。
    可視化MATLABは膜電位CSVと座標CSVの2つを読むだけでよい。
    """
    node_idx = fiber.get_node_compartment_indices()
    comp_positions = fiber.get_compartment_positions_um()

    node_positions_um = comp_positions[node_idx]
    v_nodes = np.asarray(
        simulation_result["v_membrane"], dtype=np.float64
    )[node_idx, :]

    node_coords_mm = fiber_path.interpolate_1d_to_3d(unit_id, node_positions_um)

    return {
        "unit_id": int(unit_id),
        "fiber_length_um": float(fiber_length_um),
        "point_positions_um": node_positions_um,       # (n_node,)
        "point_coords_mm": node_coords_mm,             # (n_node, 3)
        "v_membrane": v_nodes,                         # (n_node, T)
        "ap_count": int(simulation_result["ap_count"]),
        "spike_times_ms": np.asarray(
            simulation_result["spike_times_ms"], dtype=np.float64
        ),
    }


def simulate_one_mrg_fiber(fiber_path, unit_id, stim_configs, sim_config, t_ms):
    """run_common の実行フレーム用「MRG線維1本計算関数」。"""
    from run_common import prepare_potential

    fiber_length_um = float(fiber_path.get_fiber_length_um(unit_id))
    fiber = MRGaxon(
        fiber_diameter=sim_config.fiber_diameter_um,
        length_um=fiber_length_um,
    )

    positions_um = fiber.get_compartment_positions_um()

    V_ext = prepare_potential(
        fiber_path=fiber_path,
        unit_id=unit_id,
        stim_configs=stim_configs,
        t_ms=t_ms,
        compartment_positions_um=positions_um,
    )

    sim_result = simulate_single_mrg_fiber(fiber, V_ext, sim_config, t_ms)

    return make_mrg_result_record(
        unit_id, fiber, fiber_length_um, fiber_path, sim_result
    )
from dataclasses import dataclass
from typing import Any, Dict

import numpy as np
from neuron import h

from model_thio import ThioAxon


@dataclass
class SimulationConfigThio:
    """Thioシミュレーション設定。"""
    dt_ms: float = 0.01
    tstop_ms: float = 100.0
    v_init_mV: float = -55.0
    ap_threshold_mV: float = 0.0

    fiber_diameter_um: float = 1.0
    temperature_c: float = 37.0

    # cFiberBuilder.hocでは変数名がsegdensityだが、実際には
    # dx=segdensityとしてセグメント長[um]に使用される。
    segment_length_um: float = 50.0 / 6.0

    particle_index: int = 1


def simulate_single_thio_fiber(
    fiber: ThioAxon,
    V_extracellular: np.ndarray,
    config: SimulationConfigThio,
    t_ms: np.ndarray,
) -> Dict[str, Any]:
    """
    Thio線維1本のNEURONシミュレーション。

    Parameters
    ----------
    V_extracellular:
        (n_compartments, n_steps) 膜外電位 [mV]

    Returns
    -------
    dict
        v_membrane, ap_count, spike_times_ms
    """
    V_extracellular = np.asarray(V_extracellular, dtype=np.float64)
    t_ms = np.asarray(t_ms, dtype=np.float64)

    n_comp = fiber.n_compartments
    n_steps = V_extracellular.shape[1]

    if V_extracellular.shape[0] != n_comp:
        raise ValueError(
            f"V_extracellular shape[0]={V_extracellular.shape[0]} "
            f"!= n_comp={n_comp}"
        )

    if len(t_ms) != n_steps:
        raise ValueError(
            f"len(t_ms)={len(t_ms)} != "
            f"V_extracellular shape[1]={n_steps}"
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

    # APは線維末端で検出する。
    apc = h.APCount(fiber.nodes[-1](0.5))
    apc.thresh = config.ap_threshold_mV

    spike_times_vec = h.Vector()
    apc.record(spike_times_vec)

    # Thioモデル固有の定常状態調整
    h.finitialize(h.v_init)
    h.balance()

    h.continuerun(h.tstop)

    v_membrane = np.zeros((n_comp, n_steps), dtype=np.float64)
    for i, vec in enumerate(rec_vectors):
        arr = np.asarray(vec.as_numpy(), dtype=np.float64)
        copy_length = min(len(arr), n_steps)
        v_membrane[i, :copy_length] = arr[:copy_length]

    return {
        "v_membrane": v_membrane,
        "ap_count": int(apc.n),
        "spike_times_ms": np.asarray(
            spike_times_vec.as_numpy(),
            dtype=np.float64,
        ).copy(),
    }


def make_thio_result_record(
    unit_id: int,
    fiber: ThioAxon,
    fiber_length_um: float,
    fiber_path,
    simulation_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Thio結果を共通形式へ変換する。

    Thioモデルでは全コンパートメントを結果点として扱う。
    MPIスクリプトではsummaryのみ保存するが、将来の逐次版でも
    共通result_ioを利用できる形式にしている。
    """
    positions_um = fiber.get_compartment_positions_um()
    coords_mm = fiber_path.interpolate_1d_to_3d(
        unit_id,
        positions_um,
    )

    return {
        "unit_id": int(unit_id),
        "fiber_length_um": float(fiber_length_um),
        "point_positions_um": positions_um,
        "point_coords_mm": coords_mm,
        "v_membrane": np.asarray(
            simulation_result["v_membrane"],
            dtype=np.float64,
        ),
        "ap_count": int(simulation_result["ap_count"]),
        "spike_times_ms": np.asarray(
            simulation_result["spike_times_ms"],
            dtype=np.float64,
        ),
    }


def simulate_one_thio_fiber(
    fiber_path,
    unit_id,
    stim_configs,
    sim_config,
    t_ms,
):
    """run_commonの実行フレーム用「Thio線維1本計算関数」。"""
    from run_common import prepare_potential

    fiber_length_um = float(
        fiber_path.get_fiber_length_um(unit_id)
    )

    fiber = ThioAxon(
        fiber_diameter=sim_config.fiber_diameter_um,
        length_um=fiber_length_um,
        temperature=sim_config.temperature_c,
        segment_length_um=sim_config.segment_length_um,
        particle_index=sim_config.particle_index,
    )

    positions_um = fiber.get_compartment_positions_um()

    V_ext = prepare_potential(
        fiber_path=fiber_path,
        unit_id=unit_id,
        stim_configs=stim_configs,
        t_ms=t_ms,
        compartment_positions_um=positions_um,
    )

    sim_result = simulate_single_thio_fiber(
        fiber=fiber,
        V_extracellular=V_ext,
        config=sim_config,
        t_ms=t_ms,
    )

    return make_thio_result_record(
        unit_id=unit_id,
        fiber=fiber,
        fiber_length_um=fiber_length_um,
        fiber_path=fiber_path,
        simulation_result=sim_result,
    )
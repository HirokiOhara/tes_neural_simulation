from pathlib import Path
import numpy as np
import pandas as pd
from neuron import h
from dataclasses import dataclass, field


def setup_apcount(section, x=0.5, threshold=-20.0):
    '''指定セクションにAPCounterを設置'''
    apc = h.APCount(section(x))
    apc.thresh = threshold
    spk_times = h.Vector()
    apc.record(spk_times)
    return apc, spk_times


def simulate_mrg_fiber(fiber_model, potentials_timeseries_along_fiber, dt_ms, tstop, lst_cumulative_dx):
    '''単一fiberのシミュレーション'''
    n_compartments = fiber_model.n_compartments
    n_steps = int(round(tstop / dt_ms)) + 1
    
    # 入力検証
    if potentials_timeseries_along_fiber.shape[0] != n_compartments:
        raise ValueError(
            f"potentials shape[0]={potentials_timeseries_along_fiber.shape[0]} "
            f"does not match n_compartments={n_compartments}"
        )
    if potentials_timeseries_along_fiber.shape[1] != n_steps:
        raise ValueError(
            f"potentials shape[1]={potentials_timeseries_along_fiber.shape[1]} "
            f"does not match expected n_steps={n_steps}"
        )
    
    # 時間ベクトル
    lst_cumulative_dt = np.linspace(0.0, tstop, n_steps)
    
    h.v_init = -80
    h.dt = dt_ms
    h.tstop = tstop

    t_vec = h.Vector(lst_cumulative_dt.tolist())

    v_stimulation_vectors = []
    v_recorder_vectors = []

    sl = fiber_model.section_list_all

    for i, sec in enumerate(sl):
        # 刺激電位の設定
        v_vec = h.Vector(potentials_timeseries_along_fiber[i].tolist())
        v_vec.play(sec(0.5)._ref_e_extracellular, t_vec, False)
        v_stimulation_vectors.append(v_vec)
        
        # 膜電位の記録
        v_recorder_vec = h.Vector()
        v_recorder_vec.record(sec(0.5)._ref_v)
        v_recorder_vectors.append(v_recorder_vec)

    # 最終ノードでAPをカウント
    apc, spk_times = setup_apcount(fiber_model.nodes[-1], x=0.5, threshold=0.0)

    # シミュレーション実行
    h.finitialize(h.v_init)
    h.continuerun(h.tstop)

    # 結果の取得
    v_matrix = np.zeros((n_compartments, n_steps), dtype=np.float64)
    for i, vec in enumerate(v_recorder_vectors):
        arr = np.array(vec.as_numpy())
        # NEURONの記録点数が若干異なる場合の対処
        v_matrix[i, :len(arr)] = arr[:n_steps]

    spike_times = np.array(spk_times.as_numpy()) if spk_times.size() > 0 else np.array([])
    ap_count = int(apc.n)

    # 毎回インスタンスを作成するので、セクションの削除は不要

    return v_matrix, ap_count, spike_times


if __name__ == "__main__":

    import os
    from pathlib import Path
    import datetime

    import numpy as np
    import pandas as pd
    from neuron import h

    from wrapper_MRGaxon import MRGaxon
    from utility import load_csv_points
    from get_fiber_length import calculate_cumulative_dx_along_fiber, calculate_fiber_lengths
    from get_potential_along_fiber import (
        load_potentials_csv_by_freq,
        list_freqs_in_potentials_csv,
        get_potential_timeseries_along_fiber,
        calculate_potentials_lerp,
        superpose_timeseries,
        load_potentials_csv,
        build_coord_to_index,
    )

    PROJECT_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = PROJECT_DIR / "data"
    MODEL_DIR = DATA_DIR / "mrg-model"
    CONFIG_DIR = DATA_DIR / "config"
    COMSOL_DIR = DATA_DIR / "comsol"

    os.chdir(MODEL_DIR)
    h.nrn_load_dll(str(MODEL_DIR / "nrnmech.dll"))
    h.load_file("nrngui.hoc")
    h.xopen("MRGaxonBuilder.hoc")

    @dataclass
    class PotentialsData:
        csv_path: str = ""
        coords: np.ndarray = field(default_factory=lambda: np.empty((0, 3), dtype=float))
        freqs: np.ndarray = field(default_factory=lambda: np.empty((0,), dtype=float))
        V_all: np.ndarray = field(default_factory=lambda: np.empty((0, 0), dtype=np.complex64))
        coord_to_index: dict = field(default_factory=dict)

    # --- sim settings ---
    dt_ms = 0.01
    tstop_ms = 100.0
    t_ms = np.arange(0.0, tstop_ms + dt_ms, dt_ms)

    # --- unit_id -> fiber type (RA1/RA2/SA1) を決めるために数をカウント ---
    fiber_info = pd.read_csv(CONFIG_DIR / "fiber_info_summary.csv")
    counts = fiber_info["ReceptorType"].value_counts()
    n_ra1 = int(counts.get("RA1", 0))
    n_ra2 = int(counts.get("RA2", 0))
    n_sa1 = int(counts.get("SA1", 0))

    dt_now = datetime.datetime.now()
    print(dt_now)

    ra1_e1 = PotentialsData()
    ra1_e1.csv_path = str(COMSOL_DIR / "electrode_square/potentials_along_ra1_fiber_electrodes_1.csv")
    ra1_e1.coords, ra1_e1.freqs, ra1_e1.V_all = load_potentials_csv(ra1_e1.csv_path)
    ra1_e1.coord_to_index = build_coord_to_index(ra1_e1.coords, decimals=6)
    dt_now = datetime.datetime.now()
    print(dt_now)

    ra1_e2 = PotentialsData()
    ra1_e2.csv_path = str(COMSOL_DIR / "electrode_square/potentials_along_ra1_fiber_electrodes_2.csv")
    ra1_e2.coords, ra1_e2.freqs, ra1_e2.V_all = load_potentials_csv(ra1_e2.csv_path)
    ra1_e2.coord_to_index = build_coord_to_index(ra1_e2.coords, decimals=6)
    dt_now = datetime.datetime.now()
    print(dt_now)

    # ra2_e1 = PotentialsData()
    # ra2_e1.csv_path = str(COMSOL_DIR / "electrode_square/potentials_along_ra1_fiber_electrodes_1.csv")
    # ra2_e1.coords, ra2_e1.freqs, ra2_e1.V_all = load_potentials_csv(ra2_e1.csv_path)
    # ra2_e1.coord_to_index = build_coord_to_index(ra2_e1.coords, decimals=6)

    # ra2_e2 = PotentialsData()
    # ra2_e2.csv_path = str(COMSOL_DIR / "electrode_square/potentials_along_ra1_fiber_electrodes_1.csv")
    # ra2_e2.coords, ra2_e2.freqs, ra2_e2.V_all = load_potentials_csv(ra2_e2.csv_path)
    # ra2_e2.coord_to_index = build_coord_to_index(ra2_e2.coords, decimals=6)

    # sa1_e1 = PotentialsData()
    # sa1_e1.csv_path = str(COMSOL_DIR / "electrode_square/potentials_along_ra1_fiber_electrodes_1.csv")
    # sa1_e1.coords, sa1_e1.freqs, sa1_e1.V_all = load_potentials_csv(sa1_e1.csv_path)
    # sa1_e1.coord_to_index1 = build_coord_to_index(sa1_e1.coords, decimals=6)

    # sa1_e2 = PotentialsData()
    # sa1_e2.csv_path = str(COMSOL_DIR / "electrode_square/potentials_along_ra1_fiber_electrodes_1.csv")
    # sa1_e2.coords, sa1_e2.freqs, sa1_e2.V_all = load_potentials_csv(sa1_e2.csv_path)
    # sa1_e2.coord_to_index = build_coord_to_index(sa1_e2.coords, decimals=6)

    ra1_pairs = [ra1_e1, ra1_e2]
    # ra2_pairs = [ra2_e1, ra2_e2]
    # sa1_pairs = [sa1_e1, sa1_e2]

    lst_amp = [8.0, 8.0]
    lst_theta = [0.0, 0.0]
    lst_freq = [2000.0, 2040.0]


    # for RA1
    points = load_csv_points(CONFIG_DIR / "points_along_ra1_fibers.csv")
    cum_lengths = calculate_cumulative_dx_along_fiber(points)
    fiber_lengths = calculate_fiber_lengths(points)

    for unit_id, length in fiber_lengths.items():
        if unit_id != 23:  ## center of RA1
        # if unit_id != 380:  ## center of SA1 id=380 (371 - 539)
            continue

        fiber = MRGaxon(8.7, length_um=length)

        lst_dx_fiber = [
            fiber.distance_to_node_center_from_end(i) for i in range(fiber.n_compartments)
        ]

        per_component = []
        for i, pair in enumerate(ra1_pairs):
            v = get_potential_timeseries_along_fiber(unit_id, points, pair, lst_freq[i], t_ms, lst_amp[i], lst_theta[i])
            per_component.append(v)
        # 同じfiber type の electrode pair1 + pair2 だけ合成
        v_total = superpose_timeseries(per_component)
        v_interp = calculate_potentials_lerp(lst_dx_fiber, v_total, cum_lengths[unit_id])

        print(np.max(np.abs(v_interp)))

        v_matrix, ap_count, spike_times = simulate_mrg_fiber(
            fiber, v_interp, dt_ms, tstop_ms, lst_dx_fiber
        )

        np.savetxt(DATA_DIR / f"temp/vm_UnitId_{unit_id}.csv", v_matrix, delimiter=",")

        print(unit_id, "ap_count:", ap_count, "spike_times:", spike_times)
        print(f"v_total min: {v_interp.min():.4f} mV, max: {v_interp.max():.4f} mV")


    # # ----- for RA2 -----
    # points = load_csv_points(CONFIG_DIR / "points_along_ra2_fibers.csv")
    # cum_lengths = calculate_cumulative_dx_along_fiber(points)
    # fiber_lengths = calculate_fiber_lengths(points)

    # for unit_id, length in fiber_lengths.items():

    #     fiber = MRGaxon(8.7, length_um=length)

    #     lst_dx_fiber = [
    #         fiber.distance_to_node_center_from_end(i) for i in range(fiber.n_compartments)
    #     ]

    #     per_component = []
    #     for i, pair in enumerate(ra2_pairs):
    #         v = get_potential_timeseries_along_fiber(unit_id, points, pair, lst_freq[i], t_ms, lst_amp[i], lst_theta[i])
    #         per_component.append(v)
    #     # 同じfiber type の electrode pair1 + pair2 だけ合成
    #     v_total = superpose_timeseries(per_component)
    #     v_interp = calculate_potentials_lerp(lst_dx_fiber, v_total, cum_lengths[unit_id])

    #     print(np.max(np.abs(v_interp)))

    #     v_matrix, ap_count, spike_times = simulate_mrg_fiber(
    #         fiber, v_interp, dt_ms, tstop_ms, lst_dx_fiber
    #     )

    #     # np.savetxt(DATA_DIR / f"temp/vm_UnitId_{unit_id}.csv", v_matrix, delimiter=",")

    #     print(unit_id, "ap_count:", ap_count, "spike_times:", spike_times)
    #     print(f"v_total min: {v_total.min():.4f} mV, max: {v_total.max():.4f} mV")


    # # ----- for SA1 -----
    # points = load_csv_points(CONFIG_DIR / "points_along_sa1_fibers.csv")
    # cum_lengths = calculate_cumulative_dx_along_fiber(points)
    # fiber_lengths = calculate_fiber_lengths(points)

    # for unit_id, length in fiber_lengths.items():

    #     fiber = MRGaxon(8.7, length_um=length)

    #     lst_dx_fiber = [
    #         fiber.distance_to_node_center_from_end(i) for i in range(fiber.n_compartments)
    #     ]

    #     per_component = []
    #     for i, pair in enumerate(sa1_pairs):
    #         v = get_potential_timeseries_along_fiber(unit_id, points, pair, lst_freq[i], t_ms, lst_amp[i], lst_theta[i])
    #         per_component.append(v)
    #     # 同じfiber type の electrode pair1 + pair2 だけ合成
    #     v_total = superpose_timeseries(per_component)
    #     v_interp = calculate_potentials_lerp(lst_dx_fiber, v_total, cum_lengths[unit_id])

    #     print(np.max(np.abs(v_interp)))

    #     v_matrix, ap_count, spike_times = simulate_mrg_fiber(
    #         fiber, v_interp, dt_ms, tstop_ms, lst_dx_fiber
    #     )

    #     # np.savetxt(DATA_DIR / f"temp/vm_UnitId_{unit_id}.csv", v_matrix, delimiter=",")

    #     print(unit_id, "ap_count:", ap_count, "spike_times:", spike_times)
    #     print(f"v_total min: {v_total.min():.4f} mV, max: {v_total.max():.4f} mV")

from pathlib import Path

import numpy as np

from fiber_path import FiberPathData
from freq_data import FreqPotentials
from nrn_runner_mrg import SimulationConfigMRG, simulate_one_mrg_fiber
from result_io import (
    append_one_fiber_coords,
    append_one_fiber_membrane,
    open_coords_writer,
    open_membrane_writer,
    save_results_summary,
)
from run_common import (
    StimConfig,
    initialize_neuron,
    make_time_axis_ms,
    print_start_banner,
    run_fibers_serial,
    validate_input_sizes,
)


def main() -> None:
    # ---- パス設定 ----
    project_dir = Path(__file__).resolve().parent.parent
    data_dir = project_dir / "data"
    model_dir = data_dir / "MRG_model"
    config_dir = data_dir / "config"
    comsol_dir = data_dir / "comsol" / "selectivity"
    output_dir = data_dir / "output"

    # ---- NEURON初期化（MRG固有hoc）----
    initialize_neuron(model_dir, hoc_files=["MRGaxonBuilder.hoc"])

    # ---- シミュレーション設定 ----
    sim_config = SimulationConfigMRG(
        dt_ms=0.01,
        tstop_ms=300.0,
        v_init_mV=-80.0,
        ap_threshold_mV=0.0,
        fiber_diameter_um=8.7,
    )
    t_ms = make_time_axis_ms(sim_config.dt_ms, sim_config.tstop_ms)

    # None なら全線維。例: {17, 20, 78}
    target_unit_ids = {17, 18, 20, 21}
    output_prefix = "selectivity_seed12_mrg"

    # ---- 入力データ ----
    # ---- y切断（None なら切断しない）----
    y_cut_mm = 10.0   # この y 断面(遠位側 y<=y_cut)まで計算
    # y_cut_mm = None

    fiber_path = FiberPathData.from_csv(
        config_dir
        / "fiber_points_makima_RA1-RA2-SA1_toTip-toDIP_palmar_seed12.csv"
    )
    stim_configs = [
        StimConfig(
            pot=FreqPotentials.from_csv(
                comsol_dir / "layout2_para_pair1_makima_seed12.csv"
            ),
            freq_hz=2000.0, amp_mA=0.5, phase_rad=0.0,
        ),
        StimConfig(
            pot=FreqPotentials.from_csv(
                comsol_dir / "layout2_para_pair2_makima_seed12.csv"
            ),
            freq_hz=2040.0, amp_mA=0.5, phase_rad=0.0,
        ),
    ]
    validate_input_sizes(fiber_path, stim_configs)
    if y_cut_mm is not None:
        fiber_path = fiber_path.truncate_by_y(y_cut_mm)

    # ---- 実行 & 保存（ストリーミング）----
    print_start_banner("MRG Frequency Domain Simulation (serial)")
    print(f"Number of fibers: {len(fiber_path.get_unit_ids())}")

    mem_path = open_membrane_writer(output_dir, output_prefix, len(t_ms))
    crd_path = open_coords_writer(output_dir, output_prefix)

    def on_result(r):
        append_one_fiber_membrane(mem_path, r)
        append_one_fiber_coords(crd_path, r)

    summaries = run_fibers_serial(
        fiber_path=fiber_path,
        stim_configs=stim_configs,
        sim_config=sim_config,
        t_ms=t_ms,
        simulate_one_fiber_fn=simulate_one_mrg_fiber,
        target_unit_ids=target_unit_ids,
        on_result=on_result,
    )

    save_results_summary(summaries, output_dir, prefix=output_prefix)


if __name__ == "__main__":
    main()
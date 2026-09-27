import datetime
from pathlib import Path

from fiber_path import FiberPathData
from freq_data import FreqPotentials
from nrn_runner_mrg import SimulationConfigMRG, simulate_one_mrg_fiber
from result_io import save_results_summary
from run_common import (
    StimConfig,
    filter_target_unit_ids,
    initialize_neuron,
    make_time_axis_ms,
    merge_summary_dicts,
    print_start_banner,
    run_fibers_for_rank,
    split_unit_ids_round_robin,
    validate_input_sizes,
)

from mpi4py import MPI


def main() -> None:
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    # ---- パス設定 ----
    project_dir = Path(__file__).resolve().parent.parent
    data_dir = project_dir / "data"
    model_dir = data_dir / "MRG_model"
    config_dir = data_dir / "config"
    comsol_dir = data_dir / "comsol" / "selectivity_layout2_04d-04e"
    output_dir = data_dir / "output"

    # ---- NEURON初期化（全rankで実行）----
    initialize_neuron(model_dir, hoc_files=["MRGaxonBuilder.hoc"])

    # ---- シミュレーション設定 ----
    sim_config = SimulationConfigMRG(
        dt_ms=0.01,
        tstop_ms=200.0,
        v_init_mV=-80.0,
        ap_threshold_mV=0.0,
        fiber_diameter_um=8.7,
    )
    t_ms = make_time_axis_ms(sim_config.dt_ms, sim_config.tstop_ms)

    target_unit_ids = None
    # target_unit_ids = {17, 18, 20, 21}
    output_prefix = "selectivity_seed12_mrg_mpi"

    # ---- 入力データ（各rankが独立に読む）----
    # ---- y切断（None なら切断しない）----
    y_cut_mm = 10.0

    fiber_path = FiberPathData.from_csv(
        comsol_dir
        / "fiber_points_makima_RA1-RA2-SA1_toTip-toDIP_palmar_seed12.csv"
    )
    stim_configs = [
        StimConfig(
            pot=FreqPotentials.from_csv(
                comsol_dir
                / "layout2_perp_epair1_makima_seed12_ABeta.csv"
            ),
            freq_hz=2000.0,
            amp_mA=0.15,
            phase_rad=0.0,
        ),
        StimConfig(
            pot=FreqPotentials.from_csv(
                comsol_dir
                / "layout2_perp_epair2_makima_seed12_ABeta.csv"
            ),
            freq_hz=2040.0,
            amp_mA=0.05,
            phase_rad=0.0,
        ),
    ]
    validate_input_sizes(fiber_path, stim_configs)
    if y_cut_mm is not None:
        fiber_path = fiber_path.truncate_by_y(y_cut_mm)

    # ---- 線維分配 ----
    all_unit_ids = filter_target_unit_ids(
        fiber_path.get_unit_ids(), target_unit_ids
    )
    my_unit_ids = split_unit_ids_round_robin(all_unit_ids, rank, size)

    if rank == 0:
        print_start_banner("MRG Frequency Domain Simulation (MPI)")
        print(f"MPI processes: {size}")
        print(f"Total target fibers: {len(all_unit_ids)}")
    print(f"[rank {rank}/{size}] assigned fibers: {my_unit_ids}")

    comm.Barrier()

    # ---- AP count 早期確認：膜電位・座標は保存しない ----
    def on_result(r):
        pass   # summary のみ保持される（_run_loop の keep_full=False 経路）

    local_summary = run_fibers_for_rank(
        fiber_path=fiber_path, stim_configs=stim_configs,
        sim_config=sim_config, t_ms=t_ms,
        my_unit_ids=my_unit_ids,
        simulate_one_fiber_fn=simulate_one_mrg_fiber,
        rank=rank, on_result=on_result,
    )

    gathered = comm.gather(local_summary, root=0)
    if rank == 0:
        merged = merge_summary_dicts(gathered)
        save_results_summary(merged, output_dir, prefix=output_prefix)
        print(f"Done: {datetime.datetime.now()}")
        print(f"Summary fibers: {len(merged)} / requested: {len(all_unit_ids)}")

    comm.Barrier()


if __name__ == "__main__":
    main()
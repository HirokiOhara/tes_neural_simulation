import datetime
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

import numpy as np
from neuron import h

from fiber_path import FiberPathData
from freq_data import FreqPotentials, get_timeseries_at_points
from interp import interpolate_to_axon_nodes, superpose_potentials


# ----------------------------------------------------------------------
# 刺激条件（モデル非依存）
# ----------------------------------------------------------------------
@dataclass
class StimConfig:
    """
    1つの周波数刺激成分の設定。

    「1電極ペア・1周波数」を1要素とする。
    同じCOMSOLファイルから別周波数を取りたい場合も、
    同じ pot を指定して複数のStimConfigを作ればよい。
    """
    pot: FreqPotentials
    freq_hz: float
    amp_mA: float = 1.0
    phase_rad: float = 0.0


# 各モデルの「1本を計算する関数」の型
SimulateOneFiberFn = Callable[
    [FiberPathData, int, List[StimConfig], Any, np.ndarray],
    Dict[str, Any],
]


# ----------------------------------------------------------------------
# NEURON初期化
# ----------------------------------------------------------------------
def initialize_neuron(
    model_dir: Path,
    hoc_files: List[str],
    dll_name: str = "nrnmech.dll",
) -> None:
    """
    NEURONおよびモデルhocを初期化する。

    Parameters
    ----------
    model_dir:
        DLL / hocファイルの置かれたディレクトリ。
    hoc_files:
        xopenするhocファイル名のリスト（モデル固有）。
        例: ["MRGaxonBuilder.hoc"]
    dll_name:
        メカニズムDLL名。

    Notes
    -----
    MPI版でも各rankがこの関数を呼ぶ。
    各MPIプロセスは独立したPythonプロセスであるため、
    全rankでDLL/hocのロードが必要。
    """
    model_dir = Path(model_dir)
    os.chdir(model_dir)

    dll_path = model_dir / dll_name
    if not dll_path.exists():
        raise FileNotFoundError(f"NEURON mechanism DLL not found: {dll_path}")

    h.nrn_load_dll(str(dll_path))
    h.load_file("nrngui.hoc")

    for hoc_file in hoc_files:
        hoc_path = model_dir / hoc_file
        if not hoc_path.exists():
            raise FileNotFoundError(f"hoc file not found: {hoc_path}")
        h.xopen(str(hoc_path))


# ----------------------------------------------------------------------
# 入力サイズ検証（モデル非依存）
# ----------------------------------------------------------------------
def validate_input_sizes(
    fiber_path: FiberPathData,
    stim_configs: List[StimConfig],
) -> None:
    """
    パスCSVとCOMSOL CSVのデータ行数が一致することを確認する。

    行順が一致している前提のため、行数不一致は致命的エラー。
    """
    n_path_points = len(fiber_path.unit_ids)

    for index, stim in enumerate(stim_configs):
        if stim.pot.n_points != n_path_points:
            raise ValueError(
                f"StimConfig[{index}] point count mismatch: "
                f"COMSOL={stim.pot.n_points}, path CSV={n_path_points}. "
                "COMSOL CSV and path CSV must have identical data-row "
                "order and count."
            )


def build_stim_waveform(
    fiber_path, unit_id, stim, t_ms, compartment_positions_um
) -> np.ndarray:
    """1つの StimConfig 成分の膜外電位波形 (n_comp, n_time) を生成。"""
    point_indices = fiber_path.get_point_indices(unit_id)
    comsol_cumulative_dx_um = fiber_path.get_cumulative_dx_um(unit_id)
    if len(point_indices) == 0:
        raise ValueError(f"No path points found for unit_id={unit_id}")

    V_comsol = get_timeseries_at_points(
        pot=stim.pot, point_indices=point_indices,
        freq_hz=stim.freq_hz, amp_mA=stim.amp_mA,
        phase_rad=stim.phase_rad, t_ms=t_ms,
    )
    return interpolate_to_axon_nodes(
        V_at_comsol_points=V_comsol,
        comsol_cumulative_dx_um=comsol_cumulative_dx_um,
        axon_node_positions_um=compartment_positions_um,
    )


def build_all_stim_waveforms(
    fiber_path, unit_id, stim_configs, t_ms, compartment_positions_um
) -> List[np.ndarray]:
    """全 StimConfig 成分の波形リストを生成（重畳しない）。"""
    return [
        build_stim_waveform(fiber_path, unit_id, s, t_ms, compartment_positions_um)
        for s in stim_configs
    ]


def prepare_potential(
    fiber_path, unit_id, stim_configs, t_ms, compartment_positions_um
) -> np.ndarray:
    """
    総膜外電位を計算する。
    生成(build_all_stim_waveforms)と重畳(superpose_potentials)を分離。
    重畳本数は len(stim_configs) で決まる。
    """
    components = build_all_stim_waveforms(
        fiber_path, unit_id, stim_configs, t_ms, compartment_positions_um
    )
    return superpose_potentials(components)


def _run_loop(
    fiber_path, stim_configs, sim_config, t_ms, unit_ids,
    simulate_one_fiber_fn, on_result=None, tag="", verbose=True,
) -> Dict[int, Dict[str, Any]]:
    """
    線維ループの共通実装。

    on_result:
        1本計算するたびに呼ぶコールバック（膜電位・座標の即保存用）。
        指定時は巨大配列をメモリに残さず、summaryのみ返す。
    """
    from result_io import make_result_summary

    keep_full = on_result is None
    out: Dict[int, Dict[str, Any]] = {}

    for unit_id in unit_ids:
        unit_id = int(unit_id)
        if verbose:
            length = fiber_path.get_fiber_length_um(unit_id)
            print(f"{tag}Processing unit_id={unit_id}, "
                  f"fiber_length={length:.3f} um")

        result = simulate_one_fiber_fn(
            fiber_path, unit_id, stim_configs, sim_config, t_ms
        )

        if on_result is not None:
            on_result(result)                      # 即保存
            out[unit_id] = make_result_summary(result)     # 軽量のみ保持
        else:
            out[unit_id] = result                  # 全部保持（逐次・小規模用）

        if verbose:
            print(f"{tag}unit_id={unit_id}: "
                  f"AP count={result['ap_count']}, "
                  f"spikes={np.asarray(result['spike_times_ms']).tolist()}")

    return out


# ----------------------------------------------------------------------
# 逐次実行フレーム（モデル非依存）
# ----------------------------------------------------------------------
def run_fibers_serial(
    fiber_path, stim_configs, sim_config, t_ms,
    simulate_one_fiber_fn, target_unit_ids=None,
    on_result=None, verbose=True,
) -> Dict[int, Dict[str, Any]]:
    """全線維を逐次処理する。on_result指定時はsummaryのみ返す。"""
    unit_ids = filter_target_unit_ids(
        fiber_path.get_unit_ids(), target_unit_ids
    )
    return _run_loop(
        fiber_path, stim_configs, sim_config, t_ms, unit_ids,
        simulate_one_fiber_fn, on_result=on_result, tag="", verbose=verbose,
    )

# ----------------------------------------------------------------------
# MPI: 自rank担当分の計算（モデル非依存）
# ----------------------------------------------------------------------
def run_fibers_for_rank(
    fiber_path, stim_configs, sim_config, t_ms,
    my_unit_ids, simulate_one_fiber_fn, rank,
    on_result=None, verbose=True,
) -> Dict[int, Dict[str, Any]]:
    """自rank担当のunit_idを処理する。on_result指定時はsummaryのみ返す。"""
    return _run_loop(
        fiber_path, stim_configs, sim_config, t_ms, my_unit_ids,
        simulate_one_fiber_fn, on_result=on_result,
        tag=f"[rank {rank}] ", verbose=verbose,
    )

# ----------------------------------------------------------------------
# 対象unit_idの選別（モデル非依存）
# ----------------------------------------------------------------------
def filter_target_unit_ids(
    all_unit_ids: np.ndarray,
    target_unit_ids: Optional[Set[int]],
) -> np.ndarray:
    """target_unit_idsが指定されている場合だけ対象を絞る。"""
    if target_unit_ids is None:
        return np.asarray(all_unit_ids, dtype=int)

    return np.asarray(
        [
            int(unit_id)
            for unit_id in all_unit_ids
            if int(unit_id) in target_unit_ids
        ],
        dtype=int,
    )


# ----------------------------------------------------------------------
# MPI: 線維分配（モデル非依存）
# ----------------------------------------------------------------------
def split_unit_ids_round_robin(
    unit_ids: np.ndarray,
    rank: int,
    size: int,
) -> List[int]:
    """
    unit_idをrankごとに静的ラウンドロビン分割する。

    例:
        unit_ids = [10, 17, 20, 31, 42, 56], size = 3
        rank 0 -> [10, 31]
        rank 1 -> [17, 42]
        rank 2 -> [20, 56]
    """
    return [int(unit_id) for unit_id in unit_ids[rank::size]]


# ----------------------------------------------------------------------
# MPI: summary統合（モデル非依存）
# ----------------------------------------------------------------------
def merge_summary_dicts(
    gathered_summaries: List[Dict[int, Dict[str, Any]]],
) -> Dict[int, Dict[str, Any]]:
    """
    rankごとのsummary辞書を1つに統合する。
    """
    merged: Dict[int, Dict[str, Any]] = {}

    for rank_summary in gathered_summaries:
        for unit_id, summary in rank_summary.items():
            if unit_id in merged:
                raise ValueError(
                    f"Duplicate unit_id in gathered summaries: {unit_id}"
                )
            merged[unit_id] = summary

    return merged


# ----------------------------------------------------------------------
# 時間軸生成ヘルパ（モデル非依存）
# ----------------------------------------------------------------------
def make_time_axis_ms(dt_ms: float, tstop_ms: float) -> np.ndarray:
    """シミュレーション時間軸 [ms] を生成する。"""
    return np.arange(0.0, tstop_ms + dt_ms, dt_ms, dtype=np.float64)


def print_start_banner(title: str) -> None:
    """開始バナーを表示する。"""
    print("=" * 70)
    print(title)
    print("=" * 70)
    print(f"Start: {datetime.datetime.now()}")
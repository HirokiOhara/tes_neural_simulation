import os
import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional, Set

import numpy as np
import pandas as pd
from scipy.io import savemat
from neuron import h

from mrg_axon import MRGaxon
from comsol_data import (
    MultiFreqPotentialsData,
    FiberPathData,
    load_csv_points,
)
from potential_interp import (
    get_potential_timeseries_at_comsol_points,
    interpolate_to_axon_nodes,
    superpose_potentials,
)
from simulation_mrg import (
    SimulationConfig,
    simulate_single_fiber,
)


# =============================================================================
# 設定パラメータ
# =============================================================================
N_ELECTRODE_PAIRS = 4
ELECTRODE_PAIR_IDS = [22, 4, 11, 17]
FREQ_MIN_HZ = 100
FREQ_MAX_HZ = 10000


# =============================================================================
# データクラス
# =============================================================================
@dataclass
class FourierComponent:
    """フーリエ成分"""
    n: int
    frequency_hz: float
    amplitude_mA: float
    phase_rad: float
    electrode_pair_idx: int  # 0, 1, 2, 3, ... (n % N_ELECTRODE_PAIRS)


# =============================================================================
# フーリエ係数読み込み
# =============================================================================
def load_fourier_components(
    filepath: Path,
    freq_min_hz: float,
    freq_max_hz: float,
    n_electrode_pairs: int,
) -> List[FourierComponent]:
    """
    フーリエ係数CSVを読み込み、周波数範囲でフィルタリング。
    電極ペアは n % n_electrode_pairs で自動割り当て。
    """
    df = pd.read_csv(filepath)
    
    components = []
    for _, row in df.iterrows():
        freq = row['frequency_Hz']
        
        # 周波数範囲フィルタ
        if freq < freq_min_hz or freq > freq_max_hz:
            continue
        
        n = int(row['n'])
        comp = FourierComponent(
            n=n,
            frequency_hz=freq,
            amplitude_mA=row['amplitude_mA'],
            phase_rad=row['phase_rad'],
            electrode_pair_idx=(n - 1) % n_electrode_pairs,  # n=1から始まるので-1
        )
        components.append(comp)
    
    return components


def group_components_by_electrode(
    components: List[FourierComponent],
    n_electrode_pairs: int,
) -> Dict[int, List[FourierComponent]]:
    """電極ペアごとにフーリエ成分をグループ化"""
    grouped = {i: [] for i in range(n_electrode_pairs)}
    for comp in components:
        grouped[comp.electrode_pair_idx].append(comp)
    return grouped


# =============================================================================
# 電位時系列合成
# =============================================================================
def synthesize_potential_timeseries(
    pot_data: MultiFreqPotentialsData,
    fiber_path: FiberPathData,
    unit_id: int,
    t_ms: np.ndarray,
    components: List[FourierComponent],
) -> np.ndarray:
    """
    複数のフーリエ成分から電位時系列を合成。
    
    Returns:
        V_comsol: (n_comsol_points, n_time_steps)
    """
    n_points = len(fiber_path.get_cumulative_dx_um(unit_id))
    n_steps = len(t_ms)
    V_total = np.zeros((n_points, n_steps))
    
    for comp in components:
        pot_single = pot_data.to_potentials_data(comp.frequency_hz)
        V_comp = get_potential_timeseries_at_comsol_points(
            pot_single,
            fiber_path,
            unit_id,
            t_ms,
            freq_hz=comp.frequency_hz,
            amp_mA=comp.amplitude_mA,
            phase_rad=comp.phase_rad,
        )
        V_total += V_comp
    
    return V_total


# =============================================================================
# MAT保存関数
# =============================================================================
def save_unit_result_mat(
    output_dir: Path,
    fiber_type: str,
    unit_id: int,
    fiber: MRGaxon,
    fiber_path: FiberPathData,
    result: dict,
    t_ms: np.ndarray,
    freq_min_hz: float,
    freq_max_hz: float,
):
    """1 unit の結果を .mat ファイルで保存"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    x_um = fiber.get_node_positions_um()
    coords_3d_mm = fiber_path.interpolate_1d_to_3d(unit_id, x_um)
    
    comp_types = []
    for comp_idx in range(fiber.n_compartments):
        comp_type, _ = fiber.get_compartment_info(comp_idx)
        comp_types.append(comp_type)
    
    mat_data = {
        'unit_id': np.array([unit_id]),
        'fiber_type': fiber_type,
        'freq_min_hz': np.array([freq_min_hz]),
        'freq_max_hz': np.array([freq_max_hz]),
        't_ms': t_ms.astype(np.float64),
        'x_um': x_um.astype(np.float64),
        'coords_3d_mm': coords_3d_mm.astype(np.float64),
        'compartment_types': np.array(comp_types, dtype=np.int32),
        'n_compartments': np.array([fiber.n_compartments]),
        'n_nodes': np.array([len(fiber.nodes)]),
        'v_membrane_mV': result['v_membrane'].astype(np.float64),
        'ap_count': np.array([result['ap_count']]),
        'spike_times_ms': result['spike_times_ms'].astype(np.float64),
    }
    
    filename = f"{fiber_type}_unit{unit_id:04d}_freq{int(freq_min_hz)}-{int(freq_max_hz)}Hz.mat"
    filepath = output_dir / filename
    savemat(filepath, mat_data, do_compression=True)


# =============================================================================
# サマリー保存関数
# =============================================================================
def save_summary_csv(
    summary_data: List[dict],
    output_dir: Path,
    fiber_type: str,
    freq_min_hz: float,
    freq_max_hz: float,
):
    """サマリーをCSVで保存"""
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{fiber_type}_summary_freq{int(freq_min_hz)}-{int(freq_max_hz)}Hz.csv"
    filepath = output_dir / filename
    
    df = pd.DataFrame(summary_data)
    df.to_csv(filepath, index=False)
    print(f"Saved summary: {filepath} ({len(summary_data)} rows)")


# =============================================================================
# シミュレーション実行
# =============================================================================
def run_interference_simulation(
    fiber_type: str,
    fiber_path: FiberPathData,
    pot_data_list: List[MultiFreqPotentialsData],  # 電極ペアごとの電位データ
    components_by_electrode: Dict[int, List[FourierComponent]],
    sim_config: SimulationConfig,
    t_ms: np.ndarray,
    output_dir: Path,
    freq_min_hz: float,
    freq_max_hz: float,
    target_unit_ids: Optional[Set[int]] = None,
    verbose: bool = True,
) -> List[dict]:
    """干渉刺激シミュレーション実行"""
    
    fiber_lengths = fiber_path.get_all_fiber_lengths_um()
    
    if target_unit_ids is not None:
        unit_ids = sorted(target_unit_ids & set(fiber_lengths.keys()))
    else:
        unit_ids = sorted(fiber_lengths.keys())
    
    total_units = len(unit_ids)
    summary_data = []
    
    print(f"\n{'='*60}")
    print(f"Starting simulation: {fiber_type}")
    print(f"  Frequency range: {freq_min_hz} - {freq_max_hz} Hz")
    print(f"  Units: {total_units}")
    print(f"{'='*60}\n")
    
    for unit_idx, unit_id in enumerate(unit_ids):
        length_um = fiber_lengths[unit_id]
        
        if verbose:
            print(f"  [{unit_idx+1}/{total_units}] unit_id={unit_id}, length={length_um:.1f} um", end="")
        
        # 軸索モデル作成
        fiber = MRGaxon(sim_config.fiber_diameter_um, length_um=length_um)
        node_positions = fiber.get_node_positions_um()
        comsol_dx = fiber_path.get_cumulative_dx_um(unit_id)
        
        # 各電極ペアの電位を合成して重畳
        V_all_electrodes = []
        for elec_idx, pot_data in enumerate(pot_data_list):
            components = components_by_electrode.get(elec_idx, [])
            if not components:
                continue
            
            V_comsol = synthesize_potential_timeseries(
                pot_data, fiber_path, unit_id, t_ms, components
            )
            V_interp = interpolate_to_axon_nodes(V_comsol, comsol_dx, node_positions)
            V_all_electrodes.append(V_interp)
        
        # 全電極の電位を重畳
        V_total = superpose_potentials(V_all_electrodes)
        
        # シミュレーション実行
        result = simulate_single_fiber(fiber, V_total, sim_config)
        
        if verbose:
            print(f" -> AP={result['ap_count']}")
        
        # 結果保存
        # save_unit_result_mat(
        #     output_dir / fiber_type,
        #     fiber_type,
        #     unit_id,
        #     fiber,
        #     fiber_path,
        #     result,
        #     t_ms,
        #     freq_min_hz,
        #     freq_max_hz,
        # )
        
        # サマリーデータ追加
        summary_data.append({
            'unit_id': unit_id,
            'fiber_type': fiber_type,
            'freq_min_hz': freq_min_hz,
            'freq_max_hz': freq_max_hz,
            'ap_count': result['ap_count'],
            'spike_times_ms': str(result['spike_times_ms'].tolist()),
        })
        
        # メモリ解放
        del fiber, result, V_total
        h('forall delete_section()')
    
    # サマリー保存
    save_summary_csv(summary_data, output_dir, fiber_type, freq_min_hz, freq_max_hz)
    
    print(f"\n{'='*60}")
    print(f"Simulation completed: {fiber_type}")
    print(f"{'='*60}\n")
    
    return summary_data


# =============================================================================
# Main
# =============================================================================
def main():
    # =========================================================================
    # パス設定
    # =========================================================================
    PROJECT_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = PROJECT_DIR / "data"
    MODEL_DIR = DATA_DIR / "mrg-model"
    CONFIG_DIR = DATA_DIR / "config"
    COMSOL_DIR = DATA_DIR / "comsol" / "electrode_octagon" / "fft"
    OUTPUT_DIR = DATA_DIR / "output" / "fft"
    
    # =========================================================================
    # NEURON初期化
    # =========================================================================
    os.chdir(MODEL_DIR)
    h.nrn_load_dll(str(MODEL_DIR / "nrnmech.dll"))
    h.load_file("nrngui.hoc")
    h.xopen("MRGaxonBuilder.hoc")
    
    # =========================================================================
    # シミュレーション設定
    # =========================================================================
    sim_config = SimulationConfig(
        dt_ms=0.01,
        tstop_ms=100.0,
        v_init_mV=-80.0,
        ap_threshold_mV=0.0,
        fiber_diameter_um=8.7,
    )
    
    t_ms = np.arange(0.0, sim_config.tstop_ms + sim_config.dt_ms, sim_config.dt_ms)
    
    # =========================================================================
    # 対象unit_id（Noneで全unit）
    # =========================================================================
    # target_unit_ids = {7, 20, 78}  # デバッグ用
    target_unit_ids = {7, 12, 15, 20, 23, 32, 39, 40, 49, 54, 61, 63, 64, 68, 70, 74, 76, 78, 81, 82, 103, 105, 107, 112, 114, 115, 121, 125, 126, 127, 129, 159, 189, 190, 191, 195, 214, 218, 226, 227, 233, 243, 246, 248, 249, 250, 257, 259, 261, 262, 274, 279, 289, 300, 303, 304, 310, 314, 327, 341, 346, 352, 361, 369, 377, 380, 389, 392, 401, 404, 412, 423, 425, 442, 443, 448, 451, 457, 466, 469, 472, 474, 477, 482, 493, 500, 505, 506, 521, 522, 524, 534, 536} #  --x_min -5 --x_max 1 --y_min -27.3 --y_max -21.3
    # target_unit_ids = None  # 全unit
    
    print(f"\nStart: {datetime.datetime.now()}")
    
    # =========================================================================
    # フーリエ係数読み込み
    # =========================================================================
    fourier_components = load_fourier_components(
        CONFIG_DIR / "fourier_components.csv",
        freq_min_hz=FREQ_MIN_HZ,
        freq_max_hz=FREQ_MAX_HZ,
        n_electrode_pairs=N_ELECTRODE_PAIRS,
    )
    
    print(f"\nLoaded {len(fourier_components)} Fourier components")
    print(f"  Frequency range: {FREQ_MIN_HZ} - {FREQ_MAX_HZ} Hz")
    
    # 電極ペアごとにグループ化
    components_by_electrode = group_components_by_electrode(
        fourier_components, N_ELECTRODE_PAIRS
    )
    
    for elec_idx, comps in components_by_electrode.items():
        freqs = [c.frequency_hz for c in comps]
        print(f"  Electrode pair {ELECTRODE_PAIR_IDS[elec_idx]}: {len(comps)} components")
        if freqs:
            print(f"    Frequencies: {freqs[:5]}{'...' if len(freqs) > 5 else ''}")
    
    # =========================================================================
    # RA1 処理
    # =========================================================================
    print("\n===== Processing RA1 =====")
    
    ra1_path = FiberPathData(
        points=load_csv_points(CONFIG_DIR / "points_along_ra1_fibers.csv"),
        interval_mm=0.1,
    )
    
    # 電極ペアごとの電位データ読み込み
    ra1_pot_list = []
    for pair_id in ELECTRODE_PAIR_IDS:
        pot_data = MultiFreqPotentialsData.from_multi_frequency_csv(
            COMSOL_DIR / f"potentials_along_ra1_fiber_electrodes_{pair_id}.csv"
        )
        ra1_pot_list.append(pot_data)
        print(f"  Loaded electrode pair {pair_id}: {sorted(pot_data.frequencies)[:5]}...")
    
    ra1_summary = run_interference_simulation(
        fiber_type="ra1",
        fiber_path=ra1_path,
        pot_data_list=ra1_pot_list,
        components_by_electrode=components_by_electrode,
        sim_config=sim_config,
        t_ms=t_ms,
        output_dir=OUTPUT_DIR,
        freq_min_hz=FREQ_MIN_HZ,
        freq_max_hz=FREQ_MAX_HZ,
        target_unit_ids=target_unit_ids,
        verbose=True,
    )
    
    # =========================================================================
    # RA2 処理
    # =========================================================================
    # print("\n===== Processing RA2 =====")
    
    # ra2_path = FiberPathData(
    #     points=load_csv_points(CONFIG_DIR / "points_along_ra2_fibers.csv"),
    #     interval_mm=0.1,
    # )
    
    # ra2_pot_list = []
    # for pair_id in ELECTRODE_PAIR_IDS:
    #     pot_data = MultiFreqPotentialsData.from_multi_frequency_csv(
    #         COMSOL_DIR / f"potentials_along_ra2_fiber_electrodes_{pair_id}.csv"
    #     )
    #     ra2_pot_list.append(pot_data)
    
    # ra2_summary = run_interference_simulation(
    #     fiber_type="ra2",
    #     fiber_path=ra2_path,
    #     pot_data_list=ra2_pot_list,
    #     components_by_electrode=components_by_electrode,
    #     sim_config=sim_config,
    #     t_ms=t_ms,
    #     output_dir=OUTPUT_DIR,
    #     freq_min_hz=FREQ_MIN_HZ,
    #     freq_max_hz=FREQ_MAX_HZ,
    #     target_unit_ids=target_unit_ids,
    #     verbose=True,
    # )
    
    # =========================================================================
    # SA1 処理
    # =========================================================================
    # print("\n===== Processing SA1 =====")
    
    # sa1_path = FiberPathData(
    #     points=load_csv_points(CONFIG_DIR / "points_along_sa1_fibers.csv"),
    #     interval_mm=0.1,
    # )
    
    # sa1_pot_list = []
    # for pair_id in ELECTRODE_PAIR_IDS:
    #     pot_data = MultiFreqPotentialsData.from_multi_frequency_csv(
    #         COMSOL_DIR / f"potentials_along_sa1_fiber_electrodes_{pair_id}.csv"
    #     )
    #     sa1_pot_list.append(pot_data)
    
    # sa1_summary = run_interference_simulation(
    #     fiber_type="sa1",
    #     fiber_path=sa1_path,
    #     pot_data_list=sa1_pot_list,
    #     components_by_electrode=components_by_electrode,
    #     sim_config=sim_config,
    #     t_ms=t_ms,
    #     output_dir=OUTPUT_DIR,
    #     freq_min_hz=FREQ_MIN_HZ,
    #     freq_max_hz=FREQ_MAX_HZ,
    #     target_unit_ids=target_unit_ids,
    #     verbose=True,
    # )
    
    # =========================================================================
    # 結果サマリー表示
    # =========================================================================
    print("\n===== Summary =====")
    # for name, summary in [("RA1", ra1_summary), ("RA2", ra2_summary), ("SA1", sa1_summary)]:
    for name, summary in [("RA1", ra1_summary)]:
        total_ap = sum(s['ap_count'] for s in summary)
        active_units = sum(1 for s in summary if s['ap_count'] > 0)
        print(f"  {name}: {active_units}/{len(summary)} units active, total AP={total_ap}")
    
    print(f"\nDone: {datetime.datetime.now()}")


if __name__ == "__main__":
    main()
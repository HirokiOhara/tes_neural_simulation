import os
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple
import datetime
import json

import numpy as np
import pandas as pd
from scipy.io import savemat

from neuron import h, gui

from mpi4py import MPI

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

from mrg_axon import MRGaxon
from comsol_data import (
    PotentialsData, 
    FiberPathData, 
    MultiFreqPotentialsData,
    load_csv_points,
    coord_key,
)
from potential_interp import (
    interpolate_to_axon_nodes,
)
from simulation_mrg import SimulationConfig, simulate_single_fiber


# =============================================================================
# Configuration
# =============================================================================

# 周波数設定
FREQ1_LIST = [2000]
FREQ2_OFFSETS = [0, 40]

# シミュレーション設定
DT_MS = 0.01
TSTOP_MS = 100.0
V_INIT_MV = -80.0
AP_THRESHOLD_MV = 0.0
FIBER_DIAMETER_UM = 8.7

# 振幅設定
STIM_AMPLITUDE_MA = 0.2

# 座標照合設定
COORD_DECIMALS = 4

# 出力設定
SAVE_MAT = False
MAT_SAVE_WAVEFORMS = False

# Fiber type設定
FIBER_TYPES = ['ra1', 'ra2', 'sa1']

# 各fiber typeに対応するtarget_unit_ids
# FIBER_TYPE_UNIT_IDS = {
#     'ra1': {7, 12, 15, 20, 23, 32, 39, 40, 49, 54, 61, 63, 64, 68, 70, 74, 76, 78, 81, 82, 103, 105, 107, 112, 114, 115, 121, 125, 126, 127, 129, 159, 189, 190, 191, 195, 214, 218, 226, 227, 233, 243, 246, 248, 249, 250, 257, 259, 261, 262, 274, 279, 289, 300, 303, 304, 310, 314, 327},
#     'ra2': {341, 346, 352, 361, 369},
#     'sa1': {377, 380, 389, 392, 401, 404, 412, 423, 425, 442, 443, 448, 451, 457, 466, 469, 472, 474, 477, 482, 493, 500, 505, 506, 521, 522, 524, 534, 536},
# }
FIBER_TYPE_UNIT_IDS = {
    'ra1': None,  # すべてのunitを実行
    'ra2': None,  # すべてのunitを実行
    'sa1': None,  # すべてのunitを実行
}

@dataclass
class SweepConfig:
    """時間変化振幅スイープの設定"""
    freq1_hz: float
    freq2_hz: float
    total_amplitude_mA: float = STIM_AMPLITUDE_MA
    
    @property
    def label(self) -> str:
        return f"f1={int(self.freq1_hz)}_f2={int(self.freq2_hz)}"


@dataclass
class FiberTypeData:
    """各fiber typeのデータを保持"""
    fiber_type: str
    pot_data_elec1: MultiFreqPotentialsData
    pot_data_elec2: MultiFreqPotentialsData
    fiber_path: FiberPathData
    target_unit_ids: set


# =============================================================================
# Time-Varying Amplitude Potential Generation
# =============================================================================

def generate_time_varying_potential(
    pot_data1: PotentialsData,
    pot_data2: PotentialsData,
    fiber_path: FiberPathData,
    unit_id: int,
    t_ms: np.ndarray,
    freq1_hz: float,
    freq2_hz: float,
    total_amplitude_mA: float,
    node_positions_um: np.ndarray,
) -> np.ndarray:
    """
    時間変化する振幅比で2電極の電位を合成
    """
    n_steps = len(t_ms)
    tstop = t_ms[-1]
    
    amp1_t = total_amplitude_mA * (1.0 - t_ms / tstop)
    amp2_t = total_amplitude_mA * (t_ms / tstop)
    
    comsol_dx = fiber_path.get_cumulative_dx_um(unit_id)
    
    V_complex1 = _get_complex_potential_at_unit(
        pot_data1, fiber_path, unit_id, freq1_hz
    )
    V_complex2 = _get_complex_potential_at_unit(
        pot_data2, fiber_path, unit_id, freq2_hz
    )
    
    if V_complex1 is None or V_complex2 is None:
        return np.zeros((len(node_positions_um), n_steps), dtype=np.float32)
    
    t_s = t_ms * 1e-3
    
    phase1 = 2.0 * np.pi * freq1_hz * t_s
    V1_comsol = np.real(
        (amp1_t[None, :] * V_complex1[:, None]) * np.exp(1j * phase1[None, :])
    )
    
    phase2 = 2.0 * np.pi * freq2_hz * t_s
    V2_comsol = np.real(
        (amp2_t[None, :] * V_complex2[:, None]) * np.exp(1j * phase2[None, :])
    )
    
    V_comsol = V1_comsol + V2_comsol
    
    V_total = interpolate_to_axon_nodes(
        V_comsol.astype(np.float32),
        comsol_dx,
        node_positions_um
    )
    
    return V_total


def _get_complex_potential_at_unit(
    pot_data: PotentialsData,
    fiber_path: FiberPathData,
    unit_id: int,
    freq_hz: float,
) -> Optional[np.ndarray]:
    """
    指定unit_idのCOMSOL点における複素電位を取得
    """
    xyz_coords = fiber_path.get_xyz_coords(unit_id)
    if len(xyz_coords) == 0:
        return None
    
    indices = []
    for xyz in xyz_coords:
        key = coord_key(xyz, COORD_DECIMALS)
        if key in pot_data.coord_to_index:
            indices.append(pot_data.coord_to_index[key])
        else:
            return None
    
    indices = np.array(indices, dtype=int)
    
    V_complex = pot_data.get_potential_at_frequency(freq_hz)
    if V_complex is None:
        return None
    
    return V_complex[indices]


# =============================================================================
# Single Unit Simulation (Worker Function)
# =============================================================================

def simulate_single_unit(
    unit_id: int,
    fiber_type: str,
    pot_data1: PotentialsData,
    pot_data2: PotentialsData,
    fiber_path: FiberPathData,
    t_ms: np.ndarray,
    cfg: SweepConfig,
    sim_config: SimulationConfig,
    fiber_lengths: Dict[int, float],
) -> Optional[Dict[str, Any]]:
    """
    単一unit_idのシミュレーションを実行
    """
    length_um = fiber_lengths.get(unit_id, 0)
    if length_um <= 0:
        return None
    
    # 軸索モデル作成
    fiber = MRGaxon(FIBER_DIAMETER_UM, length_um=length_um)
    node_positions = fiber.get_node_positions_um()
    
    # 時間変化振幅での電位生成
    V_total = generate_time_varying_potential(
        pot_data1, pot_data2,
        fiber_path, unit_id,
        t_ms,
        cfg.freq1_hz, cfg.freq2_hz,
        cfg.total_amplitude_mA,
        node_positions,
    )
    
    # シミュレーション実行
    result = simulate_single_fiber(fiber, V_total, sim_config)
    
    return {
        'fiber_type': fiber_type,
        'unit_id': unit_id,
        'fiber_length_um': length_um,
        'n_compartments': fiber.n_compartments,
        'ap_count': result['ap_count'],
        'spike_times_ms': result['spike_times_ms'],
        'V_min': float(V_total.min()),
        'V_max': float(V_total.max()),
    }


# =============================================================================
# Main Sweep Function (MPI Parallelized)
# =============================================================================

def run_sweep_mpi(
    fiber_type_data_list: List[FiberTypeData],
    output_dir: Path,
    sweep_configs: List[SweepConfig],
    verbose: bool = True,
) -> pd.DataFrame:
    """
    MPI並列化された時間変化振幅スイープ（全fiber type統合版）
    """
    # rank 0 のみディレクトリ作成
    if rank == 0:
        output_dir.mkdir(parents=True, exist_ok=True)
    comm.Barrier()
    
    # シミュレーション設定
    sim_config = SimulationConfig(
        dt_ms=DT_MS,
        tstop_ms=TSTOP_MS,
        v_init_mV=V_INIT_MV,
        ap_threshold_mV=AP_THRESHOLD_MV,
        fiber_diameter_um=FIBER_DIAMETER_UM,
    )
    
    # 時間ベクトル
    n_steps = int(TSTOP_MS / DT_MS) + 1
    t_ms = np.linspace(0.0, TSTOP_MS, n_steps)
    
    # 全タスクリストを作成 (fiber_type, unit_id, cfg)のタプル
    all_tasks = []
    for fiber_data in fiber_type_data_list:
        all_unit_ids = fiber_data.fiber_path.get_unit_ids()
        if fiber_data.target_unit_ids is None:
            unit_ids = all_unit_ids
        else:
            unit_ids = [uid for uid in all_unit_ids if uid in fiber_data.target_unit_ids]
        
        for cfg in sweep_configs:
            for unit_id in unit_ids:
                all_tasks.append((fiber_data, unit_id, cfg))
    
    if rank == 0 and verbose:
        print(f"\n{'='*60}")
        print(f"Total tasks: {len(all_tasks)}")
        print(f"MPI processes: {size}")
        print(f"Sweep configurations: {len(sweep_configs)}")
        for cfg in sweep_configs:
            print(f"  {cfg.label}")
        print(f"Fiber types: {len(fiber_type_data_list)}")
        for fiber_data in fiber_type_data_list:
            # unit数を計算
            all_unit_ids = fiber_data.fiber_path.get_unit_ids()
            if fiber_data.target_unit_ids is None:
                unit_ids = all_unit_ids
            else:
                unit_ids = [uid for uid in all_unit_ids if uid in fiber_data.target_unit_ids]
            print(f"  {fiber_data.fiber_type}: {len(unit_ids)} units")
        print(f"{'='*60}")
    
    # タスクをプロセス間で分割
    my_tasks = [task for i, task in enumerate(all_tasks) if i % size == rank]
    
    if rank == 0 and verbose:
        print(f"  Rank 0 processing {len(my_tasks)} tasks")
    
    # 各プロセスで担当タスクをシミュレーション
    local_results = []
    for fiber_data, unit_id, cfg in my_tasks:
        # 該当周波数のPotentialsDataを抽出
        try:
            pot_data1 = fiber_data.pot_data_elec1.to_potentials_data(cfg.freq1_hz, COORD_DECIMALS)
            pot_data2 = fiber_data.pot_data_elec2.to_potentials_data(cfg.freq2_hz, COORD_DECIMALS)
        except ValueError as e:
            if verbose:
                print(f"  [Rank {rank}] Error extracting potential data: {e}")
            continue
        
        fiber_lengths = fiber_data.fiber_path.get_all_fiber_lengths_um()
        
        result = simulate_single_unit(
            unit_id, fiber_data.fiber_type,
            pot_data1, pot_data2,
            fiber_data.fiber_path, t_ms, cfg, sim_config, fiber_lengths
        )
        
        if result is not None:
            result['freq1_hz'] = cfg.freq1_hz
            result['freq2_hz'] = cfg.freq2_hz
            local_results.append(result)
            
            if verbose:
                print(f"  [Rank {rank}] {fiber_data.fiber_type} unit_id={unit_id}, "
                      f"{cfg.label}, "
                      f"V=[{result['V_min']:.3f}, {result['V_max']:.3f}] mV, "
                      f"AP={result['ap_count']}")
    
    # 全プロセスの結果を収集
    all_local_results = comm.gather(local_results, root=0)
    
    if rank == 0:
        # 結果をフラット化
        all_results = []
        for proc_results in all_local_results:
            all_results.extend(proc_results)
        
        # 周波数設定ごとにMATファイル保存
        if SAVE_MAT:
            for cfg in sweep_configs:
                cfg_results = [r for r in all_results 
                             if r['freq1_hz'] == cfg.freq1_hz and r['freq2_hz'] == cfg.freq2_hz]
                
                if len(cfg_results) > 0:
                    mat_data = {
                        'freq1_hz': cfg.freq1_hz,
                        'freq2_hz': cfg.freq2_hz,
                        't_ms': t_ms,
                        'amplitude_sweep': '100:0 -> 0:100',
                        'fiber_types': np.array([r['fiber_type'] for r in cfg_results], dtype=object),
                        'unit_ids': np.array([r['unit_id'] for r in cfg_results]),
                        'ap_counts': np.array([r['ap_count'] for r in cfg_results]),
                    }
                    
                    # 各unitのスパイク時刻を追加
                    for r in cfg_results:
                        key = f"{r['fiber_type']}_unit_{r['unit_id']}"
                        spike_times = r['spike_times_ms']
                        if isinstance(spike_times, str):
                            spike_times = np.array(json.loads(spike_times))
                        mat_data[key] = spike_times
                    
                    mat_path = output_dir / f"results_{cfg.label}.mat"
                    savemat(mat_path, mat_data)
                    if verbose:
                        print(f"  Saved: {mat_path}")
        
        # サマリーCSV保存
        summary_data = []
        for r in all_results:
            spike_times = r['spike_times_ms']
            if isinstance(spike_times, np.ndarray):
                spike_times_str = json.dumps(spike_times.tolist())
            else:
                spike_times_str = spike_times
                
            summary_data.append({
                'freq1_hz': r['freq1_hz'],
                'freq2_hz': r['freq2_hz'],
                'unit_id': r['unit_id'],
                'fiber_length_um': r['fiber_length_um'],
                'n_compartments': r['n_compartments'],
                'ap_count': r['ap_count'],
                'spike_times_ms': spike_times_str,
            })
        
        summary_df = pd.DataFrame(summary_data)
        summary_path = output_dir / "summary.csv"
        summary_df.to_csv(summary_path, index=False)
        
        if verbose:
            print(f"\nSummary saved: {summary_path}")
            print(f"Total records: {len(summary_df)}")
        
        return summary_df
    else:
        return pd.DataFrame()
    
    comm.Barrier()


# =============================================================================
# Entry Point
# =============================================================================

def main():
    """メイン実行関数"""
    
    # ファイルパス設定
    PROJECT_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = PROJECT_DIR / "data"
    MODEL_DIR = DATA_DIR / "mrg-model"
    CONFIG_DIR = DATA_DIR / "config"
    COMSOL_DIR = DATA_DIR / "comsol" / "electrode_side"
    OUTPUT_DIR = DATA_DIR / "output" / "sweep_mrg"

    os.chdir(MODEL_DIR)
    h.nrn_load_dll(str(MODEL_DIR / "nrnmech.dll"))
    h.load_file("nrngui.hoc")
    h.xopen("MRGaxonBuilder.hoc")

    if rank == 0:
        print("Loading data...")
    
    # 全fiber typeのデータを読み込み
    fiber_type_data_list = []
    
    for fiber_type in FIBER_TYPES:
        # 入力ファイルパス
        potential_csv_elec1 = COMSOL_DIR / f"potentials_along_{fiber_type}_fiber_electrodes_1.csv"
        potential_csv_elec2 = COMSOL_DIR / f"potentials_along_{fiber_type}_fiber_electrodes_2.csv"
        fiber_path_csv = CONFIG_DIR / f"points_along_{fiber_type}_fibers.csv"
        
        # ファイル存在確認
        for f in [potential_csv_elec1, potential_csv_elec2, fiber_path_csv]:
            if not f.exists():
                if rank == 0:
                    print(f"Error: File not found: {f}")
                sys.exit(1)
        
        # データ読み込み（全プロセスで読み込む）
        pot_data_elec1 = MultiFreqPotentialsData.from_multi_frequency_csv(
            potential_csv_elec1, decimals=COORD_DECIMALS
        )
        pot_data_elec2 = MultiFreqPotentialsData.from_multi_frequency_csv(
            potential_csv_elec2, decimals=COORD_DECIMALS
        )
        
        points = load_csv_points(fiber_path_csv)
        fiber_path = FiberPathData(points=points, interval_mm=0.1)
        
        # target_unit_idsの処理
        target_ids = FIBER_TYPE_UNIT_IDS[fiber_type]
        
        fiber_type_data_list.append(FiberTypeData(
            fiber_type=fiber_type,
            pot_data_elec1=pot_data_elec1,
            pot_data_elec2=pot_data_elec2,
            fiber_path=fiber_path,
            target_unit_ids=target_ids,  # Noneの場合はすべて実行
        ))
        
        if rank == 0:
            print(f"  {fiber_type.upper()}:")
            print(f"    Electrode 1: {pot_data_elec1.n_points} points, {pot_data_elec1.n_frequencies} frequencies")
            print(f"    Electrode 2: {pot_data_elec2.n_points} points, {pot_data_elec2.n_frequencies} frequencies")
            print(f"    Fiber paths: {len(fiber_path.get_unit_ids())} units")
            if target_ids is None:
                print(f"    Target units: ALL units")
            else:
                print(f"    Target units: {len(target_ids)} units")
    
    if rank == 0:
        print(f"  MPI processes: {size}")
    
    # スイープ設定を生成
    sweep_configs = []
    for freq1 in FREQ1_LIST:
        for offset in FREQ2_OFFSETS:
            freq2 = freq1 + offset
            sweep_configs.append(SweepConfig(
                freq1_hz=freq1,
                freq2_hz=freq2,
                total_amplitude_mA=STIM_AMPLITUDE_MA,
            ))
    
    if rank == 0:
        print(f"\nSweep configurations: {len(sweep_configs)}")
        for cfg in sweep_configs:
            print(f"  {cfg.label}")
    
    # 出力ディレクトリ
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = OUTPUT_DIR / f"sweep_{timestamp}"
    
    # スイープ実行
    if rank == 0:
        print("\nStarting simulation...")
    
    summary_df = run_sweep_mpi(
        fiber_type_data_list=fiber_type_data_list,
        output_dir=output_dir,
        sweep_configs=sweep_configs,
        verbose=True,
    )
    
    # 結果サマリー表示（rank 0のみ）
    # if rank == 0:
    #     print("\n" + "="*60)
    #     print("Results Summary")
    #     print("="*60)
        
    #     for fiber_type in FIBER_TYPES:
    #         print(f"\n{fiber_type.upper()}:")
    #         for cfg in sweep_configs:
    #             subset = summary_df[
    #                 (summary_df['fiber_type'] == fiber_type) &
    #                 (summary_df['freq1_hz'] == cfg.freq1_hz) & 
    #                 (summary_df['freq2_hz'] == cfg.freq2_hz)
    #             ]
    #             activated = subset[subset['ap_count'] > 0]
    #             print(f"  {cfg.label}:")
    #             print(f"    Total units: {len(subset)}")
    #             print(f"    Activated units: {len(activated)}")
    #             if len(activated) > 0:
    #                 print(f"    Activated unit_ids: {sorted(activated['unit_id'].tolist())}")
        
    #     print(f"\nOutput directory: {output_dir}")


if __name__ == "__main__":
    main()
"""
MRG軸索モデルのシミュレーション実行スクリプト
- 周波数領域（複素数）と時間領域（実数時系列）の両方に対応
"""
import os
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Set, Tuple
import datetime

import numpy as np
import pandas as pd
from neuron import h

from mrg_axon import MRGaxon
from comsol_data import PotentialsData, FiberPathData, load_csv_points, DomainType
from potential_interp import (
    get_potential_timeseries_at_comsol_points,
    interpolate_to_axon_nodes,
    superpose_potentials,
)


# =============================================================================
# Configuration Dataclasses
# =============================================================================

@dataclass
class StimulationConfigFreq:
    """刺激パラメータ（周波数領域・1電極ペア分）"""
    pot_data: PotentialsData
    freq_hz: float
    amp_mA: float = 1.0
    phase_rad: float = 0.0


@dataclass
class StimulationConfigTime:
    """刺激パラメータ（時間領域）"""
    pot_data: PotentialsData
    amp_scale: float = 1.0  # 振幅スケーリング係数


@dataclass
class SimulationConfig:
    """シミュレーション全体の設定"""
    dt_ms: float = 0.01
    tstop_ms: float = 100.0
    v_init_mV: float = -80.0
    ap_threshold_mV: float = 0.0
    fiber_diameter_um: float = 8.7


# =============================================================================
# Core Simulation Function
# =============================================================================

def simulate_single_fiber(
    fiber: MRGaxon,
    V_extracellular: np.ndarray,
    config: SimulationConfig,
) -> Dict[str, Any]:
    """
    単一軸索のシミュレーション実行
    
    Parameters
    ----------
    fiber : MRGaxon
        軸索モデル
    V_extracellular : (n_compartments, n_steps) 膜外電位[mV]
    config : SimulationConfig
        シミュレーション設定
    
    Returns
    -------
    dict with keys:
        - 'v_membrane': (n_compartments, n_steps) 膜電位
        - 'ap_count': int
        - 'spike_times_ms': np.ndarray
    """
    n_compartments = fiber.n_compartments
    n_steps = V_extracellular.shape[1]
    
    # 入力検証
    if V_extracellular.shape[0] != n_compartments:
        raise ValueError(
            f"V_extracellular shape[0]={V_extracellular.shape[0]} != n_compartments={n_compartments}"
        )
    
    # NEURON設定
    h.v_init = config.v_init_mV
    h.dt = config.dt_ms
    h.tstop = config.tstop_ms
    
    t_vec = h.Vector(np.linspace(0.0, config.tstop_ms, n_steps).tolist())
    
    # 刺激と記録の設定
    stim_vectors = []
    rec_vectors = []
    
    for i, sec in enumerate(fiber.section_list_all):
        # 膜外電位を設定
        v_stim = h.Vector(V_extracellular[i].tolist())
        v_stim.play(sec(0.5)._ref_e_extracellular, t_vec, False)
        stim_vectors.append(v_stim)
        
        # 膜電位を記録
        v_rec = h.Vector()
        v_rec.record(sec(0.5)._ref_v)
        rec_vectors.append(v_rec)
    
    # APカウンタ設定（最終ノード）
    apc = h.APCount(fiber.nodes[-1](0.5))
    apc.thresh = config.ap_threshold_mV
    spike_times_vec = h.Vector()
    apc.record(spike_times_vec)
    
    # 実行
    h.finitialize(h.v_init)
    h.continuerun(h.tstop)
    
    # 結果取得
    v_membrane = np.zeros((n_compartments, n_steps), dtype=np.float64)
    for i, vec in enumerate(rec_vectors):
        arr = np.array(vec.as_numpy())
        v_membrane[i, :len(arr)] = arr[:n_steps]
    
    return {
        'v_membrane': v_membrane,
        'ap_count': int(apc.n),
        'spike_times_ms': np.array(spike_times_vec.as_numpy()),
    }


# =============================================================================
# Potential Preparation Functions
# =============================================================================

def prepare_potential_frequency_domain(
    fiber_path: FiberPathData,
    unit_id: int,
    stim_configs: List[StimulationConfigFreq],
    t_ms: np.ndarray,
    node_positions_um: np.ndarray,
) -> np.ndarray:
    """
    周波数領域: 複数電極ペアの電位を計算して重畳
    
    Returns
    -------
    V_total : (n_nodes, n_steps) 膜外電位[mV]
    """
    comsol_dx = fiber_path.get_cumulative_dx_um(unit_id)
    
    V_components = []
    for stim in stim_configs:
        # COMSOL点での電位時系列
        V_comsol = get_potential_timeseries_at_comsol_points(
            stim.pot_data, fiber_path, unit_id, t_ms,
            freq_hz=stim.freq_hz,
            amp_mA=stim.amp_mA,
            phase_rad=stim.phase_rad,
        )
        # 軸索ノードに補間
        V_interp = interpolate_to_axon_nodes(V_comsol, comsol_dx, node_positions_um)
        V_components.append(V_interp)
    
    return superpose_potentials(V_components)



# =============================================================================
# Batch Processing
# =============================================================================

def process_fiber_type_frequency(
    fiber_path: FiberPathData,
    stim_configs: List[StimulationConfigFreq],
    sim_config: SimulationConfig,
    t_ms: np.ndarray,
    target_unit_ids: Optional[Set[int]] = None,
    verbose: bool = True,
) -> Tuple[Dict[int, Dict[str, Any]], Dict[int, MRGaxon]]:
    """
    周波数領域: 1つの神経タイプの全線維をシミュレーション
    """
    results = {}
    fiber_models = {}
    fiber_lengths = fiber_path.get_all_fiber_lengths_um()
    
    for unit_id, length_um in fiber_lengths.items():
        if target_unit_ids is not None and unit_id not in target_unit_ids:
            continue
        
        if verbose:
            print(f"Processing unit_id={unit_id}, length={length_um:.1f} um")
        
        # 軸索モデル作成
        fiber = MRGaxon(sim_config.fiber_diameter_um, length_um=length_um)
        fiber_models[unit_id] = fiber
        
        node_positions = fiber.get_node_positions_um()
        
        # 電位計算（周波数領域）
        V_total = prepare_potential_frequency_domain(
            fiber_path, unit_id, stim_configs, t_ms, node_positions
        )
        
        if verbose:
            print(f"  V_total range: [{V_total.min():.3f}, {V_total.max():.3f}] mV")
        
        # シミュレーション実行
        result = simulate_single_fiber(fiber, V_total, sim_config)
        result['V_extracellular'] = V_total
        results[unit_id] = result
        
        if verbose:
            print(f"  AP count: {result['ap_count']}, spikes: {result['spike_times_ms']}")
    
    return results, fiber_models




# =============================================================================
# Output Functions
# =============================================================================

# コンパートメントタイプの定数（MRGaxonと同じ）
TYPE_NODE = 0
TYPE_MYSA = 1
TYPE_FLUT = 2
TYPE_STIN = 3

TYPE_NAMES = {
    TYPE_NODE: 'node',
    TYPE_MYSA: 'mysa',
    TYPE_FLUT: 'flut',
    TYPE_STIN: 'stin',
}

def save_results_all_1d(
    results: Dict[int, Dict[str, Any]],
    fiber_models: Dict[int, MRGaxon],
    output_dir: Path,
    dt_ms: float,
    prefix: str = "vm",
):
    """
    形式2: 全コンパートメントを1D座標で保存
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    rows = []
    n_steps = None
    
    for unit_id, result in results.items():
        fiber = fiber_models[unit_id]
        node_positions_um = fiber.get_node_positions_um()
        v_membrane = result['v_membrane']
        
        if n_steps is None:
            n_steps = v_membrane.shape[1]
        
        for comp_idx in range(fiber.n_compartments):
            comp_type, _ = fiber.get_compartment_info(comp_idx)
            type_name = TYPE_NAMES[comp_type]
            
            row = [
                unit_id,
                node_positions_um[comp_idx],
                type_name,
            ]
            row.extend(v_membrane[comp_idx, :].tolist())
            rows.append(row)
    
    header = ['unit_id', 'x_um', 'type']
    header.extend([f'V_t{i}' for i in range(n_steps)])
    
    filepath = output_dir / f"{prefix}_all_1d.csv"
    _save_csv_mixed_types(filepath, header, rows)
    
    print(f"Saved: {filepath} ({len(rows)} rows, all compartments)")


def save_results_summary(
    results: Dict[int, Dict[str, Any]],
    fiber_path: FiberPathData,
    fiber_models: Dict[int, MRGaxon],
    output_dir: Path,
    prefix: str = "vm",
):
    """
    サマリー情報を保存
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    rows = []
    for unit_id, result in results.items():
        fiber = fiber_models[unit_id]
        n_nodes = len(fiber.nodes)
        
        rows.append({
            'unit_id': unit_id,
            'n_nodes': n_nodes,
            'n_compartments': fiber.n_compartments,
            'fiber_length_um': fiber_path.get_fiber_length_um(unit_id),
            'ap_count': result['ap_count'],
            'spike_times_ms': str(result['spike_times_ms'].tolist()),
        })
    
    filepath = output_dir / f"{prefix}_summary.csv"
    pd.DataFrame(rows).to_csv(filepath, index=False)
    
    print(f"Saved: {filepath} ({len(rows)} rows)")


# =============================================================================
# Helper Functions
# =============================================================================

def _save_csv_with_header(filepath: Path, header: list, rows: list):
    """数値データのCSV保存"""
    data = np.array(rows, dtype=np.float64)
    
    with open(filepath, 'w') as f:
        f.write(','.join(header) + '\n')
    with open(filepath, 'ab') as f:
        np.savetxt(f, data, delimiter=',', fmt='%.6g')


def _save_csv_mixed_types(filepath: Path, header: list, rows: list):
    """文字列を含むデータのCSV保存"""
    df = pd.DataFrame(rows, columns=header)
    df.to_csv(filepath, index=False, float_format='%.6g')


# =============================================================================
# Main
# =============================================================================

def main():
    # パス設定
    PROJECT_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = PROJECT_DIR / "data"
    MODEL_DIR = DATA_DIR / "mrg-model"
    CONFIG_DIR = DATA_DIR / "config"
    COMSOL_DIR = DATA_DIR / "comsol" / "direction_E"
    OUTPUT_DIR = DATA_DIR / "output"
    
    # NEURON初期化
    os.chdir(MODEL_DIR)
    h.nrn_load_dll(str(MODEL_DIR / "nrnmech.dll"))
    h.load_file("nrngui.hoc")
    h.xopen("MRGaxonBuilder.hoc")
    
    # シミュレーション設定
    sim_config = SimulationConfig(
        dt_ms=0.01,
        tstop_ms=100.0,
        v_init_mV=-80.0,
        ap_threshold_mV=0.0,
        fiber_diameter_um=8.7,
    )
    
    t_ms = np.arange(0.0, sim_config.tstop_ms + sim_config.dt_ms, sim_config.dt_ms)

    print(f"Start: {datetime.datetime.now()}")
    
    # ===== 周波数領域シミュレーション (RA1) =====
    print("\n" + "=" * 60)
    print("Frequency Domain Simulation (RA1)")
    print("=" * 60)
    
    # 神経パスデータ読み込み
    ra1_path = FiberPathData(
        points=load_csv_points(CONFIG_DIR / "points_YaxisOrientedLine_z3mm_withID.csv"),
        interval_mm=0.1,
    )
    
    # 刺激設定（周波数領域・電極ペアごと）
    ra1_stim_configs = [
        StimulationConfigFreq(
            pot_data=PotentialsData.from_frequency_csv(
                COMSOL_DIR / "epair1_para.csv"
            ),
            freq_hz=2000.0,
            amp_mA=0.001,
            phase_rad=0.0,
        ),
        StimulationConfigFreq(
            pot_data=PotentialsData.from_frequency_csv(
                COMSOL_DIR / "epair2_para.csv"
            ),
            freq_hz=2040.0,
            amp_mA=0.001,
            phase_rad=0.0,
        ),
    ]
    print(f"Frequency domain data loaded: {datetime.datetime.now()}")
    
    # シミュレーション実行（周波数領域）
    ra1_results, ra1_fibers = process_fiber_type_frequency(
        ra1_path, ra1_stim_configs, sim_config, t_ms,
    )

    save_results_all_1d(
        ra1_results, ra1_fibers,
        OUTPUT_DIR, sim_config.dt_ms, prefix="dirE"
    )
    save_results_summary(
        ra1_results, ra1_path, ra1_fibers,
        OUTPUT_DIR, prefix="dirE"
    )
    
    print(f"\nDone: {datetime.datetime.now()}")


if __name__ == "__main__":
    main()
"""
main_thio.py

Thio C-fiber（無髄神経）モデルのシミュレーション実行スクリプト
"""
import os
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Set, Tuple
import datetime

import numpy as np
import pandas as pd
from neuron import h

from thio_axon import ThioAxon
from comsol_data import PotentialsData, FiberPathData, load_csv_points
from potential_interp import (
    get_potential_timeseries_at_comsol_points,
    interpolate_to_axon_nodes,
    superpose_potentials,
)


# =============================================================================
# Configuration Dataclasses
# =============================================================================

@dataclass
class StimulationConfig:
    """刺激パラメータ（1電極ペア分）"""
    pot_data: PotentialsData
    freq_hz: Optional[float] = None  # 周波数領域の場合のみ
    amp_mA: float = 1.0
    phase_rad: float = 0.0


@dataclass
class SimulationConfig:
    """シミュレーション全体の設定"""
    dt_ms: float = 0.01
    tstop_ms: float = 100.0
    v_init_mV: float = -55.0  # Thioモデルの静止電位
    ap_threshold_mV: float = 0.0
    fiber_diameter_um: float = 1.0  # C-fiber typical diameter
    temperature: float = 37.0
    seg_density: float = 50/6
    particle_index: int = 1


# =============================================================================
# Core Simulation Function
# =============================================================================

def simulate_single_fiber(
    fiber: ThioAxon,
    V_extracellular: np.ndarray,
    config: SimulationConfig,
) -> Dict[str, Any]:
    """
    単一軸索のシミュレーション実行
    
    Parameters
    ----------
    fiber : ThioAxon
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
    
    # balance() 実行（Thioモデル固有）
    h.finitialize(h.v_init)
    h.balance()
    
    # 実行
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
# Batch Processing
# =============================================================================

def process_fiber_type(
    fiber_path: FiberPathData,
    stim_configs: List[StimulationConfig],
    sim_config: SimulationConfig,
    t_ms: np.ndarray,
    target_unit_ids: Optional[Set[int]] = None,
    verbose: bool = True,
) -> Tuple[Dict[int, Dict[str, Any]], Dict[int, ThioAxon]]:
    """
    1つの神経タイプ（ENF）の全線維をシミュレーション
    
    Returns
    -------
    results : Dict[unit_id, result_dict]
    fiber_models : Dict[unit_id, ThioAxon] - 3D座標変換用に保持
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
        fiber = ThioAxon(
            fiber_diameter=sim_config.fiber_diameter_um,
            length_um=length_um,
            temperature=sim_config.temperature,
            seg_density=sim_config.seg_density,
            particle_index=sim_config.particle_index,
        )
        fiber_models[unit_id] = fiber
        
        node_positions = fiber.get_node_positions_um()
        comsol_dx = fiber_path.get_cumulative_dx_um(unit_id)
        
        # 各電極ペアの電位を計算して重畳
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
            V_interp = interpolate_to_axon_nodes(V_comsol, comsol_dx, node_positions)
            V_components.append(V_interp)
        
        V_total = superpose_potentials(V_components)
        
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

# コンパートメントタイプの定数
TYPE_NODE = 0
TYPE_NAMES = {TYPE_NODE: 'node'}


def save_results_nodes_3d(
    results: Dict[int, Dict[str, Any]],
    fiber_path: FiberPathData,
    fiber_models: Dict[int, ThioAxon],
    output_dir: Path,
    dt_ms: float,
    prefix: str = "vm",
):
    """
    形式1: 全コンパートメント（Thioでは全てnode）を3D座標付きで保存
    
    出力ファイル:
    - {prefix}_nodes_3d.csv
      columns: unit_id, node_index, x, y, z, V_t0, V_t1, ...
      
    座標単位: mm（COMSOL座標系と同じ）
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    rows = []
    n_steps = None
    
    for unit_id, result in results.items():
        fiber = fiber_models[unit_id]
        node_positions_um = fiber.get_node_positions_um()
        v_membrane = result['v_membrane']  # (n_compartments, n_steps)
        
        if n_steps is None:
            n_steps = v_membrane.shape[1]
        
        # 1D→3D変換
        coords_3d_mm = fiber_path.interpolate_1d_to_3d(unit_id, node_positions_um)
        
        # Thioモデルは全てnode
        for comp_idx in range(fiber.n_compartments):
            row = [
                unit_id,
                comp_idx,
                coords_3d_mm[comp_idx, 0],
                coords_3d_mm[comp_idx, 1],
                coords_3d_mm[comp_idx, 2],
            ]
            row.extend(v_membrane[comp_idx, :].tolist())
            rows.append(row)
    
    # ヘッダー作成
    header = ['unit_id', 'node_index', 'x', 'y', 'z']
    header.extend([f'V_t{i}' for i in range(n_steps)])
    
    # 保存
    filepath = output_dir / f"{prefix}_nodes_3d.csv"
    _save_csv_with_header(filepath, header, rows)
    
    print(f"Saved: {filepath} ({len(rows)} rows)")


def save_results_all_1d(
    results: Dict[int, Dict[str, Any]],
    fiber_models: Dict[int, ThioAxon],
    output_dir: Path,
    dt_ms: float,
    prefix: str = "vm",
):
    """
    形式2: 全コンパートメントを1D座標で保存
    
    出力ファイル:
    - {prefix}_all_1d.csv
      columns: unit_id, x_um, type, V_t0, V_t1, ...
      
    x_um: 軸索始端からの距離 [um]
    type: node（Thioモデルは全てnode）
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    rows = []
    n_steps = None
    
    for unit_id, result in results.items():
        fiber = fiber_models[unit_id]
        node_positions_um = fiber.get_node_positions_um()
        v_membrane = result['v_membrane']  # (n_compartments, n_steps)
        
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
    
    # ヘッダー作成
    header = ['unit_id', 'x_um', 'type']
    header.extend([f'V_t{i}' for i in range(n_steps)])
    
    # 保存
    filepath = output_dir / f"{prefix}_all_1d.csv"
    _save_csv_mixed_types(filepath, header, rows)
    
    print(f"Saved: {filepath} ({len(rows)} rows)")


def save_results_summary(
    results: Dict[int, Dict[str, Any]],
    fiber_path: FiberPathData,
    fiber_models: Dict[int, ThioAxon],
    output_dir: Path,
    prefix: str = "vm",
):
    """
    サマリー情報を保存
    
    出力ファイル:
    - {prefix}_summary.csv
      columns: unit_id, n_nodes, n_compartments, fiber_length_um, ap_count, spike_times_ms
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    rows = []
    for unit_id, result in results.items():
        fiber = fiber_models[unit_id]
        
        rows.append({
            'unit_id': unit_id,
            'n_nodes': fiber.n_nodes,
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
    """数値データのCSV保存（高速）"""
    data = np.array(rows, dtype=np.float64)
    
    with open(filepath, 'w') as f:
        f.write(','.join(header) + '\n')
    with open(filepath, 'ab') as f:
        np.savetxt(f, data, delimiter=',', fmt='%.6g')


def _save_csv_mixed_types(filepath: Path, header: list, rows: list):
    """文字列を含むデータのCSV保存（pandas使用）"""
    df = pd.DataFrame(rows, columns=header)
    df.to_csv(filepath, index=False, float_format='%.6g')


# =============================================================================
# Main
# =============================================================================

def main():
    # =========================================================================
    # パス設定
    # =========================================================================
    PROJECT_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = PROJECT_DIR / "data"
    MODEL_DIR = DATA_DIR / "thio-model"
    CONFIG_DIR = DATA_DIR / "config"
    COMSOL_DIR = DATA_DIR / "comsol" / "electrode_square"
    OUTPUT_DIR = DATA_DIR / "output"
    
    # =========================================================================
    # NEURON初期化（Thioモデル固有）
    # =========================================================================
    os.chdir(MODEL_DIR)
    h.nrn_load_dll(str(MODEL_DIR / "nrnmech.dll"))
    h.load_file("nrngui.hoc")
    h.xopen("cFiberBuilder.hoc")
    h.load_file("balance.hoc")
    
    # =========================================================================
    # シミュレーション設定
    # =========================================================================
    sim_config = SimulationConfig(
        dt_ms=0.01,
        tstop_ms=100.0,
        v_init_mV=-55.0,  # Thioモデルの静止電位
        ap_threshold_mV=0.0,
        fiber_diameter_um=1.0,  # C-fiber typical diameter
        temperature=37.0,
        seg_density=50/6,
        particle_index=1,
    )
    
    t_ms = np.arange(0.0, sim_config.tstop_ms + sim_config.dt_ms, sim_config.dt_ms)

    # デバッグ用：対象unit_id（Noneで全部）
    # ENF (C-fiber) のunit_idを指定
    target_unit_ids = {555, 582, 645, 684}
    # target_unit_ids = {550, 555, 582, 597, 598, 616, 617, 623, 645, 655, 682, 683, 684}
    # target_unit_ids = None  # 全unit_idを処理

    print(f"Start: {datetime.datetime.now()}")
    
    # =========================================================================
    # ENF (C-fiber) 処理
    # =========================================================================
    print("\n===== Processing ENF (C-fiber) =====")
    
    # データ読み込み
    # ※ ENF用のファイル名に変更が必要な場合は適宜修正
    enf_path = FiberPathData(
        points=load_csv_points(CONFIG_DIR / "points_along_enf_fibers.csv"),
        interval_mm=0.1,
    )
    
    # 刺激設定（電極ペアごと）
    enf_stim_configs = [
        StimulationConfig(
            pot_data=PotentialsData.from_frequency_csv(
                COMSOL_DIR / "potentials_along_enf_fiber_electrodes_1.csv"
            ),
            freq_hz=8000.0,
            amp_mA=0.03,
            phase_rad=0.0,
        ),
        StimulationConfig(
            pot_data=PotentialsData.from_frequency_csv(
                COMSOL_DIR / "potentials_along_enf_fiber_electrodes_2.csv"
            ),
            freq_hz=8040.0,
            amp_mA=0.03,
            phase_rad=0.0,
        ),
    ]
    print(f"Data loaded: {datetime.datetime.now()}")
    
    # シミュレーション実行
    enf_results, enf_fibers = process_fiber_type(
        enf_path, enf_stim_configs, sim_config, t_ms,
        target_unit_ids=target_unit_ids,
    )

    # =========================================================================
    # 結果保存
    # =========================================================================
    
    # 形式1: ノードのみ + 3D座標
    save_results_nodes_3d(
        enf_results, enf_path, enf_fibers,
        OUTPUT_DIR, sim_config.dt_ms, prefix="enf"
    )

    # 形式2: 全コンパートメント + 1D座標
    save_results_all_1d(
        enf_results, enf_fibers,
        OUTPUT_DIR, sim_config.dt_ms, prefix="enf"
    )

    # サマリー
    save_results_summary(
        enf_results, enf_path, enf_fibers,
        OUTPUT_DIR, prefix="enf"
    )
    
    print(f"\nDone: {datetime.datetime.now()}")


if __name__ == "__main__":
    main()
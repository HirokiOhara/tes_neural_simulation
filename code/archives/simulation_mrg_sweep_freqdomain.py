import os
import warnings
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Set
import datetime

import numpy as np
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
# スイープパラメータ
# =============================================================================
# FREQ1_LIST = [1000, 2000, 4000, 8000]  # Hz
# FREQ2_OFFSETS = [0, 10, 20, 40, 80]     # Hz
FREQ1_LIST = [2000, 8000]  # Hz
FREQ2_OFFSETS = [0, 40]     # Hz
# FREQ1_LIST = [8000]  # Hz
# FREQ2_OFFSETS = [0, 10, 20, 40, 80]     # Hz
AMPLITUDE_RATIOS = [
    (1.00, 0.00),
    (0.75, 0.25),
    (0.5, 0.5),
    (0.00, 0.75),
    (0.00, 1.00)
]
TOTAL_CURRENT_MA = 0.1  # mA


# =============================================================================
# Configuration Dataclass
# =============================================================================
@dataclass
class SweepCondition:
    """1つのスイープ条件"""
    freq1_hz: float
    freq2_hz: float
    amp1_mA: float
    amp2_mA: float
    ratio_str: str  # "75:25" など

    @property
    def condition_name(self) -> str:
        return f"f1-{int(self.freq1_hz)}_f2-{int(self.freq2_hz)}_ratio-{self.ratio_str.replace(':', '_')}"


# =============================================================================
# スイープ条件生成
# =============================================================================
def generate_sweep_conditions() -> List[SweepCondition]:
    """全スイープ条件を生成"""
    conditions = []
    
    for freq1 in FREQ1_LIST:
        for offset in FREQ2_OFFSETS:
            freq2 = freq1 + offset
            for ratio1, ratio2 in AMPLITUDE_RATIOS:
                amp1 = TOTAL_CURRENT_MA * ratio1
                amp2 = TOTAL_CURRENT_MA * ratio2
                ratio_str = f"{int(ratio1*100)}_{int(ratio2*100)}"
                
                conditions.append(SweepCondition(
                    freq1_hz=float(freq1),
                    freq2_hz=float(freq2),
                    amp1_mA=amp1,
                    amp2_mA=amp2,
                    ratio_str=ratio_str,
                ))
    
    return conditions


def filter_valid_conditions(
    conditions: List[SweepCondition],
    pot_data_elec1: MultiFreqPotentialsData,
    pot_data_elec2: MultiFreqPotentialsData,
) -> List[SweepCondition]:
    """
    COMSOLデータに存在する周波数のみの条件をフィルタリング
    存在しない周波数の条件はワーニングを出してスキップ
    """
    # frequencies属性を使用
    available_freqs_1 = set(pot_data_elec1.frequencies)
    available_freqs_2 = set(pot_data_elec2.frequencies)
    
    valid_conditions = []
    skipped_conditions = []
    
    for cond in conditions:
        freq1_ok = cond.freq1_hz in available_freqs_1
        freq2_ok = cond.freq2_hz in available_freqs_2
        
        if freq1_ok and freq2_ok:
            valid_conditions.append(cond)
        else:
            missing = []
            if not freq1_ok:
                missing.append(f"freq1={cond.freq1_hz}Hz (elec1)")
            if not freq2_ok:
                missing.append(f"freq2={cond.freq2_hz}Hz (elec2)")
            skipped_conditions.append((cond, missing))
    
    # スキップした条件をワーニング出力
    if skipped_conditions:
        warnings.warn(
            f"\n{len(skipped_conditions)} conditions skipped due to missing frequencies in COMSOL data:"
        )
        for cond, missing in skipped_conditions:
            print(f"  SKIP: {cond.condition_name} - missing: {', '.join(missing)}")
    
    return valid_conditions


# =============================================================================
# MAT保存関数
# =============================================================================
def save_unit_result_mat(
    output_dir: Path,
    fiber_type: str,
    condition: SweepCondition,
    unit_id: int,
    fiber: MRGaxon,
    fiber_path: FiberPathData,
    result: dict,
    t_ms: np.ndarray,
):
    """
    1 unit の結果を .mat ファイルで保存
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1D座標 (um)
    x_um = fiber.get_node_positions_um()
    
    # 3D座標 (mm)
    coords_3d_mm = fiber_path.interpolate_1d_to_3d(unit_id, x_um)
    
    # コンパートメントタイプ
    comp_types = []
    for comp_idx in range(fiber.n_compartments):
        comp_type, _ = fiber.get_compartment_info(comp_idx)
        comp_types.append(comp_type)
    
    # MATLABで扱いやすい形式
    mat_data = {
        # メタ情報
        'unit_id': np.array([unit_id]),
        'fiber_type': fiber_type,
        'freq1_hz': np.array([condition.freq1_hz]),
        'freq2_hz': np.array([condition.freq2_hz]),
        'amp1_mA': np.array([condition.amp1_mA]),
        'amp2_mA': np.array([condition.amp2_mA]),
        'ratio_str': condition.ratio_str,
        
        # 時間軸
        't_ms': t_ms.astype(np.float64),
        
        # 座標
        'x_um': x_um.astype(np.float64),
        'coords_3d_mm': coords_3d_mm.astype(np.float64),
        
        # コンパートメント情報
        'compartment_types': np.array(comp_types, dtype=np.int32),
        'n_compartments': np.array([fiber.n_compartments]),
        'n_nodes': np.array([len(fiber.nodes)]),
        
        # 膜電位 (n_compartments x n_steps)
        'v_membrane_mV': result['v_membrane'].astype(np.float64),
        
        # AP情報
        'ap_count': np.array([result['ap_count']]),
        'spike_times_ms': result['spike_times_ms'].astype(np.float64),
    }
    
    filename = f"{fiber_type}_unit{unit_id:04d}_{condition.condition_name}.mat"
    filepath = output_dir / filename
    
    savemat(filepath, mat_data, do_compression=True)


# =============================================================================
# サマリー保存関数
# =============================================================================
def save_sweep_summary(
    summary_data: List[dict],
    output_dir: Path,
    fiber_type: str,
):
    """全条件のサマリーをCSVで保存"""
    import pandas as pd
    
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{fiber_type}_sweep_summary.csv"
    
    df = pd.DataFrame(summary_data)
    df.to_csv(filepath, index=False)
    
    print(f"Saved summary: {filepath} ({len(summary_data)} rows)")


# =============================================================================
# メイン処理関数
# =============================================================================
def run_sweep(
    fiber_type: str,
    fiber_path: FiberPathData,
    pot_data_elec1: MultiFreqPotentialsData,
    pot_data_elec2: MultiFreqPotentialsData,
    sim_config: SimulationConfig,
    t_ms: np.ndarray,
    output_dir: Path,
    conditions: List[SweepCondition],
    target_unit_ids: Optional[Set[int]] = None,
    verbose: bool = True,
):
    """
    パラメトリックスイープ実行
    逐次保存方式：各unitの結果を即座に.matで保存し、メモリを解放
    """
    fiber_lengths = fiber_path.get_all_fiber_lengths_um()
    total_conditions = len(conditions)
    summary_data = []
    
    # 対象unit_idのリスト
    if target_unit_ids is not None:
        unit_ids = sorted(target_unit_ids & set(fiber_lengths.keys()))
    else:
        unit_ids = sorted(fiber_lengths.keys())
    
    total_units = len(unit_ids)
    total_simulations = total_conditions * total_units
    sim_count = 0
    
    print(f"\n{'='*60}")
    print(f"Starting sweep: {fiber_type}")
    print(f"  Conditions: {total_conditions}")
    print(f"  Units: {total_units}")
    print(f"  Total simulations: {total_simulations}")
    print(f"{'='*60}\n")
    
    for cond_idx, condition in enumerate(conditions):
        if verbose:
            print(f"\n[Condition {cond_idx+1}/{total_conditions}] {condition.condition_name}")
        
        # この条件用の電位データを取得
        pot1 = pot_data_elec1.to_potentials_data(condition.freq1_hz)
        pot2 = pot_data_elec2.to_potentials_data(condition.freq2_hz)
        
        # 条件ごとの出力ディレクトリ
        cond_output_dir = output_dir / fiber_type / condition.condition_name
        
        for unit_idx, unit_id in enumerate(unit_ids):
            sim_count += 1
            length_um = fiber_lengths[unit_id]
            
            if verbose:
                print(f"  [{sim_count}/{total_simulations}] unit_id={unit_id}, length={length_um:.1f} um", end="")
            
            # 軸索モデル作成
            fiber = MRGaxon(sim_config.fiber_diameter_um, length_um=length_um)
            
            node_positions = fiber.get_node_positions_um()
            comsol_dx = fiber_path.get_cumulative_dx_um(unit_id)
            
            # 電極1の電位
            V_comsol_1 = get_potential_timeseries_at_comsol_points(
                pot1, fiber_path, unit_id, t_ms,
                freq_hz=condition.freq1_hz,
                amp_mA=condition.amp1_mA,
                phase_rad=0.0,
            )
            V_interp_1 = interpolate_to_axon_nodes(V_comsol_1, comsol_dx, node_positions)
            
            # 電極2の電位
            V_comsol_2 = get_potential_timeseries_at_comsol_points(
                pot2, fiber_path, unit_id, t_ms,
                freq_hz=condition.freq2_hz,
                amp_mA=condition.amp2_mA,
                phase_rad=0.0,
            )
            V_interp_2 = interpolate_to_axon_nodes(V_comsol_2, comsol_dx, node_positions)
            
            # 重畳
            V_total = superpose_potentials([V_interp_1, V_interp_2])
            
            # シミュレーション実行
            result = simulate_single_fiber(fiber, V_total, sim_config)
            
            if verbose:
                print(f" -> AP={result['ap_count']}")
            
            # # 即座に保存
            save_unit_result_mat(
                cond_output_dir,
                fiber_type,
                condition,
                unit_id,
                fiber,
                fiber_path,
                result,
                t_ms,
            )
            
            # サマリーデータ追加
            summary_data.append({
                'unit_id': unit_id,
                'fiber_type': fiber_type,
                'freq1_hz': condition.freq1_hz,
                'freq2_hz': condition.freq2_hz,
                'amp1_mA': condition.amp1_mA,
                'amp2_mA': condition.amp2_mA,
                'ratio': condition.ratio_str,
                'ap_count': result['ap_count'],
                'spike_times_ms': str(result['spike_times_ms'].tolist()),
            })
            
            # メモリ解放
            del fiber
            del result
            del V_total
            del V_interp_1
            del V_interp_2
            h('forall delete_section()')
    
    # サマリー保存
    save_sweep_summary(summary_data, output_dir, fiber_type)
    
    print(f"\n{'='*60}")
    print(f"Sweep completed: {fiber_type}")
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
    COMSOL_DIR = DATA_DIR / "comsol" / "electrode_ring"
    OUTPUT_DIR = DATA_DIR / "output" / "sweep_mrg"
    
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
        tstop_ms=50.0,
        v_init_mV=-80.0,
        ap_threshold_mV=0.0,
        fiber_diameter_um=8.7,
    )
    
    t_ms = np.arange(0.0, sim_config.tstop_ms + sim_config.dt_ms, sim_config.dt_ms)
    
    # =========================================================================
    # デバッグ用：対象unit_id
    # =========================================================================
    target_unit_ids = {7}  # 少数でテスト
    # target_unit_ids = {7, 12, 15, 20, 23, 32, 39, 40, 49, 54, 61, 63, 64, 68, 70, 74, 76, 78, 81, 82, 103, 105, 107, 112, 114, 115, 121, 125, 126, 127, 129, 159, 189, 190, 191, 195, 214, 218, 226, 227, 233, 243, 246, 248, 249, 250, 257, 259, 261, 262, 274, 279, 289, 300, 303, 304, 310, 314, 327, 341, 346, 352, 361, 369, 377, 380, 389, 392, 401, 404, 412, 423, 425, 442, 443, 448, 451, 457, 466, 469, 472, 474, 477, 482, 493, 500, 505, 506, 521, 522, 524, 534, 536} #  --x_min -5 --x_max 1 --y_min -27.3 --y_max -21.3
    # target_unit_ids = {7, 20, 23, 32, 39, 40, 49, 54, 61, 63, 64, 68, 70, 74, 76, 78, 81, 82, 103, 105, 107, 112, 114, 115, 121, 125, 126, 127, 129, 159, 166, 182, 190, 191, 195, 214, 218, 226, 227, 233, 243, 248, 249, 257, 259, 261, 262, 265, 274, 279, 289, 300, 303, 304, 310, 314, 321, 327, 341, 346, 352, 356, 361, 369, 377, 380, 389, 392, 401, 404, 412, 423, 425, 442, 443, 448, 451, 457, 466, 469, 474, 477, 482, 500, 506, 520, 521, 522, 534, 536}
    # target_unit_ids = None  # 全unit_id
    
    print(f"\nStart: {datetime.datetime.now()}")
    
    # =========================================================================
    # RA1 処理
    # =========================================================================
    print("\n===== Processing RA1 =====")
    
    # データ読み込み
    ra1_path = FiberPathData(
        points=load_csv_points(CONFIG_DIR / "points_along_ra1_fibers.csv"),
        interval_mm=0.1,
    )
    
    # 複数周波数対応の電位データ読み込み
    ra1_pot_elec1 = MultiFreqPotentialsData.from_multi_frequency_csv(
        COMSOL_DIR / "potentials_along_ra1_fiber_electrodes_1.csv"
    )
    ra1_pot_elec2 = MultiFreqPotentialsData.from_multi_frequency_csv(
        COMSOL_DIR / "potentials_along_ra1_fiber_electrodes_2.csv"
    )
    
    print(f"Data loaded: {datetime.datetime.now()}")
    print(f"  Available frequencies (elec1): {sorted(ra1_pot_elec1.frequencies)}")
    print(f"  Available frequencies (elec2): {sorted(ra1_pot_elec2.frequencies)}")
    
    # =========================================================================
    # スイープ条件生成 & フィルタリング
    # =========================================================================
    all_conditions = generate_sweep_conditions()
    print(f"\nGenerated {len(all_conditions)} sweep conditions")
    
    # COMSOLデータに存在する周波数のみをフィルタリング
    valid_conditions = filter_valid_conditions(
        all_conditions, ra1_pot_elec1, ra1_pot_elec2
    )
    print(f"Valid conditions (with available frequencies): {len(valid_conditions)}")
    
    if not valid_conditions:
        print("ERROR: No valid conditions. Check COMSOL data frequencies.")
        return

    # =========================================================================
    # スイープ実行
    # =========================================================================
    ra1_summary = run_sweep(
        fiber_type="ra1",
        fiber_path=ra1_path,
        pot_data_elec1=ra1_pot_elec1,
        pot_data_elec2=ra1_pot_elec2,
        sim_config=sim_config,
        t_ms=t_ms,
        output_dir=OUTPUT_DIR,
        conditions=valid_conditions,
        target_unit_ids=target_unit_ids,
        verbose=True,
    )

    print(f"\nDone: {datetime.datetime.now()}")

    # =========================================================================
    # RA2 処理
    # =========================================================================
    print("\n===== Processing RA2 =====")
    
    # データ読み込み
    ra2_path = FiberPathData(
        points=load_csv_points(CONFIG_DIR / "points_along_ra2_fibers.csv"),
        interval_mm=0.1,
    )
    
    # 複数周波数対応の電位データ読み込み
    ra2_pot_elec1 = MultiFreqPotentialsData.from_multi_frequency_csv(
        COMSOL_DIR / "potentials_along_ra2_fiber_electrodes_1.csv"
    )
    ra2_pot_elec2 = MultiFreqPotentialsData.from_multi_frequency_csv(
        COMSOL_DIR / "potentials_along_ra2_fiber_electrodes_2.csv"
    )
    
    print(f"Data loaded: {datetime.datetime.now()}")
    print(f"  Available frequencies (elec1): {sorted(ra2_pot_elec1.frequencies)}")
    print(f"  Available frequencies (elec2): {sorted(ra2_pot_elec2.frequencies)}")
    
    # =========================================================================
    # スイープ条件生成 & フィルタリング
    # =========================================================================
    all_conditions = generate_sweep_conditions()
    print(f"\nGenerated {len(all_conditions)} sweep conditions")
    
    # COMSOLデータに存在する周波数のみをフィルタリング
    valid_conditions = filter_valid_conditions(
        all_conditions, ra2_pot_elec1, ra2_pot_elec2
    )
    print(f"Valid conditions (with available frequencies): {len(valid_conditions)}")
    
    if not valid_conditions:
        print("ERROR: No valid conditions. Check COMSOL data frequencies.")
        return

    print(f"\nDone: {datetime.datetime.now()}")


    # =========================================================================
    # スイープ実行
    # =========================================================================
    ra2_summary = run_sweep(
        fiber_type="ra2",
        fiber_path=ra2_path,
        pot_data_elec1=ra2_pot_elec1,
        pot_data_elec2=ra2_pot_elec2,
        sim_config=sim_config,
        t_ms=t_ms,
        output_dir=OUTPUT_DIR,
        conditions=valid_conditions,
        target_unit_ids=target_unit_ids,
        verbose=True,
    )

    # =========================================================================
    # SA1 処理
    # =========================================================================
    print("\n===== Processing SA1 =====")
    
    # データ読み込み
    sa1_path = FiberPathData(
        points=load_csv_points(CONFIG_DIR / "points_along_sa1_fibers.csv"),
        interval_mm=0.1,
    )
    
    # 複数周波数対応の電位データ読み込み
    sa1_pot_elec1 = MultiFreqPotentialsData.from_multi_frequency_csv(
        COMSOL_DIR / "potentials_along_sa1_fiber_electrodes_1.csv"
    )
    sa1_pot_elec2 = MultiFreqPotentialsData.from_multi_frequency_csv(
        COMSOL_DIR / "potentials_along_sa1_fiber_electrodes_2.csv"
    )
    
    print(f"Data loaded: {datetime.datetime.now()}")
    print(f"  Available frequencies (elec1): {sorted(sa1_pot_elec1.frequencies)}")
    print(f"  Available frequencies (elec2): {sorted(sa1_pot_elec2.frequencies)}")
    
    # =========================================================================
    # スイープ条件生成 & フィルタリング
    # =========================================================================
    all_conditions = generate_sweep_conditions()
    print(f"\nGenerated {len(all_conditions)} sweep conditions")
    
    # COMSOLデータに存在する周波数のみをフィルタリング
    valid_conditions = filter_valid_conditions(
        all_conditions, sa1_pot_elec1, sa1_pot_elec2
    )
    print(f"Valid conditions (with available frequencies): {len(valid_conditions)}")
    
    if not valid_conditions:
        print("ERROR: No valid conditions. Check COMSOL data frequencies.")
        return

    print(f"\nDone: {datetime.datetime.now()}")


    # =========================================================================
    # スイープ実行
    # =========================================================================
    sa1_summary = run_sweep(
        fiber_type="sa1",
        fiber_path=sa1_path,
        pot_data_elec1=sa1_pot_elec1,
        pot_data_elec2=sa1_pot_elec2,
        sim_config=sim_config,
        t_ms=t_ms,
        output_dir=OUTPUT_DIR,
        conditions=valid_conditions,
        target_unit_ids=target_unit_ids,
        verbose=True,
    )

    # =========================================================================
    # 結果サマリー表示
    # =========================================================================
    import pandas as pd
    df_ra1 = pd.DataFrame(ra1_summary)
    df_ra2 = pd.DataFrame(ra2_summary)
    df_sa1 = pd.DataFrame(sa1_summary)
    
    print("\n===== AP Count Summary by Condition =====")
    summary_ra1 = df_ra1.groupby(['freq1_hz', 'freq2_hz', 'ratio']).agg({
        'ap_count': ['sum', 'mean', 'max'],
        'unit_id': 'count'
    }).round(2)
    summary_ra2 = df_ra2.groupby(['freq1_hz', 'freq2_hz', 'ratio']).agg({
        'ap_count': ['sum', 'mean', 'max'],
        'unit_id': 'count'
    }).round(2)
    summary_ra3 = df_sa1.groupby(['freq1_hz', 'freq2_hz', 'ratio']).agg({
        'ap_count': ['sum', 'mean', 'max'],
        'unit_id': 'count'
    }).round(2)


if __name__ == "__main__":
    main()
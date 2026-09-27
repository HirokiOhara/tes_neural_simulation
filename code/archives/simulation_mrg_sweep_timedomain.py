"""
MRG軸索モデルのシミュレーション - 時間領域スイープ実行スクリプト

COMSOLの過渡解析データ（パルス波）を用いたシミュレーション
ファイル形式: potentials_along_{fiber_type}_fiber_AmpRatio_{ratio_id}.csv
  - fiber_type: RA1, RA2, SA1
  - ratio_id: 1=100to0, 2=75to25, 3=50to50, 4=25to75, 5=0to100
"""
import os
import warnings
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional, Set
import datetime

import numpy as np
import pandas as pd
from scipy.io import savemat
from neuron import h

from mrg_axon import MRGaxon
from comsol_data import (
    PotentialsData,
    FiberPathData,
    load_csv_points,
    coord_key,
)
from potential_interp import interpolate_to_axon_nodes
from simulation_mrg import (
    SimulationConfig,
    simulate_single_fiber,
)


# =============================================================================
# スイープパラメータ
# =============================================================================
# 神経タイプ
FIBER_TYPES = ["ra1", "ra2", "sa1"]

# AmpRatio設定
AMP_RATIO_CONFIG = {
    1: {"label": "100to0", "ratio1": 1.00, "ratio2": 0.00},
    2: {"label": "75to25", "ratio1": 0.75, "ratio2": 0.25},
    3: {"label": "50to50", "ratio1": 0.50, "ratio2": 0.50},
    4: {"label": "25to75", "ratio1": 0.25, "ratio2": 0.75},
    5: {"label": "0to100", "ratio1": 0.00, "ratio2": 1.00},
}

# デフォルトスケーリング係数
DEFAULT_AMP_SCALE = 1.0

# COMSOLでの電極電流 (各電極ペアから1mA)
COMSOL_CURRENT_PER_ELECTRODE_MA = 1.0


# =============================================================================
# Configuration Dataclass
# =============================================================================
@dataclass
class TimeDomainSweepCondition:
    """時間領域の1つのスイープ条件"""
    fiber_type: str
    amp_ratio_id: int
    amp_ratio_label: str
    ratio1: float
    ratio2: float
    amp_scale: float
    pulse_freq_hz: float  # ユーザー指定のパルス周波数（サマリー用）
    
    @property
    def condition_name(self) -> str:
        return f"{self.fiber_type}_AmpRatio_{self.amp_ratio_id}"
    
    @property
    def csv_filename(self) -> str:
        return f"potentials_along_{self.fiber_type}_fiber_AmpRatio_{self.amp_ratio_id}.csv"


# =============================================================================
# スイープ条件生成
# =============================================================================
def generate_time_domain_conditions(
    fiber_types: List[str] = None,
    amp_ratio_ids: List[int] = None,
    amp_scale: float = DEFAULT_AMP_SCALE,
    pulse_freq_hz: float = np.nan,
) -> List[TimeDomainSweepCondition]:
    """
    時間領域のスイープ条件を生成
    
    Parameters
    ----------
    fiber_types : List[str], optional
        対象の神経タイプ。Noneの場合は全タイプ
    amp_ratio_ids : List[int], optional
        対象のAmpRatio ID (1-5)。Noneの場合は全て
    amp_scale : float
        振幅スケーリング係数
    pulse_freq_hz : float
        パルス周波数 [Hz]（サマリー出力用）
    
    Returns
    -------
    List[TimeDomainSweepCondition]
    """
    if fiber_types is None:
        fiber_types = FIBER_TYPES
    if amp_ratio_ids is None:
        amp_ratio_ids = list(AMP_RATIO_CONFIG.keys())
    
    conditions = []
    
    for fiber_type in fiber_types:
        for ratio_id in amp_ratio_ids:
            config = AMP_RATIO_CONFIG[ratio_id]
            conditions.append(TimeDomainSweepCondition(
                fiber_type=fiber_type.lower(),
                amp_ratio_id=ratio_id,
                amp_ratio_label=config["label"],
                ratio1=config["ratio1"],
                ratio2=config["ratio2"],
                amp_scale=amp_scale,
                pulse_freq_hz=pulse_freq_hz,
            ))
    
    return conditions


# =============================================================================
# 電位データ準備
# =============================================================================
def prepare_potential_time_domain(
    fiber_path: FiberPathData,
    unit_id: int,
    pot_data: PotentialsData,
    t_ms_sim: np.ndarray,
    amp_scale: float,
    node_positions_um: np.ndarray,
) -> np.ndarray:
    """
    時間領域: COMSOLデータから電位を取得
    
    COMSOLデータがシミュレーション時間より短い場合は最終値で延長
    
    Parameters
    ----------
    fiber_path : FiberPathData
        神経パスデータ
    unit_id : int
        対象unit_id
    pot_data : PotentialsData
        時間領域の電位データ
    t_ms_sim : np.ndarray
        シミュレーション時間ベクトル [ms]
    amp_scale : float
        振幅スケーリング係数
    node_positions_um : np.ndarray
        軸索ノード位置 [um]
    
    Returns
    -------
    V_interp : (n_nodes, n_steps) 膜外電位 [mV]
    """
    comsol_dx = fiber_path.get_cumulative_dx_um(unit_id)
    
    # COMSOL点の3D座標を取得
    xyz_comsol = fiber_path.get_xyz_coords(unit_id)
    n_comsol_points = xyz_comsol.shape[0]
    
    # COMSOLデータの時間・電位を取得
    t_comsol = pot_data.t_ms  # (T_comsol,)
    V_comsol_raw = pot_data.V_timeseries_mV  # (N_total, T_comsol)
    
    # このunit_idに対応するCOMSOL点のインデックスを特定
    indices = []
    for i in range(n_comsol_points):
        key = coord_key(xyz_comsol[i], decimals=6)
        if key in pot_data.coord_to_index:
            indices.append(pot_data.coord_to_index[key])
        else:
            raise ValueError(f"Coordinate {xyz_comsol[i]} not found in potential data")
    
    # このunitの電位を抽出 (n_comsol_points, T_comsol)
    V_comsol_unit = V_comsol_raw[indices, :]
    
    # 振幅スケーリング
    V_comsol_unit = V_comsol_unit * amp_scale
    
    # シミュレーション時間に合わせて拡張/切り詰め
    n_steps_sim = len(t_ms_sim)
    n_steps_comsol = len(t_comsol)
    
    if n_steps_comsol >= n_steps_sim:
        # COMSOLデータが十分長い場合は切り詰め
        V_comsol_extended = V_comsol_unit[:, :n_steps_sim]
    else:
        # COMSOLデータが短い場合は最終値で延長
        V_comsol_extended = np.zeros((n_comsol_points, n_steps_sim), dtype=np.float64)
        V_comsol_extended[:, :n_steps_comsol] = V_comsol_unit
        V_comsol_extended[:, n_steps_comsol:] = V_comsol_unit[:, -1:].repeat(
            n_steps_sim - n_steps_comsol, axis=1
        )
    
    # 軸索ノードに補間
    V_interp = interpolate_to_axon_nodes(V_comsol_extended, comsol_dx, node_positions_um)
    
    return V_interp


# =============================================================================
# MAT保存関数
# =============================================================================
def save_unit_result_mat(
    output_dir: Path,
    condition: TimeDomainSweepCondition,
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
        'fiber_type': condition.fiber_type,
        'amp_ratio_id': np.array([condition.amp_ratio_id]),
        'amp_ratio_label': condition.amp_ratio_label,
        'amp_scale': np.array([condition.amp_scale]),
        'pulse_freq_hz': np.array([condition.pulse_freq_hz]),
        
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
    
    filename = f"{condition.fiber_type}_unit{unit_id:04d}_AmpRatio_{condition.amp_ratio_id}.mat"
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
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{fiber_type}_sweep_summary.csv"
    
    df = pd.DataFrame(summary_data)
    df.to_csv(filepath, index=False)
    
    print(f"Saved summary: {filepath} ({len(summary_data)} rows)")


# =============================================================================
# メイン処理関数
# =============================================================================
def run_time_domain_sweep(
    fiber_type: str,
    fiber_path: FiberPathData,
    comsol_dir: Path,
    sim_config: SimulationConfig,
    t_ms: np.ndarray,
    output_dir: Path,
    conditions: List[TimeDomainSweepCondition],
    target_unit_ids: Optional[Set[int]] = None,
    verbose: bool = True,
) -> List[dict]:
    """
    時間領域パラメトリックスイープ実行
    
    Parameters
    ----------
    fiber_type : str
        神経タイプ (ra1, ra2, sa1)
    fiber_path : FiberPathData
        神経パスデータ
    comsol_dir : Path
        COMSOLデータのディレクトリ
    sim_config : SimulationConfig
        シミュレーション設定
    t_ms : np.ndarray
        シミュレーション時間ベクトル
    output_dir : Path
        出力ディレクトリ
    conditions : List[TimeDomainSweepCondition]
        スイープ条件リスト（このfiber_typeのみ）
    target_unit_ids : Optional[Set[int]]
        対象unit_id（Noneで全て）
    verbose : bool
        詳細出力
    
    Returns
    -------
    summary_data : List[dict]
        サマリーデータ
    """
    fiber_lengths = fiber_path.get_all_fiber_lengths_um()
    summary_data = []
    
    # 対象unit_idのリスト
    if target_unit_ids is not None:
        unit_ids = sorted(target_unit_ids & set(fiber_lengths.keys()))
    else:
        unit_ids = sorted(fiber_lengths.keys())
    
    # このfiber_typeの条件のみフィルタ
    conditions_for_type = [c for c in conditions if c.fiber_type == fiber_type]
    
    total_conditions = len(conditions_for_type)
    total_units = len(unit_ids)
    total_simulations = total_conditions * total_units
    sim_count = 0
    
    print(f"\n{'='*60}")
    print(f"Starting time domain sweep: {fiber_type}")
    print(f"  Conditions: {total_conditions}")
    print(f"  Units: {total_units}")
    print(f"  Total simulations: {total_simulations}")
    print(f"{'='*60}\n")
    
    for cond_idx, condition in enumerate(conditions_for_type):
        if verbose:
            print(f"\n[Condition {cond_idx+1}/{total_conditions}] {condition.condition_name}")
        
        # 電位データ読み込み
        csv_path = comsol_dir / condition.csv_filename
        if not csv_path.exists():
            warnings.warn(f"File not found: {csv_path}, skipping...")
            continue
        
        pot_data = PotentialsData.from_time_csv(
            csv_path,
            dt_ms=sim_config.dt_ms,
        )
        
        if verbose:
            print(f"  Loaded: {csv_path.name}")
            print(f"  COMSOL time range: [0, {pot_data.t_ms[-1]:.3f}] ms ({len(pot_data.t_ms)} steps)")
        
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
            
            # 電位計算（時間領域）
            V_total = prepare_potential_time_domain(
                fiber_path,
                unit_id,
                pot_data,
                t_ms,
                condition.amp_scale,
                node_positions,
            )
            
            # シミュレーション実行
            result = simulate_single_fiber(fiber, V_total, sim_config)
            
            if verbose:
                print(f" -> AP={result['ap_count']}")
            
            # # 即座に保存（必要に応じてコメント解除）
            # save_unit_result_mat(
            #     cond_output_dir,
            #     condition,
            #     unit_id,
            #     fiber,
            #     fiber_path,
            #     result,
            #     t_ms,
            # )
            
            # サマリーデータ追加（周波数領域と共通フォーマット）
            # amp1_mA = amp_scale (COMSOLでは合計1mA)
            amp_total_mA = condition.amp_scale * COMSOL_CURRENT_PER_ELECTRODE_MA
            
            summary_data.append({
                'unit_id': unit_id,
                'fiber_type': fiber_type,
                'freq1_hz': condition.pulse_freq_hz,  # ユーザー指定のパルス周波数
                'freq2_hz': np.nan,  # 時間領域では不使用
                'amp1_mA': amp_total_mA,
                'amp2_mA': np.nan,  # 時間領域では不使用
                'ratio': condition.amp_ratio_label,
                'ap_count': result['ap_count'],
                'spike_times_ms': str(result['spike_times_ms'].tolist()),
            })
            
            # メモリ解放
            del fiber
            del result
            del V_total
            h('forall delete_section()')
        
        # 電位データのメモリ解放
        del pot_data
    
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
    COMSOL_DIR = DATA_DIR / "comsol" / "waveform_pulse"
    OUTPUT_DIR = DATA_DIR / "output" / "sweep_mrg_timedomain"
    
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
        tstop_ms=20.0,
        v_init_mV=-80.0,
        ap_threshold_mV=0.0,
        fiber_diameter_um=8.7,
    )
    
    t_ms = np.arange(0.0, sim_config.tstop_ms + sim_config.dt_ms, sim_config.dt_ms)
    
    # =========================================================================
    # ユーザー設定パラメータ
    # =========================================================================
    # パルス周波数（サマリー出力用）
    pulse_freq_hz = 10.0  # ユーザーが指定
    
    # 振幅スケーリング係数
    amp_scale = 0.06
    
    # =========================================================================
    # デバッグ用：対象unit_id
    # =========================================================================
    # target_unit_ids = {7, 20, 78}  # 少数でテスト
    target_unit_ids = {7, 12, 15, 20, 23, 32, 39, 40, 49, 54, 61, 63, 64, 68, 70, 74, 76, 78, 81, 82, 103, 105, 107, 112, 114, 115, 121, 125, 126, 127, 129, 159, 189, 190, 191, 195, 214, 218, 226, 227, 233, 243, 246, 248, 249, 250, 257, 259, 261, 262, 274, 279, 289, 300, 303, 304, 310, 314, 327, 341, 346, 352, 361, 369, 377, 380, 389, 392, 401, 404, 412, 423, 425, 442, 443, 448, 451, 457, 466, 469, 472, 474, 477, 482, 493, 500, 505, 506, 521, 522, 524, 534, 536}
    # target_unit_ids = None  # 全unit_id
    
    print(f"\nStart: {datetime.datetime.now()}")
    
    # =========================================================================
    # スイープ条件生成
    # =========================================================================
    all_conditions = generate_time_domain_conditions(
        fiber_types=FIBER_TYPES,
        amp_ratio_ids=[1, 2, 3, 4, 5],
        amp_scale=amp_scale,
        pulse_freq_hz=pulse_freq_hz,
    )
    print(f"\nGenerated {len(all_conditions)} sweep conditions")
    
    # =========================================================================
    # RA1 処理
    # =========================================================================
    print("\n===== Processing RA1 =====")
    
    ra1_path = FiberPathData(
        points=load_csv_points(CONFIG_DIR / "points_along_ra1_fibers.csv"),
        interval_mm=0.1,
    )
    print(f"Data loaded: {datetime.datetime.now()}")
    
    ra1_summary = run_time_domain_sweep(
        fiber_type="ra1",
        fiber_path=ra1_path,
        comsol_dir=COMSOL_DIR,
        sim_config=sim_config,
        t_ms=t_ms,
        output_dir=OUTPUT_DIR,
        conditions=all_conditions,
        target_unit_ids=target_unit_ids,
        verbose=True,
    )
    
    # =========================================================================
    # RA2 処理
    # =========================================================================
    print("\n===== Processing RA2 =====")
    
    ra2_path = FiberPathData(
        points=load_csv_points(CONFIG_DIR / "points_along_ra2_fibers.csv"),
        interval_mm=0.1,
    )
    print(f"Data loaded: {datetime.datetime.now()}")
    
    ra2_summary = run_time_domain_sweep(
        fiber_type="ra2",
        fiber_path=ra2_path,
        comsol_dir=COMSOL_DIR,
        sim_config=sim_config,
        t_ms=t_ms,
        output_dir=OUTPUT_DIR,
        conditions=all_conditions,
        target_unit_ids=target_unit_ids,
        verbose=True,
    )
    
    # =========================================================================
    # SA1 処理
    # =========================================================================
    print("\n===== Processing SA1 =====")
    
    sa1_path = FiberPathData(
        points=load_csv_points(CONFIG_DIR / "points_along_sa1_fibers.csv"),
        interval_mm=0.1,
    )
    print(f"Data loaded: {datetime.datetime.now()}")
    
    sa1_summary = run_time_domain_sweep(
        fiber_type="sa1",
        fiber_path=sa1_path,
        comsol_dir=COMSOL_DIR,
        sim_config=sim_config,
        t_ms=t_ms,
        output_dir=OUTPUT_DIR,
        conditions=all_conditions,
        target_unit_ids=target_unit_ids,
        verbose=True,
    )
    
    # =========================================================================
    # 結果サマリー表示
    # =========================================================================
    print("\n===== AP Count Summary by Condition =====")
    
    for fiber_type, summary in [("RA1", ra1_summary), ("RA2", ra2_summary), 
                                 ("SA1", sa1_summary)]:
        if summary:
            df = pd.DataFrame(summary)
            summary_stats = df.groupby(['ratio']).agg({
                'ap_count': ['sum', 'mean', 'max'],
                'unit_id': 'count'
            }).round(2)
            print(f"\n{fiber_type}:")
            print(summary_stats)
    
    print(f"\nDone: {datetime.datetime.now()}")


if __name__ == "__main__":
    main()
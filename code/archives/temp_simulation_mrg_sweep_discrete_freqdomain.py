import os
import warnings
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Set, Dict, Tuple
import datetime

import numpy as np
from scipy.io import savemat
from neuron import h
from mpi4py import MPI

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
# MPI初期化
# =============================================================================
COMM = MPI.COMM_WORLD
RANK = COMM.Get_rank()
SIZE = COMM.Get_size()


def mpi_print(msg: str, rank: Optional[int] = None):
    """
    MPI環境でのprint関数
    rank=None: 全プロセスが出力
    rank=0: Rank 0のみ出力
    rank=N: Rank Nのみ出力
    """
    if rank is None or RANK == rank:
        print(f"[Rank {RANK}] {msg}", flush=True)


def mpi_barrier(msg: str = ""):
    """バリア同期（デバッグ用メッセージ付き）"""
    COMM.Barrier()
    if msg:
        mpi_print(f"Barrier passed: {msg}", rank=0)


# =============================================================================
# スイープパラメータ
# =============================================================================
FREQ1_LIST = [2000, 4000, 8000]  # Hz
FREQ2_OFFSETS = [0, 20, 40, 80]     # Hz
AMPLITUDE_RATIOS = [
    (1.00, 0.00),
    (0.75, 0.25),
    (0.5, 0.5),
    (0.25, 0.75),
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
    ratio_str: str  # "75_25" など

    @property
    def condition_name(self) -> str:
        return f"f1-{int(self.freq1_hz)}_f2-{int(self.freq2_hz)}_ratio-{self.ratio_str}"


@dataclass
class TaskAssignment:
    """MPIタスク割り当て情報"""
    fiber_type: str
    condition: SweepCondition
    task_id: int  # グローバルタスクID


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
    
    # スキップした条件をワーニング出力（Rank 0のみ）
    if skipped_conditions and RANK == 0:
        warnings.warn(
            f"\n{len(skipped_conditions)} conditions skipped due to missing frequencies in COMSOL data:"
        )
        for cond, missing in skipped_conditions:
            print(f"  SKIP: {cond.condition_name} - missing: {', '.join(missing)}")
    
    return valid_conditions


# =============================================================================
# タスク分散関数
# =============================================================================
def distribute_tasks(
    fiber_types: List[str],
    conditions_per_fiber: Dict[str, List[SweepCondition]],
) -> List[TaskAssignment]:
    """
    全タスクを生成し、現在のRankに割り当てられたタスクを返す
    
    Parameters
    ----------
    fiber_types : List[str]
        処理対象のfiber_type一覧 (例: ["ra1", "ra2", "sa1"])
    conditions_per_fiber : Dict[str, List[SweepCondition]]
        fiber_typeごとの有効な条件リスト
    
    Returns
    -------
    List[TaskAssignment]
        このRankが担当するタスクのリスト
    """
    # 全タスクリスト作成
    all_tasks = []
    task_id = 0
    
    for fiber_type in fiber_types:
        conditions = conditions_per_fiber.get(fiber_type, [])
        for condition in conditions:
            all_tasks.append(TaskAssignment(
                fiber_type=fiber_type,
                condition=condition,
                task_id=task_id,
            ))
            task_id += 1
    
    total_tasks = len(all_tasks)
    
    # このRankが担当するタスクを抽出（ブロック分割方式）
    tasks_per_rank = total_tasks // SIZE
    remainder = total_tasks % SIZE
    
    # 余りを先頭のRankに1つずつ追加配分
    if RANK < remainder:
        start_idx = RANK * (tasks_per_rank + 1)
        end_idx = start_idx + tasks_per_rank + 1
    else:
        start_idx = RANK * tasks_per_rank + remainder
        end_idx = start_idx + tasks_per_rank
    
    my_tasks = all_tasks[start_idx:end_idx]
    
    # タスク割り当て情報を表示
    mpi_print(f"Assigned tasks {start_idx}-{end_idx-1} ({len(my_tasks)} tasks) out of {total_tasks} total")
    
    return my_tasks


def get_task_summary_for_display(
    fiber_types: List[str],
    conditions_per_fiber: Dict[str, List[SweepCondition]],
) -> str:
    """タスク分散状況の概要を文字列で返す（Rank 0用）"""
    total_tasks = sum(len(conds) for conds in conditions_per_fiber.values())
    tasks_per_rank = total_tasks // SIZE
    remainder = total_tasks % SIZE
    
    lines = [
        f"{'='*60}",
        f"MPI Task Distribution Summary",
        f"{'='*60}",
        f"Total MPI Processes: {SIZE}",
        f"Total Tasks: {total_tasks}",
        f"Tasks per fiber_type:",
    ]
    
    for ft in fiber_types:
        n_conds = len(conditions_per_fiber.get(ft, []))
        lines.append(f"  {ft}: {n_conds} conditions")
    
    lines.append(f"\nTask allocation (block distribution):")
    
    task_id = 0
    all_tasks = []
    for ft in fiber_types:
        for cond in conditions_per_fiber.get(ft, []):
            all_tasks.append((ft, cond.condition_name, task_id))
            task_id += 1
    
    for r in range(SIZE):
        if r < remainder:
            start = r * (tasks_per_rank + 1)
            end = start + tasks_per_rank + 1
        else:
            start = r * tasks_per_rank + remainder
            end = start + tasks_per_rank
        
        n_tasks = end - start
        if n_tasks > 0:
            first_task = all_tasks[start]
            last_task = all_tasks[end-1]
            lines.append(
                f"  Rank {r}: tasks {start}-{end-1} ({n_tasks} tasks) "
                f"[{first_task[0]}/{first_task[1]} ... {last_task[0]}/{last_task[1]}]"
            )
        else:
            lines.append(f"  Rank {r}: no tasks")
    
    lines.append(f"{'='*60}")
    return "\n".join(lines)


# =============================================================================
# 単一タスク実行関数
# =============================================================================
def run_single_task(
    task: TaskAssignment,
    fiber_path: FiberPathData,
    pot_data_elec1: MultiFreqPotentialsData,
    pot_data_elec2: MultiFreqPotentialsData,
    sim_config: SimulationConfig,
    t_ms: np.ndarray,
    output_dir: Path,
    target_unit_ids: Optional[Set[int]] = None,
    verbose: bool = True,
) -> List[dict]:
    """
    1つのタスク（1つのfiber_type × 1つのcondition）を実行
    
    Returns
    -------
    List[dict]
        このタスクのサマリーデータ（各unit_idの結果）
    """
    fiber_type = task.fiber_type
    condition = task.condition
    
    fiber_lengths = fiber_path.get_all_fiber_lengths_um()
    
    # 対象unit_idのリスト
    if target_unit_ids is not None:
        unit_ids = sorted(target_unit_ids & set(fiber_lengths.keys()))
    else:
        unit_ids = sorted(fiber_lengths.keys())
    
    if verbose:
        mpi_print(f"Task {task.task_id}: {fiber_type}/{condition.condition_name} ({len(unit_ids)} units)")
    
    # この条件用の電位データを取得
    pot1 = pot_data_elec1.to_potentials_data(condition.freq1_hz)
    pot2 = pot_data_elec2.to_potentials_data(condition.freq2_hz)
    
    # 条件ごとの出力ディレクトリ
    cond_output_dir = output_dir / fiber_type / condition.condition_name
    
    task_summary = []
    
    for unit_idx, unit_id in enumerate(unit_ids):
        length_um = fiber_lengths[unit_id]
        
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
        
        if verbose and (unit_idx + 1) % 10 == 0:
            mpi_print(f"  Task {task.task_id}: {unit_idx + 1}/{len(unit_ids)} units done")
        
        # 結果保存
        # save_unit_result_mat(
        #     cond_output_dir,
        #     fiber_type,
        #     condition,
        #     unit_id,
        #     fiber,
        #     fiber_path,
        #     result,
        #     t_ms,
        # )
        
        # サマリーデータ追加
        task_summary.append({
            'unit_id': unit_id,
            'freq1_hz': condition.freq1_hz,
            'freq2_hz': condition.freq2_hz,
            'amp1_mA': condition.amp1_mA,
            'amp2_mA': condition.amp2_mA,
            'ratio': condition.ratio_str,
            'ap_count': result['ap_count'],
        })
        
        # メモリ解放
        del fiber
        del result
        del V_total
        del V_interp_1
        del V_interp_2
        h('forall delete_section()')
    
    if verbose:
        total_ap = sum(s['ap_count'] for s in task_summary)
        mpi_print(f"Task {task.task_id}: Completed. Total APs = {total_ap}")
    
    return task_summary


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
# サマリー収集・保存関数
# =============================================================================
def gather_all_summaries(local_summary: List[dict]) -> List[dict]:
    """
    全Rankのサマリーデータを Rank 0 に集約
    
    Parameters
    ----------
    local_summary : List[dict]
        このRankのサマリーデータ
    
    Returns
    -------
    List[dict]
        Rank 0: 全Rankのサマリーを結合したリスト
        その他: 空リスト
    """
    # 全Rankのサマリーを収集
    all_summaries = COMM.gather(local_summary, root=0)
    
    if RANK == 0:
        # リストをフラット化
        combined = []
        for rank_summary in all_summaries:
            combined.extend(rank_summary)
        return combined
    else:
        return []


def save_combined_summary(
    summary_data: List[dict],
    output_dir: Path,
    filename: str = "sweep_summary.csv",
):
    """
    全条件のサマリーをCSVで保存（Rank 0のみ実行）
    """
    if RANK != 0:
        return
    
    import pandas as pd
    
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / filename
    
    df = pd.DataFrame(summary_data)
    
    # カラム順序を指定
    columns = ['unit_id', 'freq1_hz', 'freq2_hz', 'amp1_mA', 'amp2_mA', 'ratio', 'ap_count']
    df = df[columns]
    
    # ソート
    df = df.sort_values(['freq1_hz', 'freq2_hz', 'ratio', 'unit_id'])
    
    df.to_csv(filepath, index=False)
    
    mpi_print(f"Saved combined summary: {filepath} ({len(summary_data)} rows)", rank=0)


# =============================================================================
# データローダー（fiber_typeごと）
# =============================================================================
class FiberDataLoader:
    """
    fiber_typeごとのデータを遅延ロードするクラス
    必要なfiber_typeのデータのみをロードしてメモリを節約
    """
    
    def __init__(self, config_dir: Path, comsol_dir: Path):
        self.config_dir = config_dir
        self.comsol_dir = comsol_dir
        self._cache: Dict[str, Tuple[FiberPathData, MultiFreqPotentialsData, MultiFreqPotentialsData]] = {}
    
    def load(self, fiber_type: str) -> Tuple[FiberPathData, MultiFreqPotentialsData, MultiFreqPotentialsData]:
        """
        指定したfiber_typeのデータをロード（キャッシュあり）
        
        Returns
        -------
        Tuple[FiberPathData, MultiFreqPotentialsData, MultiFreqPotentialsData]
            (fiber_path, pot_data_elec1, pot_data_elec2)
        """
        if fiber_type in self._cache:
            return self._cache[fiber_type]
        
        mpi_print(f"Loading data for {fiber_type}...")
        
        # ファイル名のマッピング
        fiber_path = FiberPathData(
            points=load_csv_points(self.config_dir / f"points_along_{fiber_type}_fibers.csv"),
            interval_mm=0.1,
        )
        
        pot_elec1 = MultiFreqPotentialsData.from_multi_frequency_csv(
            self.comsol_dir / f"potentials_along_{fiber_type}_fiber_electrodes_1.csv"
        )
        pot_elec2 = MultiFreqPotentialsData.from_multi_frequency_csv(
            self.comsol_dir / f"potentials_along_{fiber_type}_fiber_electrodes_2.csv"
        )
        
        self._cache[fiber_type] = (fiber_path, pot_elec1, pot_elec2)
        
        mpi_print(f"Loaded {fiber_type}: freqs_elec1={sorted(pot_elec1.frequencies)}, freqs_elec2={sorted(pot_elec2.frequencies)}")
        
        return self._cache[fiber_type]
    
    def clear_cache(self, fiber_type: Optional[str] = None):
        """キャッシュをクリア"""
        if fiber_type is None:
            self._cache.clear()
        elif fiber_type in self._cache:
            del self._cache[fiber_type]


# =============================================================================
# メイン処理関数（MPI並列版）
# =============================================================================
def run_mpi_sweep(
    fiber_types: List[str],
    data_loader: FiberDataLoader,
    sim_config: SimulationConfig,
    t_ms: np.ndarray,
    output_dir: Path,
    target_unit_ids: Optional[Set[int]] = None,
    verbose: bool = True,
) -> List[dict]:
    """
    MPI並列でパラメトリックスイープを実行
    
    Parameters
    ----------
    fiber_types : List[str]
        処理対象のfiber_type一覧 (例: ["ra1", "ra2", "sa1"])
    data_loader : FiberDataLoader
        データローダー
    sim_config : SimulationConfig
        シミュレーション設定
    t_ms : np.ndarray
        時間軸配列
    output_dir : Path
        出力ディレクトリ
    target_unit_ids : Optional[Set[int]]
        対象unit_id（Noneなら全unit）
    verbose : bool
        詳細出力フラグ
    
    Returns
    -------
    List[dict]
        Rank 0: 全サマリーデータ
        その他: 空リスト
    """
    
    # =========================================================================
    # Step 1: 各fiber_typeの有効条件を取得（Rank 0のみ）
    # =========================================================================
    if RANK == 0:
        all_conditions = generate_sweep_conditions()
        conditions_per_fiber: Dict[str, List[SweepCondition]] = {}
        
        for fiber_type in fiber_types:
            fiber_path, pot_elec1, pot_elec2 = data_loader.load(fiber_type)
            valid_conds = filter_valid_conditions(all_conditions, pot_elec1, pot_elec2)
            conditions_per_fiber[fiber_type] = valid_conds
            mpi_print(f"{fiber_type}: {len(valid_conds)} valid conditions", rank=0)
    else:
        conditions_per_fiber = None
    
    # 条件情報をブロードキャスト
    conditions_per_fiber = COMM.bcast(conditions_per_fiber, root=0)
    
    # =========================================================================
    # Step 2: タスク分散情報を表示（Rank 0のみ）
    # =========================================================================
    if RANK == 0:
        summary_str = get_task_summary_for_display(fiber_types, conditions_per_fiber)
        print(summary_str)
    
    mpi_barrier("Task distribution ready")
    
    # =========================================================================
    # Step 3: このRankのタスクを取得
    # =========================================================================
    my_tasks = distribute_tasks(fiber_types, conditions_per_fiber)
    
    if not my_tasks:
        mpi_print("No tasks assigned. Waiting for others...")
        local_summary = []
    else:
        # =====================================================================
        # Step 4: タスク実行
        # =====================================================================
        local_summary = []
        
        # このRankが担当するfiber_typeを特定
        my_fiber_types = sorted(set(task.fiber_type for task in my_tasks))
        
        for fiber_type in my_fiber_types:
            # このfiber_typeのデータをロード
            fiber_path, pot_elec1, pot_elec2 = data_loader.load(fiber_type)
            
            # このfiber_typeのタスクを抽出
            fiber_tasks = [t for t in my_tasks if t.fiber_type == fiber_type]
            
            mpi_print(f"Processing {len(fiber_tasks)} tasks for {fiber_type}")
            
            for task in fiber_tasks:
                task_summary = run_single_task(
                    task=task,
                    fiber_path=fiber_path,
                    pot_data_elec1=pot_elec1,
                    pot_data_elec2=pot_elec2,
                    sim_config=sim_config,
                    t_ms=t_ms,
                    output_dir=output_dir,
                    target_unit_ids=target_unit_ids,
                    verbose=verbose,
                )
                local_summary.extend(task_summary)
            
            # メモリ節約：処理済みfiber_typeのキャッシュをクリア
            # （他のfiber_typeがまだある場合のみ）
            if fiber_type != my_fiber_types[-1]:
                data_loader.clear_cache(fiber_type)
        
        mpi_print(f"All {len(my_tasks)} tasks completed. Local summary: {len(local_summary)} rows")
    
    # =========================================================================
    # Step 5: 全Rankのサマリーを集約
    # =========================================================================
    mpi_barrier("All tasks completed")
    
    all_summary = gather_all_summaries(local_summary)
    
    return all_summary

def main():
    # =========================================================================
    # パス設定
    # =========================================================================
    PROJECT_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = PROJECT_DIR / "data"
    MODEL_DIR = DATA_DIR / "mrg-model"
    CONFIG_DIR = DATA_DIR / "config"
    COMSOL_DIR = DATA_DIR / "comsol" / "electrode_ring"
    OUTPUT_DIR = DATA_DIR / "output" / "sweep_mrg_mpi"
    
    # =========================================================================
    # NEURON初期化（各MPIプロセスで個別に実行）
    # =========================================================================
    os.chdir(MODEL_DIR)
    h.nrn_load_dll(str(MODEL_DIR / "nrnmech.dll"))
    h.load_file("nrngui.hoc")
    h.xopen("MRGaxonBuilder.hoc")
    
    mpi_print("NEURON initialized")
    mpi_barrier("NEURON initialization")
    
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
    # 対象unit_id設定
    # =========================================================================
    # デバッグ用：少数でテスト
    # target_unit_ids = {7}
    
    # 中規模テスト
    # target_unit_ids = {7, 12, 15, 20, 23, 32, 39, 40, 49, 54, 61, 63, 64, 68, 70, 74, 76, 78, 81, 82, 103, 105, 107, 112, 114, 115, 121, 125, 126, 127, 129, 159, 189, 190, 191, 195, 214, 218, 226, 227, 233, 243, 246, 248, 249, 250, 257, 259, 261, 262, 274, 279, 289, 300, 303, 304, 310, 314, 327, 341, 346, 352, 361, 369, 377, 380, 389, 392, 401, 404, 412, 423, 425, 442, 443, 448, 451, 457, 466, 469, 472, 474, 477, 482, 493, 500, 505, 506, 521, 522, 524, 534, 536} #  --x_min -5 --x_max 1 --y_min -27.3 --y_max -21.3
    
    # 全unit_id
    target_unit_ids = None
    
    # =========================================================================
    # 処理対象のfiber_type
    # =========================================================================
    fiber_types = ["ra1", "ra2", "sa1"]
    
    # =========================================================================
    # 開始メッセージ（Rank 0のみ）
    # =========================================================================
    if RANK == 0:
        print(f"\n{'='*60}")
        print(f"MPI Parallel Sweep Simulation")
        print(f"{'='*60}")
        print(f"Start time: {datetime.datetime.now()}")
        print(f"MPI Processes: {SIZE}")
        print(f"Fiber types: {fiber_types}")
        print(f"Target unit_ids: {target_unit_ids if target_unit_ids else 'All'}")
        print(f"Output directory: {OUTPUT_DIR}")
        print(f"{'='*60}\n")
    
    mpi_barrier("Configuration ready")
    
    # =========================================================================
    # データローダー作成
    # =========================================================================
    data_loader = FiberDataLoader(CONFIG_DIR, COMSOL_DIR)
    
    # =========================================================================
    # MPI並列スイープ実行
    # =========================================================================
    start_time = MPI.Wtime()
    
    all_summary = run_mpi_sweep(
        fiber_types=fiber_types,
        data_loader=data_loader,
        sim_config=sim_config,
        t_ms=t_ms,
        output_dir=OUTPUT_DIR,
        target_unit_ids=target_unit_ids,
        verbose=True,
    )
    
    elapsed_time = MPI.Wtime() - start_time
    
    # =========================================================================
    # サマリー保存（Rank 0のみ）
    # =========================================================================
    if RANK == 0:
        save_combined_summary(all_summary, OUTPUT_DIR, "sweep_summary.csv")
    
    mpi_barrier("Summary saved")
    
    # =========================================================================
    # 結果表示（Rank 0のみ）
    # =========================================================================
    if RANK == 0:
        import pandas as pd
        
        print(f"\n{'='*60}")
        print(f"Sweep Completed")
        print(f"{'='*60}")
        print(f"End time: {datetime.datetime.now()}")
        print(f"Total elapsed time: {elapsed_time:.2f} seconds")
        print(f"Total simulations: {len(all_summary)}")
        
        if all_summary:
            df = pd.DataFrame(all_summary)
            
            print(f"\n===== AP Count Summary by Condition =====")
            summary = df.groupby(['freq1_hz', 'freq2_hz', 'ratio']).agg({
                'ap_count': ['sum', 'mean', 'max'],
                'unit_id': 'count'
            }).round(2)
            print(summary)
            
            total_ap = df['ap_count'].sum()
            activated_units = (df['ap_count'] > 0).sum()
            print(f"\nTotal APs: {total_ap}")
            print(f"Activated units: {activated_units} / {len(df)}")
        
        print(f"{'='*60}\n")
    
    # =========================================================================
    # 全プロセスの実行時間を集計（オプション）
    # =========================================================================
    all_times = COMM.gather(elapsed_time, root=0)
    
    if RANK == 0:
        print(f"Execution time per rank:")
        for r, t in enumerate(all_times):
            print(f"  Rank {r}: {t:.2f} seconds")
        print(f"  Max: {max(all_times):.2f} seconds")
        print(f"  Min: {min(all_times):.2f} seconds")
        print(f"  Avg: {sum(all_times)/len(all_times):.2f} seconds")
    
    mpi_barrier("All done")
    mpi_print("Finalized")


if __name__ == "__main__":
    main()
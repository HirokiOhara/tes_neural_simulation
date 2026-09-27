from dataclasses import dataclass, field
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.spatial import ConvexHull
import optuna
import itertools

# ==============================================================================
# データクラス定義
# ==============================================================================

@dataclass
class FrequencyComponent:
    """1つの周波数成分のパラメータ"""
    freq_hz: float
    amp_ma: float
    theta_rad: float


@dataclass
class ElectrodePairParams:
    pair_id: int                 # 1..n_pairs
    electrodes: tuple[int, int]  # (a,b)
    components: list["FrequencyComponent"] = field(default_factory=list)

    def total_amp(self) -> float:
        return sum(c.amp_ma for c in self.components)


@dataclass
class StimulationParams:
    """最適化対象の全パラメータ"""
    pairs: list[ElectrodePairParams] = field(default_factory=list)

    def total_amp(self) -> float:
        return sum(p.total_amp() for p in self.pairs)

    def is_valid(self, max_amp_ma: float = 10.0) -> bool:
        return self.total_amp() <= max_amp_ma


@dataclass
class OptimizationTarget:
    """ユーザー指定の目標"""
    target_x: float
    target_y: float
    radius: float
    target_type: str  # "RA1", "RA2", "SA1", or "any"


@dataclass
class SimulationResult:
    """1つのunit_idのシミュレーション結果"""
    unit_id: int
    fiber_type: str
    ap_count: int
    spike_times: list
    p_x: float
    p_y: float
    p_z: float


@dataclass
class EvaluationScores:
    """各評価指標のスコア"""
    position_error: float
    area_error: float
    selectivity: float
    intensity: float


# ==============================================================================
# 定数・設定
# ==============================================================================

# AVAILABLE_FREQS_HZ = [1000 + 100 * i for i in range(101)]  # 1000〜10000 Hz
AVAILABLE_FREQS_HZ = (
    [base + 10 * i for base in range(1000, 10000, 1000) for i in range(0, 11)]
    + [10000]
)
# AVAILABLE_FREQS_HZ = [2000]
MAX_TOTAL_AMP_MA = 10.0
MAX_FREQ_COMPONENTS_PER_PAIR = 6
MAX_PAIRS_USED = 4


# ==============================================================================
# ヘルパー関数
# ==============================================================================

def load_fiber_info(config_dir: Path) -> pd.DataFrame:
    """fiber_info_summary.csv を読み込み"""
    return pd.read_csv(config_dir / "fiber_info_summary.csv")


def get_fiber_type_counts(fiber_info: pd.DataFrame) -> dict:
    """各fiber typeの数を取得"""
    counts = fiber_info["ReceptorType"].value_counts()
    return {
        "RA1": int(counts.get("RA1", 0)),
        "RA2": int(counts.get("RA2", 0)),
        "SA1": int(counts.get("SA1", 0)),
    }


def get_fiber_type_boundaries(fiber_info: pd.DataFrame) -> dict:
    """unit_id の境界を計算（MRGのみ）"""
    counts = get_fiber_type_counts(fiber_info)
    n_ra1 = counts["RA1"]
    n_ra2 = counts["RA2"]
    n_sa1 = counts["SA1"]
    return {
        "RA1": (1, n_ra1),
        "RA2": (n_ra1 + 1, n_ra1 + n_ra2),
        "SA1": (n_ra1 + n_ra2 + 1, n_ra1 + n_ra2 + n_sa1),
    }


def fiber_type_from_unit_id(unit_id: int, boundaries: dict) -> str:
    """unit_id から fiber_type を判定"""
    for ftype, (start, end) in boundaries.items():
        if start <= unit_id <= end:
            return ftype
    raise ValueError(f"unit_id out of range: {unit_id}")


def get_receptor_position(fiber_info: pd.DataFrame, unit_id: int) -> tuple[float, float, float]:
    """unit_id に対応する受容器位置 (P_x, P_y, P_z) を取得"""
    row = fiber_info[fiber_info["GlobalUnitID"] == unit_id].iloc[0]
    return row["P_x"], row["P_y"], row["P_z"]


def is_within_target_region(p_x: float, p_y: float, target: OptimizationTarget) -> bool:
    """受容器位置が目標領域内か判定"""
    dist = np.sqrt((p_x - target.target_x) ** 2 + (p_y - target.target_y) ** 2)
    return dist <= target.radius

def make_pair_index(available_pairs: list[tuple[int, int]]):
    # 念のため常に(a<b)に正規化
    norm = [tuple(sorted(p)) for p in available_pairs]

    id_to_pair = {i: p for i, p in enumerate(norm, start=1)}
    pair_to_id = {p: i for i, p in id_to_pair.items()}
    return pair_to_id, id_to_pair

def available_pairs_4_simple():
    # あなたのファイル対応:
    # 1->(1,2), 2->(3,4)
    return [(1, 2), (3, 4)]

def available_pairs_8_all():
    # 28ペア全部
    pairs = []
    for a in range(1, 9):
        for b in range(a + 1, 9):
            pairs.append((a, b))
    return pairs

def build_potentials_csv_map(comsol_dir: Path, available_pairs: list[tuple[int, int]]) -> dict:
    """
    potentials_along_{ra1}_fiber_electrodes_{pair_id}.csv
    pair_id は available_pairs の並びで 1..N。
    """
    _, id_to_pair = make_pair_index(available_pairs)
    n_pairs = len(id_to_pair)

    fiber_types = ["RA1", "RA2", "SA1"]
    csv_map = {ft: {} for ft in fiber_types}
    for ft in fiber_types:
        ft_lower = ft.lower()
        for pid in range(1, n_pairs + 1):
            csv_map[ft][pid] = str(
                comsol_dir / f"potentials_along_{ft_lower}_fiber_electrodes_{pid}.csv"
            )
    return csv_map

def no_shared_electrodes(selected_pairs: list[tuple[int, int]]) -> bool:
    used = set()
    for a, b in selected_pairs:
        if a in used or b in used:
            return False
        used.add(a); used.add(b)
    return True

def choose_pair_ids_without_replacement(trial, N: int, k: int) -> list[int]:
    """
    N個のペアIDから k 個を重複なしで選ぶ（順序なし）。
    Optuna の categorical は文字列で扱い、後で復元する。
    """
    # 組合せを文字列化（例: "1,2" や "1,2,3"）
    combos = list(itertools.combinations(range(1, N + 1), k))
    combo_strs = [",".join(map(str, c)) for c in combos]
    
    chosen_str = trial.suggest_categorical(f"pair_combo_k{k}", combo_strs)
    
    # 文字列→整数リストに復元
    return [int(x) for x in chosen_str.split(",")]

# ==============================================================================
# シミュレーション実行関数
# ==============================================================================

def run_simulation_all_fibers(
    params: StimulationParams,
    fiber_info: pd.DataFrame,
    boundaries: dict,
    mrg_points: dict,
    mrg_cum_lengths: dict,
    mrg_fiber_lengths: dict,
    potentials_csv_map: dict,
    dt_ms: float,
    tstop_ms: float,
) -> list[SimulationResult]:
    """全unit_id（MRGのみ: RA1, RA2, SA1）をシミュレートして結果リストを返す"""

    results = []

    for unit_id, length in mrg_fiber_lengths.items():
        unit_id = int(unit_id)
        mrg_start = boundaries["RA1"][0]
        mrg_end   = boundaries["SA1"][1]
        if unit_id < mrg_start or unit_id > mrg_end:
            continue
        ftype = fiber_type_from_unit_id(unit_id, boundaries)
        p_x, p_y, p_z = get_receptor_position(fiber_info, unit_id)

        fiber = MRGaxon(8.7, length_um=length)
        lst_dx_fiber = [
            fiber.distance_to_node_center_from_end(i)
            for i in range(fiber.n_compartments)
        ]

        # 電位の重畳（電極ペア × 周波数成分）
        per_component = []
        for pair_param in params.pairs:
            pot_csv = potentials_csv_map[ftype][pair_param.pair_id]
            for freq_comp in pair_param.components:
                v = get_potential_timeseries_along_fiber(
                    unit_id=unit_id,
                    points=mrg_points,
                    potentials_csv=pot_csv,
                    target_freq_hz=freq_comp.freq_hz,
                    dt_ms=dt_ms,
                    tstop_ms=tstop_ms,
                    amp_ma=freq_comp.amp_ma,
                    phi_rad=freq_comp.theta_rad,
                )
                v_interp = calculate_potentials_lerp(lst_dx_fiber, v, mrg_cum_lengths[unit_id])
                per_component.append(v_interp)

        if len(per_component) == 0:
            v_total = np.zeros((len(lst_dx_fiber), int(tstop_ms / dt_ms) + 1))
        else:
            v_total = superpose_timeseries(per_component)

        v_matrix, ap_count, spike_times = simulate_mrg_fiber(
            fiber, v_total, dt_ms, tstop_ms, lst_dx_fiber
        )

        results.append(SimulationResult(
            unit_id=unit_id,
            fiber_type=ftype,
            ap_count=ap_count,
            spike_times=list(spike_times),
            p_x=p_x,
            p_y=p_y,
            p_z=p_z,
        ))

    return results


# ==============================================================================
# 評価指標の計算関数
# ==============================================================================

def calculate_activation_centroid(
    results: list[SimulationResult], target: OptimizationTarget
) -> tuple[float, float]:
    """活性化した受容器の重心を計算（発火数で重み付け）"""
    total_weight = 0
    weighted_x = 0.0
    weighted_y = 0.0

    for r in results:
        if target.target_type != "any" and r.fiber_type != target.target_type:
            continue
        if r.ap_count > 0:
            weighted_x += r.p_x * r.ap_count
            weighted_y += r.p_y * r.ap_count
            total_weight += r.ap_count

    if total_weight == 0:
        return float("inf"), float("inf")

    return weighted_x / total_weight, weighted_y / total_weight


def calculate_convex_hull_area(results: list[SimulationResult]) -> float:
    """活性化した受容器の凸包面積を計算"""
    active_points = [
        [r.p_x, r.p_y]
        for r in results
        if r.ap_count > 0
    ]

    if len(active_points) < 3:
        return 0.0

    try:
        hull = ConvexHull(active_points)
        return hull.volume  # 2Dでは面積
    except Exception:
        return 0.0


def calculate_scores(
    results: list[SimulationResult], target: OptimizationTarget
) -> EvaluationScores:
    """全評価指標を計算"""

    # 1. 位置スコア（重心と目標の距離）
    cx, cy = calculate_activation_centroid(results, target)
    position_error = np.sqrt((cx - target.target_x) ** 2 + (cy - target.target_y) ** 2)

    # 2. 領域スコア（凸包面積と目標面積の差）
    actual_area = calculate_convex_hull_area(results)
    target_area = np.pi * target.radius ** 2
    area_error = abs(actual_area - target_area)

    # 3. 感覚スコア（指定typeの発火割合）
    target_type_fires = sum(
        r.ap_count for r in results
        if r.fiber_type == target.target_type
    )
    other_type_fires = sum(
        r.ap_count for r in results
        if r.fiber_type != target.target_type
    )
    total_fires = target_type_fires + other_type_fires
    selectivity = target_type_fires / total_fires if total_fires > 0 else 0.0

    # 4. 強度スコア（目標領域内の発火数）
    intensity = sum(
        r.ap_count for r in results
        if is_within_target_region(r.p_x, r.p_y, target)
    )

    return EvaluationScores(
        position_error=position_error,
        area_error=area_error,
        selectivity=selectivity,
        intensity=intensity,
    )


def objective_function(
    scores: EvaluationScores,
    weights: dict = None,
) -> float:
    """多目的を単一スカラーに変換（最小化問題）"""
    if weights is None:
        weights = {
            "position": 100.0,
            "area": 10.0,
            "selectivity": 1.0,
            "intensity": 0.1,
        }

    cost = (
        weights["position"] * scores.position_error
        + weights["area"] * scores.area_error
        - weights["selectivity"] * scores.selectivity
        - weights["intensity"] * scores.intensity
    )

    return cost


# ==============================================================================
# Optuna 最適化
# ==============================================================================

def create_objective(
    fiber_info, boundaries,
    mrg_points, mrg_cum_lengths, mrg_fiber_lengths,
    potentials_csv_map,
    target, dt_ms, tstop_ms,
    available_pairs: list[tuple[int, int]],
):
    _, id_to_pair = make_pair_index(available_pairs)
    N = len(id_to_pair)

    def objective(trial: optuna.Trial) -> float:
        k = trial.suggest_int("n_pairs_used", 1, min(MAX_PAIRS_USED, N))
        chosen_pair_ids = choose_pair_ids_without_replacement(trial, N, k)

        chosen_pair_ids = [trial.suggest_int(f"pair_id_{i}", 1, N) for i in range(k)]
        if len(set(chosen_pair_ids)) != len(chosen_pair_ids):
            return float("inf")

        chosen_pairs = [id_to_pair[pid] for pid in chosen_pair_ids]
        if not no_shared_electrodes(chosen_pairs):
            return float("inf")

        pairs = []
        total_amp = 0.0

        for pid in chosen_pair_ids:
            n_components = trial.suggest_int(
                f"pair{pid:02d}_n_components", 1, MAX_FREQ_COMPONENTS_PER_PAIR
            )
            components = []
            for c in range(n_components):
                freq_hz = trial.suggest_categorical(f"pair{pid:02d}_freq_{c}", AVAILABLE_FREQS_HZ)
                amp_ma  = trial.suggest_float(f"pair{pid:02d}_amp_{c}", 0.0, MAX_TOTAL_AMP_MA)
                theta   = trial.suggest_float(f"pair{pid:02d}_theta_{c}", 0.0, 2*np.pi)
                total_amp += amp_ma
                components.append(FrequencyComponent(freq_hz, amp_ma, theta))

            pairs.append(ElectrodePairParams(
                pair_id=pid,
                electrodes=id_to_pair[pid],
                components=components,
            ))

        if total_amp > MAX_TOTAL_AMP_MA:
            return float("inf")

        params = StimulationParams(pairs=pairs)

        results = run_simulation_all_fibers(
            params, fiber_info, boundaries,
            mrg_points, mrg_cum_lengths, mrg_fiber_lengths,
            potentials_csv_map,
            dt_ms, tstop_ms,
        )

        scores = calculate_scores(results, target)
        cost = objective_function(scores)

        trial.set_user_attr("chosen_pairs", chosen_pairs)
        trial.set_user_attr("total_amp_ma", total_amp)
        return cost

    return objective


def run_optimization(
    fiber_info: pd.DataFrame,
    boundaries: dict,
    mrg_points: dict,
    mrg_cum_lengths: dict,
    mrg_fiber_lengths: dict,
    potentials_csv_map: dict,
    target: OptimizationTarget,
    dt_ms: float,
    tstop_ms: float,
    available_pairs: list,
    n_trials: int = 50,
    study_name: str = "tactile_optimization",
) -> optuna.Study:
    """最適化を実行"""

    objective = create_objective(
        fiber_info, boundaries,
        mrg_points, mrg_cum_lengths, mrg_fiber_lengths,
        potentials_csv_map,
        target, dt_ms, tstop_ms,
        available_pairs=available_pairs,
    )
    study = optuna.create_study(
        study_name=study_name,
        direction="minimize",
        sampler=optuna.samplers.TPESampler(seed=42),
    )

    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)

    return study


def print_optimization_results(study: optuna.Study):
    """最適化結果を表示"""
    print("\n" + "=" * 60)
    print("最適化結果")
    print("=" * 60)

    best_trial = study.best_trial

    print(f"\n最良スコア（cost）: {best_trial.value:.4f}")

    print("\n最適パラメータ:")
    for pair_name in available_pairs:
        use_key = f"use_{pair_name}"
        if best_trial.params.get(use_key, False):
            print(f"\n  {pair_name}:")
            n_comp = best_trial.params.get(f"{pair_name}_n_components", 0)
            print(f"    周波数成分数: {n_comp}")
            for i in range(n_comp):
                freq = best_trial.params.get(f"{pair_name}_freq_{i}", "N/A")
                amp = best_trial.params.get(f"{pair_name}_amp_{i}", "N/A")
                theta = best_trial.params.get(f"{pair_name}_theta_{i}", "N/A")
                if isinstance(amp, float):
                    print(f"    成分{i}: freq={freq}Hz, amp={amp:.3f}mA, theta={theta:.3f}rad")
                else:
                    print(f"    成分{i}: freq={freq}Hz, amp={amp}, theta={theta}")
        else:
            print(f"\n  {pair_name}: 未使用")

    print("\n評価指標:")
    print(f"  total_amp_ma: {best_trial.user_attrs.get('total_amp_ma', 'N/A'):.3f}")
    print(f"  position_error: {best_trial.user_attrs.get('position_error', 'N/A')}")
    print(f"  area_error: {best_trial.user_attrs.get('area_error', 'N/A')}")
    print(f"  selectivity: {best_trial.user_attrs.get('selectivity', 'N/A')}")
    print(f"  intensity: {best_trial.user_attrs.get('intensity', 'N/A')}")


# ==============================================================================
# メイン実行
# ==============================================================================

if __name__ == "__main__":
    import os
    from neuron import h

    from wrapper_MRGaxon import MRGaxon
    from simulate_mrg_model import simulate_mrg_fiber
    from get_potential_along_fiber import (
        get_potential_timeseries_along_fiber,
        calculate_potentials_lerp,
        superpose_timeseries,
    )
    from utility import load_csv_points
    from get_fiber_length import calculate_cumulative_dx_along_fiber, calculate_fiber_lengths

    # --- パス設定 ---
    PROJECT_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = PROJECT_DIR / "data"
    MODEL_DIR = DATA_DIR / "fiber_models"
    CONFIG_DIR = DATA_DIR / "config"
    COMSOL_DIR = DATA_DIR / "comsol" / "electrode_square"

    # --- NEURON 初期化 ---
    os.chdir(MODEL_DIR)
    h.nrn_load_dll(str(MODEL_DIR / "nrnmech.dll"))
    h.load_file("nrngui.hoc")
    h.xopen("MRGaxonBuilder.hoc")

    # --- シミュレーション設定 ---
    dt_ms = 0.01
    tstop_ms = 100.0

    # --- データ読み込み ---
    fiber_info = load_fiber_info(CONFIG_DIR)
    boundaries = get_fiber_type_boundaries(fiber_info)

    print("Fiber type boundaries (MRG only):")
    for ftype, (start, end) in boundaries.items():
        print(f"  {ftype}: {start} - {end}")

    # MRG fibers
    mrg_points = load_csv_points(CONFIG_DIR / "points_along_all_fibers.csv")
    mrg_cum_lengths = calculate_cumulative_dx_along_fiber(mrg_points)
    mrg_fiber_lengths = calculate_fiber_lengths(mrg_points)

    # 4電極の場合
    available_pairs = available_pairs_4_simple()
    potentials_csv_map = build_potentials_csv_map(COMSOL_DIR, available_pairs)
    # 8電極の場合
    # available_pairs = available_pairs_8_all()
    # potentials_csv_map = build_potentials_csv_map(comsol_dir, available_pairs)

    # --- 最適化ターゲット設定 ---
    print("\nReceptor position range:")
    print(f"  P_x: {fiber_info['P_x'].min():.2f} - {fiber_info['P_x'].max():.2f}")
    print(f"  P_y: {fiber_info['P_y'].min():.2f} - {fiber_info['P_y'].max():.2f}")

    target = OptimizationTarget(
        target_x=(fiber_info["P_x"].min() + fiber_info["P_x"].max()) / 2,
        target_y=(fiber_info["P_y"].min() + fiber_info["P_y"].max()) / 2,
        radius=1.0,
        target_type="RA1",
    )

    print(f"\nOptimization target:")
    print(f"  Position: ({target.target_x:.2f}, {target.target_y:.2f})")
    print(f"  Radius: {target.radius}")
    print(f"  Target type: {target.target_type}")

    # --- 最適化実行 ---
    print("\n" + "=" * 60)
    print("最適化開始 (MRGモデルのみ: RA1, RA2, SA1)")
    print("=" * 60)

    study = run_optimization(
        fiber_info=fiber_info,
        boundaries=boundaries,
        mrg_points=mrg_points,
        mrg_cum_lengths=mrg_cum_lengths,
        mrg_fiber_lengths=mrg_fiber_lengths,
        potentials_csv_map=potentials_csv_map,
        target=target,
        dt_ms=dt_ms,
        available_pairs=available_pairs,
        tstop_ms=tstop_ms,
        n_trials=10,
    )

    # --- 結果表示 ---
    print_optimization_results(study)

    # --- 結果保存 ---
    results_df = study.trials_dataframe()
    results_df.to_csv(DATA_DIR / "optimization_results.csv", index=False)
    print(f"\n結果を保存: {DATA_DIR / 'optimization_results.csv'}")
from dataclasses import dataclass, field
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.spatial import ConvexHull
import optuna


# ==============================================================================
# データクラス定義
# ==============================================================================

@dataclass
class FrequencyComponent:
    """1つの周波数成分のパラメータ"""
    freq_hz: float       # 周波数 [Hz]（離散選択）
    amp_ma: float        # 振幅 [mA]
    theta_rad: float     # 位相 [rad]


@dataclass
class ElectrodePairParams:
    """1つの電極ペアのパラメータ（複数周波数成分を持つ）"""
    pair_name: str                              # "e1e2", "e4e3", etc.
    components: list[FrequencyComponent] = field(default_factory=list)

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
    fiber_type: str       # "RA1", "RA2", "SA1", "ENF"
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
    enf_penalty: float


# ==============================================================================
# 定数・設定
# ==============================================================================

# AVAILABLE_FREQS_HZ = [1000 + 10 * i for i in range(501)]  # 1000〜5000 Hz
AVAILABLE_FREQS_HZ = [2000]
MAX_TOTAL_AMP_MA = 10.0
AVAILABLE_PAIRS = ["e1e2", "e4e3"]
MAX_FREQ_COMPONENTS_PER_PAIR = 6


# ==============================================================================
# ヘルパー関数
# ==============================================================================

def load_fiber_info(config_dir: Path) -> pd.DataFrame:
    """fiber_info_summary.csv を読み込み"""
    return pd.read_csv(config_dir / "fiber_info_summary.csv")


def get_fiber_type_boundaries(fiber_info: pd.DataFrame) -> dict:
    """unit_id の境界を計算"""
    counts = fiber_info["ReceptorType"].value_counts()
    n_ra1 = int(counts.get("RA1", 0))
    n_ra2 = int(counts.get("RA2", 0))
    n_sa1 = int(counts.get("SA1", 0))
    n_enf = int(counts.get("ENF", 0))
    return {
        "RA1": (1, n_ra1),
        "RA2": (n_ra1 + 1, n_ra1 + n_ra2),
        "SA1": (n_ra1 + n_ra2 + 1, n_ra1 + n_ra2 + n_sa1),
        "ENF": (n_ra1 + n_ra2 + n_sa1 + 1, n_ra1 + n_ra2 + n_sa1 + n_enf),
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


def build_potentials_csv_map(comsol_dir: Path) -> dict:
    """fiber_type と pair_name から CSV パスを生成"""
    fiber_types = ["RA1", "RA2", "SA1", "ENF"]
    csv_map = {}
    for ftype in fiber_types:
        csv_map[ftype] = {}
        for pair in AVAILABLE_PAIRS:
            csv_map[ftype][pair] = str(
                comsol_dir / f"fourier_transform/finger_model/freq_domain_{ftype}_fiber_electrodes_{pair}.csv"
            )
    return csv_map


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
    enf_points: dict,
    enf_cum_lengths: dict,
    enf_fiber_lengths: dict,
    potentials_csv_map: dict,
    dt_ms: float,
    tstop_ms: float,
) -> list[SimulationResult]:
    """全unit_id（MRG + Thio）をシミュレートして結果リストを返す"""

    results = []

    # --- MRG fibers (RA1, RA2, SA1) ---
    for unit_id, length in mrg_fiber_lengths.items():
        unit_id = int(unit_id)
        ftype = fiber_type_from_unit_id(unit_id, boundaries)

        if ftype == "ENF":
            continue

        p_x, p_y, p_z = get_receptor_position(fiber_info, unit_id)

        fiber = MRGaxon(8.7, length_um=length)
        lst_dx_fiber = [
            fiber.distance_to_node_center_from_end(i)
            for i in range(fiber.n_compartments)
        ]

        # 電位の重畳（電極ペア × 周波数成分）
        per_component = []
        for pair_param in params.pairs:
            pot_csv = potentials_csv_map[ftype][pair_param.pair_name]
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

        # def simulate_mrg_fiber(fiber_model, potentials_timeseries_along_fiber, dt_ms, tstop, lst_cumulative_dx):
        v_matrix, ap_count, spike_times = simulate_mrg_fiber(
            fiber_model=fiber, potentials_timeseries_along_fiber=v_total, dt_ms=dt_ms, tstop=tstop_ms, lst_cumulative_dx=lst_dx_fiber
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

    # --- ENF fibers (Thio model) ---
    for unit_id, length in enf_fiber_lengths.items():
        unit_id = int(unit_id)

        p_x, p_y, p_z = get_receptor_position(fiber_info, unit_id)

        fiber = ThioCFiber(
            fiber_diameter=0.8,
            length_um=length,
            temperature=37,
            particle_index=1
        )
        lst_dx_fiber = [
            fiber.distance_to_node_center_from_end(i)
            for i in range(len(fiber))
        ]

        # 電位の重畳（電極ペア × 周波数成分）
        per_component = []
        for pair_param in params.pairs:
            pot_csv = potentials_csv_map["ENF"][pair_param.pair_name]
            for freq_comp in pair_param.components:
                v = get_potential_timeseries_along_fiber(
                    unit_id=unit_id,
                    points=enf_points,
                    potentials_csv=pot_csv,
                    target_freq_hz=freq_comp.freq_hz,
                    dt_ms=dt_ms,
                    tstop_ms=tstop_ms,
                    amp_ma=freq_comp.amp_ma,
                    phi_rad=freq_comp.theta_rad,
                )
                v_interp = calculate_potentials_lerp(lst_dx_fiber, v, enf_cum_lengths[unit_id])
                per_component.append(v_interp)

        if len(per_component) == 0:
            v_total = np.zeros((len(lst_dx_fiber), int(tstop_ms / dt_ms) + 1))
        else:
            v_total = superpose_timeseries(per_component)

        v_matrix, ap_count, spike_times = simulate_thio_fiber(
            fiber, v_total, dt_ms, tstop_ms, lst_dx_fiber
        )

        results.append(SimulationResult(
            unit_id=unit_id,
            fiber_type="ENF",
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
        if r.fiber_type == "ENF":
            continue
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
        if r.ap_count > 0 and r.fiber_type != "ENF"
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
        if r.fiber_type in ["RA1", "RA2", "SA1"] and r.fiber_type != target.target_type
    )
    total_fires = target_type_fires + other_type_fires
    selectivity = target_type_fires / total_fires if total_fires > 0 else 0.0

    # 4. 強度スコア（目標領域内の発火数）
    intensity = sum(
        r.ap_count for r in results
        if r.fiber_type != "ENF" and is_within_target_region(r.p_x, r.p_y, target)
    )

    # 5. ENFペナルティ
    enf_penalty = sum(r.ap_count for r in results if r.fiber_type == "ENF")

    return EvaluationScores(
        position_error=position_error,
        area_error=area_error,
        selectivity=selectivity,
        intensity=intensity,
        enf_penalty=enf_penalty,
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
            "enf_penalty": 1000.0,
        }

    cost = (
        weights["position"] * scores.position_error
        + weights["area"] * scores.area_error
        - weights["selectivity"] * scores.selectivity
        - weights["intensity"] * scores.intensity
        + weights["enf_penalty"] * scores.enf_penalty
    )

    return cost


# ==============================================================================
# Optuna 最適化
# ==============================================================================

def create_objective(
    fiber_info: pd.DataFrame,
    boundaries: dict,
    mrg_points: dict,
    mrg_cum_lengths: dict,
    mrg_fiber_lengths: dict,
    enf_points: dict,
    enf_cum_lengths: dict,
    enf_fiber_lengths: dict,
    potentials_csv_map: dict,
    target: OptimizationTarget,
    dt_ms: float,
    tstop_ms: float,
):
    """Optuna の objective 関数を生成"""

    def objective(trial: optuna.Trial) -> float:
        pairs = []
        total_amp = 0.0

        for pair_name in AVAILABLE_PAIRS:
            # このペアを使うか
            use_pair = trial.suggest_categorical(f"use_{pair_name}", [True, False])

            if not use_pair:
                continue

            # 周波数成分の数（1〜6）
            n_components = trial.suggest_int(
                f"{pair_name}_n_components", 1, MAX_FREQ_COMPONENTS_PER_PAIR
            )

            components = []
            for i in range(n_components):
                freq_hz = trial.suggest_categorical(
                    f"{pair_name}_freq_{i}", AVAILABLE_FREQS_HZ
                )
                amp_ma = trial.suggest_float(
                    f"{pair_name}_amp_{i}", 0.0, MAX_TOTAL_AMP_MA
                )
                theta_rad = trial.suggest_float(
                    f"{pair_name}_theta_{i}", 0.0, 2 * np.pi
                )

                total_amp += amp_ma

                components.append(FrequencyComponent(
                    freq_hz=freq_hz,
                    amp_ma=amp_ma,
                    theta_rad=theta_rad,
                ))

            pairs.append(ElectrodePairParams(
                pair_name=pair_name,
                components=components,
            ))

        # 少なくとも1つのペアが必要
        if len(pairs) == 0:
            return float("inf")

        # 制約チェック: 全振幅合計 ≤ 10mA
        if total_amp > MAX_TOTAL_AMP_MA:
            return float("inf")

        params = StimulationParams(pairs=pairs)

        # シミュレーション実行
        results = run_simulation_all_fibers(
            params=params,
            fiber_info=fiber_info,
            boundaries=boundaries,
            mrg_points=mrg_points,
            mrg_cum_lengths=mrg_cum_lengths,
            mrg_fiber_lengths=mrg_fiber_lengths,
            enf_points=enf_points,
            enf_cum_lengths=enf_cum_lengths,
            enf_fiber_lengths=enf_fiber_lengths,
            potentials_csv_map=potentials_csv_map,
            dt_ms=dt_ms,
            tstop_ms=tstop_ms,
        )

        # 評価
        scores = calculate_scores(results, target)
        cost = objective_function(scores)

        # ログ出力
        trial.set_user_attr("total_amp_ma", total_amp)
        trial.set_user_attr("n_pairs", len(pairs))
        trial.set_user_attr("n_total_components", sum(len(p.components) for p in pairs))
        trial.set_user_attr("position_error", scores.position_error)
        trial.set_user_attr("area_error", scores.area_error)
        trial.set_user_attr("selectivity", scores.selectivity)
        trial.set_user_attr("intensity", scores.intensity)
        trial.set_user_attr("enf_penalty", scores.enf_penalty)

        return cost

    return objective


def run_optimization(
    fiber_info: pd.DataFrame,
    boundaries: dict,
    mrg_points: dict,
    mrg_cum_lengths: dict,
    mrg_fiber_lengths: dict,
    enf_points: dict,
    enf_cum_lengths: dict,
    enf_fiber_lengths: dict,
    potentials_csv_map: dict,
    target: OptimizationTarget,
    dt_ms: float,
    tstop_ms: float,
    n_trials: int = 50,
    study_name: str = "tactile_optimization",
) -> optuna.Study:
    """最適化を実行"""

    objective = create_objective(
        fiber_info=fiber_info,
        boundaries=boundaries,
        mrg_points=mrg_points,
        mrg_cum_lengths=mrg_cum_lengths,
        mrg_fiber_lengths=mrg_fiber_lengths,
        enf_points=enf_points,
        enf_cum_lengths=enf_cum_lengths,
        enf_fiber_lengths=enf_fiber_lengths,
        potentials_csv_map=potentials_csv_map,
        target=target,
        dt_ms=dt_ms,
        tstop_ms=tstop_ms,
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
    for pair_name in AVAILABLE_PAIRS:
        use_key = f"use_{pair_name}"
        if best_trial.params.get(use_key, False):
            print(f"\n  {pair_name}:")
            n_comp = best_trial.params.get(f"{pair_name}_n_components", 0)
            print(f"    周波数成分数: {n_comp}")
            for i in range(n_comp):
                freq = best_trial.params.get(f"{pair_name}_freq_{i}", "N/A")
                amp = best_trial.params.get(f"{pair_name}_amp_{i}", "N/A")
                theta = best_trial.params.get(f"{pair_name}_theta_{i}", "N/A")
                print(f"    成分{i}: freq={freq}Hz, amp={amp:.3f}mA, theta={theta:.3f}rad")
        else:
            print(f"\n  {pair_name}: 未使用")

    print("\n評価指標:")
    print(f"  total_amp_ma: {best_trial.user_attrs.get('total_amp_ma', 'N/A'):.3f}")
    print(f"  position_error: {best_trial.user_attrs.get('position_error', 'N/A')}")
    print(f"  area_error: {best_trial.user_attrs.get('area_error', 'N/A')}")
    print(f"  selectivity: {best_trial.user_attrs.get('selectivity', 'N/A')}")
    print(f"  intensity: {best_trial.user_attrs.get('intensity', 'N/A')}")
    print(f"  enf_penalty: {best_trial.user_attrs.get('enf_penalty', 'N/A')}")


# ==============================================================================
# メイン実行
# ==============================================================================

if __name__ == "__main__":
    import os
    from neuron import h

    from wrapper_MRGaxon import MRGaxon
    from wrapper_cFiberBuilder import ThioCFiber
    from simulate_mrg_model import simulate_mrg_fiber
    from simulate_thio_model import simulate_thio_fiber
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
    COMSOL_DIR = DATA_DIR / "comsol"

    # --- NEURON 初期化 ---
    os.chdir(MODEL_DIR)
    h.nrn_load_dll(str(MODEL_DIR / "nrnmech.dll"))
    h.load_file("nrngui.hoc")
    h.xopen("MRGaxonBuilder.hoc")
    h.xopen('cFiberBuilder.hoc')
    h.load_file('balance.hoc')


    # --- シミュレーション設定 ---
    dt_ms = 0.01
    tstop_ms = 10.0

    # --- データ読み込み ---
    fiber_info = load_fiber_info(CONFIG_DIR)
    boundaries = get_fiber_type_boundaries(fiber_info)

    print("Fiber type boundaries:")
    for ftype, (start, end) in boundaries.items():
        print(f"  {ftype}: {start} - {end}")

    # MRG fibers
    mrg_points = load_csv_points(CONFIG_DIR / "points_along_all_fibers.csv")
    mrg_cum_lengths = calculate_cumulative_dx_along_fiber(mrg_points)
    mrg_fiber_lengths = calculate_fiber_lengths(mrg_points)

    # ENF fibers
    enf_points = load_csv_points(CONFIG_DIR / "points_along_enf_fibers.csv")
    enf_cum_lengths = calculate_cumulative_dx_along_fiber(enf_points)
    enf_fiber_lengths = calculate_fiber_lengths(enf_points)

    # potentials CSV map
    potentials_csv_map = build_potentials_csv_map(COMSOL_DIR)

    # --- 最適化ターゲット設定 ---
    # fiber_info から P_x, P_y の範囲を確認
    print("\nReceptor position range:")
    print(f"  P_x: {fiber_info['P_x'].min():.2f} - {fiber_info['P_x'].max():.2f}")
    print(f"  P_y: {fiber_info['P_y'].min():.2f} - {fiber_info['P_y'].max():.2f}")

    # 目標位置を設定（例：中央付近）
    target = OptimizationTarget(
        target_x=(fiber_info["P_x"].min() + fiber_info["P_x"].max()) / 2,
        target_y=(fiber_info["P_y"].min() + fiber_info["P_y"].max()) / 2,
        radius=1.0,  # mm（適宜調整）
        target_type="RA1",
    )

    print(f"\nOptimization target:")
    print(f"  Position: ({target.target_x:.2f}, {target.target_y:.2f})")
    print(f"  Radius: {target.radius}")
    print(f"  Target type: {target.target_type}")

    # --- 最適化実行 ---
    print("\n" + "=" * 60)
    print("最適化開始")
    print("=" * 60)

    study = run_optimization(
        fiber_info=fiber_info,
        boundaries=boundaries,
        mrg_points=mrg_points,
        mrg_cum_lengths=mrg_cum_lengths,
        mrg_fiber_lengths=mrg_fiber_lengths,
        enf_points=enf_points,
        enf_cum_lengths=enf_cum_lengths,
        enf_fiber_lengths=enf_fiber_lengths,
        potentials_csv_map=potentials_csv_map,
        target=target,
        dt_ms=dt_ms,
        tstop_ms=tstop_ms,
        n_trials=10,  # テスト用に少なく設定（本番は50〜100以上）
    )

    # --- 結果表示 ---
    print_optimization_results(study)

    # --- 結果保存（オプション） ---
    results_df = study.trials_dataframe()
    results_df.to_csv(DATA_DIR / "optimization_results.csv", index=False)
    print(f"\n結果を保存: {DATA_DIR / 'optimization_results.csv'}")
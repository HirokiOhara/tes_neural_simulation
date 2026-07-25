"""
電位データの補間と時系列変換
- 周波数領域と時間領域の両方に対応
"""
import numpy as np
from typing import List, Optional
import warnings

from comsol_data import PotentialsData, FiberPathData, DomainType, coord_key


def get_potential_timeseries_at_comsol_points(
    pot_data: PotentialsData,
    fiber_path: FiberPathData,
    unit_id: int,
    t_ms: np.ndarray,
    freq_hz: float = None,
    amp_mA: float = 1.0,
    phase_rad: float = 0.0,
    decimals: int = 6,
) -> np.ndarray:
    """
    指定unit_idのCOMSOL座標点における電位時系列を取得
    
    周波数領域の場合: freq_hz, amp_mA, phase_rad で時系列に変換
    時間領域の場合: amp_mA でスケーリング（freq_hz, phase_rad は無視）
    
    Parameters
    ----------
    pot_data : PotentialsData
        COMSOL電位データ
    fiber_path : FiberPathData
        神経パス情報
    unit_id : int
        対象の神経線維ID
    t_ms : np.ndarray
        出力の時間ベクトル[ms]
    freq_hz : float, optional
        抽出する周波数[Hz]（周波数領域の場合のみ必要）
    amp_mA : float
        電流振幅[mA]（スケーリング係数）
    phase_rad : float
        位相[rad]（周波数領域の場合のみ使用）
    decimals : int
        座標マッチングの小数点桁数
    
    Returns
    -------
    V_timeseries : (P, T) COMSOL点数 x 時間ステップ [mV]
    """
    # unit_idに対応するCOMSOLインデックスを取得
    indices = _get_unit_point_indices(
        fiber_path.points, unit_id, pot_data.coord_to_index, decimals
    )
    
    if len(indices) == 0:
        warnings.warn(f"No matching coordinates found for unit_id={unit_id}")
        return np.zeros((0, len(t_ms)), dtype=np.float32)
    
    # 領域タイプに応じた処理
    if pot_data.domain_type == DomainType.FREQUENCY:
        return _get_timeseries_from_frequency(
            pot_data, indices, t_ms, freq_hz, amp_mA, phase_rad
        )
    else:  # TIME
        return _get_timeseries_from_time(
            pot_data, indices, t_ms, amp_mA
        )


def interpolate_to_axon_nodes(
    V_at_comsol_points: np.ndarray,
    comsol_cumulative_dx_um: np.ndarray,
    axon_node_positions_um: np.ndarray,
) -> np.ndarray:
    """
    COMSOL点での電位を軸索ノード位置に線形補間
    
    Parameters
    ----------
    V_at_comsol_points : (P, T) COMSOL点での電位時系列
    comsol_cumulative_dx_um : (P,) COMSOL点の累積距離[um]
    axon_node_positions_um : (N,) 軸索ノードの位置[um]
    
    Returns
    -------
    V_at_nodes : (N, T) 軸索ノードでの電位時系列
    """
    V = np.asarray(V_at_comsol_points, dtype=float)
    dx = np.asarray(comsol_cumulative_dx_um, dtype=float).ravel()
    xq = np.asarray(axon_node_positions_um, dtype=float).ravel()
    
    if V.shape[0] != len(dx):
        raise ValueError(
            f"V shape[0]={V.shape[0]} does not match dx length={len(dx)}"
        )
    
    # 範囲外はクランプ
    xq_clamped = np.clip(xq, dx[0], dx[-1])
    
    # 線形補間のインデックス計算
    i = np.searchsorted(dx, xq_clamped, side="left")
    i = np.clip(i, 1, len(dx) - 1)
    j = i - 1
    
    # 補間重み
    x0, x1 = dx[j], dx[i]
    denom = x1 - x0
    denom[denom == 0] = 1.0  # ゼロ除算回避
    w = ((xq_clamped - x0) / denom)[:, None]  # (N, 1)
    
    # 補間実行
    V_interp = (1.0 - w) * V[j, :] + w * V[i, :]  # (N, T)
    return V_interp.astype(np.float32)


def superpose_potentials(potential_list: List[np.ndarray]) -> np.ndarray:
    """複数の電位時系列を重畳"""
    if len(potential_list) == 0:
        return np.zeros((0, 0), dtype=np.float32)
    result = potential_list[0].astype(np.float64)  # 精度のため
    for v in potential_list[1:]:
        result += v
    return result.astype(np.float32)


# =============================================================================
# Internal Functions
# =============================================================================

def _get_unit_point_indices(
    points: np.ndarray,
    unit_id: int,
    coord_to_index: dict,
    decimals: int = 6
) -> np.ndarray:
    """unit_idに対応するCOMSOLインデックス配列を取得"""
    group = points[points[:, 0] == unit_id]
    xyz = group[:, 1:4]
    
    indices = []
    missing = 0
    for p in xyz:
        key = coord_key(p, decimals)
        if key in coord_to_index:
            indices.append(coord_to_index[key])
        else:
            missing += 1
    
    if missing > 0:
        warnings.warn(f"unit_id={unit_id}: {missing} coordinates not found in COMSOL data")
    
    return np.array(indices, dtype=int)


def _get_timeseries_from_frequency(
    pot_data: PotentialsData,
    indices: np.ndarray,
    t_ms: np.ndarray,
    freq_hz: float,
    amp_mA: float,
    phase_rad: float,
) -> np.ndarray:
    """周波数領域データから時系列を生成"""
    if freq_hz is None:
        raise ValueError("freq_hz is required for frequency domain data")
    
    # 周波数インデックスを探す
    freq_idx = _find_freq_index(pot_data.freqs, freq_hz)
    if freq_idx is None:
        warnings.warn(f"Frequency {freq_hz} Hz not found")
        return np.zeros((len(indices), len(t_ms)), dtype=np.float32)
    
    V_complex = pot_data.V_complex_mV[indices, freq_idx]  # (P,)
    return _complex_to_timeseries(V_complex, amp_mA, freq_hz, t_ms, phase_rad)


def _get_timeseries_from_time(
    pot_data: PotentialsData,
    indices: np.ndarray,
    t_ms: np.ndarray,
    amp_mA: float,
) -> np.ndarray:
    """時間領域データから時系列を取得（必要に応じて補間）"""
    V_source = pot_data.V_timeseries_mV[indices, :]  # (P, T_source)
    t_source = pot_data.t_ms  # (T_source,)
    
    # 時間軸が一致していればそのまま返す
    if len(t_ms) == len(t_source) and np.allclose(t_ms, t_source):
        return (amp_mA * V_source).astype(np.float32)
    
    # 時間軸が異なる場合は線形補間
    P = len(indices)
    T = len(t_ms)
    V_interp = np.zeros((P, T), dtype=np.float32)
    
    for p in range(P):
        V_interp[p, :] = np.interp(t_ms, t_source, V_source[p, :])
    
    return (amp_mA * V_interp).astype(np.float32)


def _find_freq_index(freqs: np.ndarray, target_freq: float, atol: float = 1e-6) -> Optional[int]:
    """周波数配列から対象周波数のインデックスを探す"""
    if freqs is None or len(freqs) == 0:
        return None
    diffs = np.abs(freqs - target_freq)
    idx = int(np.argmin(diffs))
    if diffs[idx] < atol:
        return idx
    return None


def _complex_to_timeseries(
    V_complex: np.ndarray,
    amp_mA: float,
    freq_hz: float,
    t_ms: np.ndarray,
    phase_rad: float
) -> np.ndarray:
    """複素電位を実時間領域の時系列に変換"""
    t_s = t_ms * 1e-3
    ejwt = np.exp(1j * (2.0 * np.pi * freq_hz * t_s + phase_rad))
    v = np.real((amp_mA * V_complex)[:, None] * ejwt[None, :])
    return v.astype(np.float32)
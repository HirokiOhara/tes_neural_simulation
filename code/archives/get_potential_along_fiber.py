import numpy as np
from typing import Dict, List, Tuple
import warnings
from dataclasses import dataclass, field

V_TO_MV = 1e3

# ----------------------------
# I/O: COMSOL potentials CSV
# ----------------------------
def load_potentials_csv(filepath: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    '''
    CSV format (after 9-line header):
      [x, y, z, f1, R1, I1, f2, R2, I2, ..., fK, RK, IK]

    Returns
      coords: (N,3)
      freqs: (K,)              float (as in file)
      V:     (N,K) complex     complex potentials
    '''
    arr = np.genfromtxt(filepath, delimiter=',', skip_header=9)
    coords = arr[:, 0:3]
    rest = arr[:, 3:]

    K = rest.shape[1] // 3
    freqs = rest[0, 0::3].copy()        # (K,)
    R = rest[:, 1::3]
    I = rest[:, 2::3]
    V = R + 1j * I
    V_mV = V * V_TO_MV
    return coords, freqs, V_mV

def load_potentials_csv_by_freq(filepath: str, freq_hz: float) -> Tuple[np.ndarray, float, np.ndarray]:
    """
    filepath のCSVから、指定周波数 freq_hz に対応する列だけ抽出して返す。

    Returns
      coords: (N,3)
      freq:   float
      V:      (N,) complex (mV)
    """
    coords, freqs, V_mV = load_potentials_csv(filepath)

    # 浮動小数なので完全一致は避けて近いものを探す
    idx = int(np.argmin(np.abs(freqs - freq_hz)))

    # どれくらい一致しているかチェックしたい場合（必要なら閾値調整）
    if not np.isclose(freqs[idx], freq_hz, rtol=0, atol=1e-9):
        raise ValueError(f"指定周波数 {freq_hz} Hz が見つかりません。ファイルの周波数例: {freqs}")

    return coords, float(freqs[idx]), V_mV[:, idx]

def list_freqs_in_potentials_csv(filepath: str) -> np.ndarray:
    '''potentials CSVが持つ周波数一覧(K,)を返す。'''
    _, freqs, _ = load_potentials_csv(filepath)
    return freqs


# ----------------------------
# Coordinates: match points to COMSOL coords
# ----------------------------
def coord_key(p_xyz: np.ndarray, decimals: int = 6) -> tuple:
    p = p_xyz.astype(float)
    return (
        float(f"{p[0]:.{decimals}f}"),
        float(f"{p[1]:.{decimals}f}"),
        float(f"{p[2]:.{decimals}f}")
    )


def build_coord_to_index(coords: np.ndarray, decimals: int = 6) -> Dict[tuple, int]:
    coord_to_index: Dict[tuple, int] = {}

    for i in range(coords.shape[0]):
        k = coord_key(coords[i], decimals)
        coord_to_index[k] = int(i)

    return coord_to_index


def unit_indices_from_points(points_along_line: np.ndarray, unit_id: int, coord_to_index: Dict[tuple, int], decimals: int = 6) -> np.ndarray:
    '''
    points_along_line assumed columns:
      col0: unit_id
      col1-3: x,y,z
    '''
    group = points_along_line[points_along_line[:, 0] == unit_id]
    xyz = group[:, 1:4]

    idx = []
    missing = 0
    for p in xyz:
        k = coord_key(p, decimals)
        if k not in coord_to_index:
            missing += 1
            print(f"Missing key: {k}")
            print(f"Original point: {p}")
            print(f"Point repr: {repr(p)}")  # より詳細な表現
            print("---")
            continue
        idx.append(coord_to_index[k])

    if missing > 0:
        warnings.warn(f'[unit_indices_from_points] missing coords: {missing} points were skipped.')

    return np.asarray(idx, dtype=int)


# ----------------------------
# Signal conversion
# ----------------------------
def complex_to_timeseries_real(V_points: np.ndarray, amp_ma: float, f_hz: float, t_ms: np.ndarray, phi_rad: float) -> np.ndarray:
    '''
    V_points: (P,) complex
    returns : (P,T) float32
    '''
    t_s = t_ms * 1e-3
    ejwt = np.exp(1j * (2.0 * np.pi * f_hz * t_s + phi_rad))   # (T,)
    v = np.real((amp_ma * V_points)[:, None] * ejwt[None, :])  # (P,T)
    return v.astype(np.float32)


def get_potential_timeseries_along_fiber(
    unit_id: int,
    points,
    pot: dataclass,
    target_freq_hz: float,
    t_ms: np.ndarray,
    amp_ma: float,
    phi_rad: float = 0.0,
    decimals: int = 6,
) -> np.ndarray:
    """
    1つの PotentialsData から、指定周波数1成分だけ取り出して (P,T) を返す（CSVは読まない）。
    """

    idx = unit_indices_from_points(points, unit_id, pot.coord_to_index, decimals=decimals)

    target_f = float(target_freq_hz)
    k_list = np.where(pot.freqs == target_f)[0]
    if len(k_list) == 0:
        return np.zeros((len(idx), len(t_ms)), dtype=np.float32)
    k = int(k_list[0])

    V_points = pot.V_all[idx, k]  # (P,)
    return complex_to_timeseries_real(V_points, float(amp_ma), target_f, t_ms, float(phi_rad))


# ----------------------------
# Superposition (time domain)
# ----------------------------
def superpose_timeseries(v_list: List[np.ndarray]) -> np.ndarray:
    '''
    入力：複数の (P,T) を足し合わせて (P,T) を返す。
    '''
    if len(v_list) == 0:
        return np.zeros((0, 0), dtype=np.float32)
    out = v_list[0].copy()
    for v in v_list[1:]:
        out += v
    return out

# ----------------------------
# Function
# ----------------------------
def calculate_potentials_lerp(
        x: np.ndarray,
        lst_potentials_timeserise: list,
        lst_dx: list,
    ) -> np.ndarray:
    """
    空間方向のみ線形補間。

    Parameters
    ----------
    x : (X,) or (X,1)
        問い合わせ座標[um]
    lst_potentials_timeserise : [V]
        V shape=(N,M) 電位時系列
    lst_dx : [dx]
        dx shape=(N,) or (N,1) 累積距離[um]

    Returns
    -------
    v : (X,M)
        補間後の電位
    """

    V = np.asarray(lst_potentials_timeserise, dtype=float)   # (N,M)
    dx = np.asarray(lst_dx, dtype=float).ravel()             # (N,)
    xq = np.asarray(x, dtype=float).ravel()                     # (X,)

    N = dx.shape[0]
    xq_clamped = np.clip(xq, dx[0], dx[-1])

    i = np.searchsorted(dx, xq_clamped, side="left")
    i = np.clip(i, 1, N - 1)
    j = i - 1

    x0 = dx[j]
    x1 = dx[i]
    w = ((xq_clamped - x0) / (x1 - x0))[:, None]   # (X,1)

    v0 = V[j, :]   # (X,M)
    v1 = V[i, :]   # (X,M)

    v = (1.0 - w) * v0 + w * v1            # (X,M)
    return v



if __name__ == '__main__':
    from pathlib import Path
    import os
    from neuron import h
    from wrapper_cFiberBuilder import ThioCFiber
    from utility import load_csv_points
    from get_fiber_length import calculate_cumulative_dx_along_fiber, calculate_fiber_lengths

    PROJECT_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = PROJECT_DIR / 'data'
    MODEL_DIR = DATA_DIR / 'thio-model'
    CONFIG_DIR = DATA_DIR / 'config'
    COMSOL_DIR = DATA_DIR / 'comsol'

    @dataclass
    class PotentialsData:
        csv_path: str = ""
        coords: np.ndarray = field(default_factory=lambda: np.empty((0, 3), dtype=float))
        freqs: np.ndarray = field(default_factory=lambda: np.empty((0,), dtype=float))
        V_all: np.ndarray = field(default_factory=lambda: np.empty((0, 0), dtype=np.complex64))
        coord_to_index: dict = field(default_factory=dict)

    os.chdir(MODEL_DIR)
    h.nrn_load_dll(str(MODEL_DIR / 'nrnmech.dll'))
    h.load_file('nrngui.hoc')
    h.xopen('cFiberBuilder.hoc')
    h.load_file('balance.hoc')

    unit_id = 1
    dt_ms = 0.01
    tstop_ms = 100.0
    t_ms = np.arange(0.0, tstop_ms + dt_ms, dt_ms)

    points = load_csv_points(CONFIG_DIR / 'points_along_ra1_fibers.csv')
    cum_lengths = calculate_cumulative_dx_along_fiber(points)
    fiber_lengths = calculate_fiber_lengths(points)

    ra1_e1 = PotentialsData()
    ra1_e1.csv_path = str(COMSOL_DIR / "electrode_square/potentials_along_ra1_fiber_electrodes_1.csv")
    ra1_e1.coords, ra1_e1.freqs, ra1_e1.V_all = load_potentials_csv(ra1_e1.csv_path)
    ra1_e1.coord_to_index = build_coord_to_index(ra1_e1.coords, decimals=6)

    for unit_id, length in fiber_lengths.items():

        fiber = ThioCFiber(
            fiber_diameter=0.8,
            length_um=length,
            temperature=37,
            particle_index=1
        )

        lst_dx_fiber = []
        for n in range(len(fiber)):
            dist = fiber.distance_to_node_center_from_end(n)
            lst_dx_fiber.append(dist)

        v = get_potential_timeseries_along_fiber(unit_id, points, ra1_e1, 1000.0, t_ms, 5.0, 0.0)
        # print(lst_dx_fiber)
        print(v)
        # print(cum_lengths[unit_id])
        v_interporated = calculate_potentials_lerp(lst_dx_fiber, v, cum_lengths[unit_id])
        # print(v_interporated)

    #     per_component.append(v)     # 重畳用

    # v_total = superpose_timeseries(per_component)   # 重畳
    # print('v_total shape:', v_total.shape)  # (P,T)
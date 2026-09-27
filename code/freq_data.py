"""
周波数領域COMSOL電位データの読み込みと時系列変換

COMSOL CSV format (9行 %ヘッダー後):
  x, y, z, [freq, real(V), imag(V)] × K
座標はパスCSVとデータ行が同順で対応する。
"""
import numpy as np
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

V_TO_MV = 1e3
COMSOL_HEADER_ROWS = 9


@dataclass
class FreqPotentials:
    """
    周波数領域の複素電位データ（1電極ペア分）

    coords : (N, 3) 座標 [mm]
    freqs  : (K,) 周波数 [Hz]
    V_complex_mV : (N, K) 複素電位 [mV]
    """
    coords: np.ndarray
    freqs: np.ndarray
    V_complex_mV: np.ndarray
    csv_path: str = ""

    @classmethod
    def from_csv(cls, filepath) -> "FreqPotentials":
        arr = np.genfromtxt(
            filepath, delimiter=',', skip_header=COMSOL_HEADER_ROWS, encoding='utf-8'
        )
        coords = arr[:, 0:3]
        rest = arr[:, 3:]  # [freq, real, imag] × K

        freqs = rest[0, 0::3].copy()
        real = rest[:, 1::3]
        imag = rest[:, 2::3]
        V_complex_mV = (real + 1j * imag) * V_TO_MV

        return cls(
            coords=coords,
            freqs=freqs,
            V_complex_mV=V_complex_mV,
            csv_path=str(filepath),
        )

    @property
    def n_points(self) -> int:
        return self.coords.shape[0]

    def find_freq_index(self, freq_hz: float, atol: float = 1e-6) -> Optional[int]:
        """対象周波数のインデックス（見つからなければNone）"""
        diffs = np.abs(self.freqs - freq_hz)
        idx = int(np.argmin(diffs))
        return idx if diffs[idx] < atol else None


def complex_to_timeseries(
    V_complex_mV: np.ndarray,
    freq_hz: float,
    amp_mA: float,
    phase_rad: float,
    t_ms: np.ndarray,
) -> np.ndarray:
    """
    複素電位 (P,) を実時間領域の時系列 (P, T) に変換

    V(t) = Re[ amp * V_complex * exp(j(2πf t + φ)) ]
    """
    t_s = np.asarray(t_ms, dtype=float) * 1e-3
    ejwt = np.exp(1j * (2.0 * np.pi * freq_hz * t_s + phase_rad))  # (T,)
    v = np.real((amp_mA * V_complex_mV)[:, None] * ejwt[None, :])  # (P, T)
    return v.astype(np.float64)


def get_timeseries_at_points(
    pot: FreqPotentials,
    point_indices: np.ndarray,
    freq_hz: float,
    amp_mA: float,
    phase_rad: float,
    t_ms: np.ndarray,
) -> np.ndarray:
    """
    指定行インデックス（=COMSOL点）の電位時系列を取得

    Returns
    -------
    V_timeseries : (P, T) [mV]
    """
    if len(point_indices) == 0:
        return np.zeros((0, len(t_ms)), dtype=np.float64)

    freq_idx = pot.find_freq_index(freq_hz)
    if freq_idx is None:
        raise ValueError(
            f"Frequency {freq_hz} Hz not found. Available: {pot.freqs.tolist()}"
        )

    V_complex = pot.V_complex_mV[point_indices, freq_idx]  # (P,)
    return complex_to_timeseries(V_complex, freq_hz, amp_mA, phase_rad, t_ms)
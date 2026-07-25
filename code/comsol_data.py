"""
comsol_data.py

COMSOL電位データの読み込みと管理
- 周波数領域（複素数）と時間領域（実数時系列）の両方に対応
- 複数周波数を含む単一ファイルに対応
"""
import re
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Union
from pathlib import Path
from enum import Enum, auto

V_TO_MV = 1e3
MM_TO_UM = 1e3


class DomainType(Enum):
    """解析領域の種類"""
    FREQUENCY = auto()  # 周波数領域（複素数）
    TIME = auto()       # 時間領域（実数時系列）


@dataclass
class PotentialsData:
    """
    COMSOLの電位分布データを保持するコンテナ
    
    周波数領域の場合:
        - freqs: (K,) 周波数[Hz]
        - V_complex_mV: (N, K) 複素電位[mV]
        - t_ms, V_timeseries_mV: None
    
    時間領域の場合:
        - t_ms: (T,) 時間[ms]
        - V_timeseries_mV: (N, T) 実電位[mV]
        - freqs, V_complex_mV: None
    """
    csv_path: str = ""
    domain_type: DomainType = DomainType.FREQUENCY
    coords: np.ndarray = field(default_factory=lambda: np.empty((0, 3), dtype=float))
    coord_to_index: Dict[tuple, int] = field(default_factory=dict)
    
    # 周波数領域用
    freqs: Optional[np.ndarray] = None          # (K,)
    V_complex_mV: Optional[np.ndarray] = None   # (N, K) complex
    
    # 時間領域用
    t_ms: Optional[np.ndarray] = None           # (T,)
    V_timeseries_mV: Optional[np.ndarray] = None  # (N, T) float
    
    @classmethod
    def from_frequency_csv(cls, filepath: str, decimals: int = 6) -> "PotentialsData":
        """周波数領域CSVから読み込み（単一周波数形式）"""
        coords, freqs, V_mV = load_potentials_csv_frequency(filepath)
        coord_to_index = build_coord_to_index(coords, decimals)
        return cls(
            csv_path=str(filepath),
            domain_type=DomainType.FREQUENCY,
            coords=coords,
            coord_to_index=coord_to_index,
            freqs=freqs,
            V_complex_mV=V_mV,
        )
    
    @classmethod
    def from_time_csv(cls, filepath: str, dt_ms: float, decimals: int = 6) -> "PotentialsData":
        """時間領域CSVから読み込み"""
        coords, t_ms, V_mV = load_potentials_csv_time(filepath, dt_ms)
        coord_to_index = build_coord_to_index(coords, decimals)
        return cls(
            csv_path=str(filepath),
            domain_type=DomainType.TIME,
            coords=coords,
            coord_to_index=coord_to_index,
            t_ms=t_ms,
            V_timeseries_mV=V_mV,
        )
    
    def get_available_freqs(self) -> Optional[np.ndarray]:
        """利用可能な周波数一覧（周波数領域の場合のみ）"""
        if self.domain_type == DomainType.FREQUENCY and self.freqs is not None:
            return self.freqs.copy()
        return None
    
    def get_time_vector(self) -> Optional[np.ndarray]:
        """時間ベクトル（時間領域の場合のみ）"""
        if self.domain_type == DomainType.TIME and self.t_ms is not None:
            return self.t_ms.copy()
        return None
    
    def get_potential_at_frequency(self, freq_hz: float) -> Optional[np.ndarray]:
        """
        指定周波数の複素電位を取得
        
        Parameters
        ----------
        freq_hz : float
            取得する周波数 [Hz]
        
        Returns
        -------
        V_complex : (N,) complex array [mV], or None if not found
        """
        if self.domain_type != DomainType.FREQUENCY or self.freqs is None:
            return None
        
        # 周波数インデックスを検索
        idx = np.where(np.isclose(self.freqs, freq_hz, rtol=1e-6))[0]
        if len(idx) == 0:
            return None
        
        return self.V_complex_mV[:, idx[0]]
    
    @property
    def n_points(self) -> int:
        """座標点数"""
        return self.coords.shape[0]
    
    @property
    def n_frequencies(self) -> int:
        """周波数の数（周波数領域の場合のみ）"""
        if self.freqs is not None:
            return len(self.freqs)
        return 0


@dataclass
class MultiFreqPotentialsData:
    """
    複数周波数を含むCOMSOLファイルから読み込んだ電位データ
    
    用途: 電極ごとに全周波数データを保持し、
          シミュレーション時に必要な周波数を抽出
    
    Attributes
    ----------
    csv_path : str
        読み込み元ファイルパス
    coords : np.ndarray
        (N, 3) 座標 [mm]
    coord_to_index : Dict[tuple, int]
        座標→インデックスの辞書
    frequencies : List[float]
        含まれる周波数のリスト [Hz]（ソート済み）
    potentials : Dict[float, np.ndarray]
        {freq_hz: (N,) complex} 各周波数の複素電位 [mV]
    """
    csv_path: str = ""
    coords: np.ndarray = field(default_factory=lambda: np.empty((0, 3), dtype=float))
    coord_to_index: Dict[tuple, int] = field(default_factory=dict)
    frequencies: List[float] = field(default_factory=list)
    potentials: Dict[float, np.ndarray] = field(default_factory=dict)
    
    @classmethod
    def from_multi_frequency_csv(
        cls, 
        filepath: Union[str, Path], 
        skip_header: int = 9,
        decimals: int = 6,
    ) -> "MultiFreqPotentialsData":
        """
        複数周波数を含むCOMSOL CSVを読み込む
        """
        import pandas as pd
        
        filepath = Path(filepath)
        
        # ヘッダーから周波数リストを抽出
        frequencies = _parse_header_frequencies(filepath)
        
        # pandas で高速読み込み
        df = pd.read_csv(filepath, comment='%', header=None, skiprows=skip_header)
        arr = df.values
        
        coords = arr[:, 0:3]
        rest = arr[:, 3:]
        
        # 周波数ごとに電位を抽出
        K = rest.shape[1] // 3
        potentials = {}
        
        for k in range(K):
            freq = rest[0, k * 3]
            real_v = rest[:, k * 3 + 1]
            imag_v = rest[:, k * 3 + 2]
            V_complex_mV = (real_v + 1j * imag_v) * V_TO_MV
            potentials[freq] = V_complex_mV
        
        if not frequencies:
            frequencies = sorted(potentials.keys())
        
        coord_to_index = build_coord_to_index(coords, decimals)
        
        return cls(
            csv_path=str(filepath),
            coords=coords,
            coord_to_index=coord_to_index,
            frequencies=frequencies,
            potentials=potentials,
        )
    
    def get_potential_at_frequency(self, freq_hz: float) -> np.ndarray:
        """
        指定周波数の複素電位を取得
        
        Parameters
        ----------
        freq_hz : float
            取得する周波数 [Hz]
        
        Returns
        -------
        V_complex : (N,) complex array [mV]
        
        Raises
        ------
        ValueError
            指定周波数が存在しない場合
        """
        # 完全一致を試行
        if freq_hz in self.potentials:
            return self.potentials[freq_hz]
        
        # 近似一致を試行
        for f in self.potentials.keys():
            if np.isclose(f, freq_hz, rtol=1e-6):
                return self.potentials[f]
        
        available = sorted(self.potentials.keys())
        raise ValueError(
            f"Frequency {freq_hz} Hz not found. "
            f"Available: {available[:5]}... ({len(available)} total)"
        )
    
    def to_potentials_data(self, freq_hz: float, decimals: int = 6) -> PotentialsData:
        """
        指定周波数のPotentialsDataを生成（既存コードとの互換性用）
        
        Parameters
        ----------
        freq_hz : float
            抽出する周波数 [Hz]
        decimals : int
            座標丸め桁数
        
        Returns
        -------
        PotentialsData
            単一周波数のPotentialsData
        """
        V_complex = self.get_potential_at_frequency(freq_hz)
        
        return PotentialsData(
            csv_path=self.csv_path,
            domain_type=DomainType.FREQUENCY,
            coords=self.coords.copy(),
            coord_to_index=self.coord_to_index.copy(),
            freqs=np.array([freq_hz]),
            V_complex_mV=V_complex.reshape(-1, 1),
        )
    
    @property
    def n_points(self) -> int:
        """座標点数"""
        return self.coords.shape[0]
    
    @property
    def n_frequencies(self) -> int:
        """周波数の数"""
        return len(self.frequencies)
    
    def get_available_freqs(self) -> List[float]:
        """利用可能な周波数一覧"""
        return self.frequencies.copy()


def _parse_header_frequencies(filepath: Path) -> List[float]:
    """
    ヘッダー行から周波数リストを抽出
    
    ヘッダー例:
    % x,y,z,freq (Hz) @ freq=1000, amp01=1, amp02=0,...
    """
    frequencies = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('%'):
                # "freq=数値" のパターンを抽出
                matches = re.findall(r'freq=(\d+)', line)
                for m in matches:
                    freq = float(m)
                    if freq not in frequencies:
                        frequencies.append(freq)
                break  # 最初のコメント行のみ処理
    
    return sorted(frequencies)


@dataclass
class FiberPathData:
    """
    神経線維のパス情報（COMSOL座標系）
    
    points: (N, 4+) [unit_id, x, y, z, ...]
    """
    points: np.ndarray
    interval_mm: float = 0.1
    _cumulative_dx_um: Dict[int, np.ndarray] = field(default_factory=dict, repr=False)
    _fiber_lengths_um: Dict[int, float] = field(default_factory=dict, repr=False)
    _point_indices: Dict[int, np.ndarray] = field(default_factory=dict, repr=False)
    
    def __post_init__(self):
        self._compute_lengths()
        self._build_point_indices()
    
    def _compute_lengths(self):
        """累積距離と線維長を計算"""
        unit_ids = np.unique(self.points[:, 0]).astype(int)
        
        for uid in unit_ids:
            uid = int(uid)
            group = self.points[self.points[:, 0] == uid]
            n_points = len(group)
            
            if n_points == 0:
                self._cumulative_dx_um[uid] = np.array([], dtype=float)
                self._fiber_lengths_um[uid] = float("nan")
                continue
            if n_points == 1:
                self._cumulative_dx_um[uid] = np.array([0.0], dtype=float)
                self._fiber_lengths_um[uid] = 0.0
                continue
            
            # 等間隔 + 最終点のみ実距離で補正
            arr_dx = np.arange(n_points, dtype=float) * self.interval_mm
            dx_last = np.linalg.norm(group[-1, 1:4] - group[-2, 1:4])
            arr_dx[-1] = arr_dx[-2] + dx_last
            
            self._cumulative_dx_um[uid] = arr_dx * MM_TO_UM
            self._fiber_lengths_um[uid] = float(arr_dx[-1] * MM_TO_UM)
    
    def _build_point_indices(self):
        """各unit_idの行インデックスを記録"""
        unit_ids = np.unique(self.points[:, 0]).astype(int)
        for uid in unit_ids:
            uid = int(uid)
            mask = self.points[:, 0] == uid
            self._point_indices[uid] = np.where(mask)[0]
    
    def get_unit_ids(self) -> np.ndarray:
        """含まれるunit_id一覧"""
        return np.array(sorted(self._fiber_lengths_um.keys()))
    
    def get_cumulative_dx_um(self, unit_id: int) -> np.ndarray:
        """指定unit_idの累積距離[um]"""
        return self._cumulative_dx_um.get(unit_id, np.array([]))
    
    def get_fiber_length_um(self, unit_id: int) -> float:
        """指定unit_idの線維長[um]"""
        return self._fiber_lengths_um.get(unit_id, float("nan"))
    
    def get_all_fiber_lengths_um(self) -> Dict[int, float]:
        """全unit_idの線維長[um]"""
        return self._fiber_lengths_um.copy()
    
    def get_xyz_coords(self, unit_id: int) -> np.ndarray:
        """指定unit_idの3D座標 (P, 3)"""
        indices = self._point_indices.get(unit_id, np.array([]))
        if len(indices) == 0:
            return np.empty((0, 3), dtype=float)
        return self.points[indices, 1:4].copy()
    
    def interpolate_1d_to_3d(
        self,
        unit_id: int,
        positions_1d_um: np.ndarray,
    ) -> np.ndarray:
        """
        1D軸索位置[um]から3D COMSOL座標への逆変換（線形補間）
        
        Parameters
        ----------
        unit_id : int
            対象unit_id
        positions_1d_um : (M,) 
            軸索上の1D位置[um]
        
        Returns
        -------
        coords_3d : (M, 3)
            対応する3D座標
        """
        cumulative_dx = self.get_cumulative_dx_um(unit_id)
        xyz = self.get_xyz_coords(unit_id)
        
        if len(cumulative_dx) == 0 or len(xyz) == 0:
            return np.full((len(positions_1d_um), 3), np.nan)
        
        positions_1d = np.asarray(positions_1d_um, dtype=float).ravel()
        
        # クランプして補間
        pos_clamped = np.clip(positions_1d, cumulative_dx[0], cumulative_dx[-1])
        
        # 各座標軸で線形補間
        coords_3d = np.zeros((len(positions_1d), 3), dtype=float)
        for axis in range(3):
            coords_3d[:, axis] = np.interp(pos_clamped, cumulative_dx, xyz[:, axis])
        
        return coords_3d


# =============================================================================
# I/O Functions
# =============================================================================

def load_csv_points(filepath) -> np.ndarray:
    """
    神経パスの位置情報CSVを読み込む
    
    Returns
    -------
    np.ndarray : (N, 4+) [unit_id, x, y, z, ...]
    """
    data = np.loadtxt(filepath, delimiter=',', encoding="utf-8_sig")
    return data


def load_potentials_csv_frequency(filepath: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    COMSOL周波数領域の電位CSVを読み込む（単一周波数または複数周波数）
    
    CSV format (9行ヘッダ後):
      [x, y, z, f1, R1, I1, f2, R2, I2, ..., fK, RK, IK]
    
    Returns
    -------
    coords : (N, 3) 座標
    freqs : (K,) 周波数[Hz]
    V_mV : (N, K) 複素電位[mV]
    """
    arr = np.genfromtxt(filepath, delimiter=',', skip_header=9, encoding='utf-8')
    coords = arr[:, 0:3]
    rest = arr[:, 3:]
    
    K = rest.shape[1] // 3
    freqs = rest[0, 0::3].copy()
    R = rest[:, 1::3]
    I = rest[:, 2::3]
    V_mV = (R + 1j * I) * V_TO_MV
    
    return coords, freqs, V_mV


def load_potentials_csv_time(
    filepath: str, 
    dt_ms: float,
    skip_header: int = 9,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    COMSOL時間領域の電位CSVを読み込む
    
    CSV format (skip_header行後):
      [x, y, z, V(t=0), V(t=dt), V(t=2dt), ...]
    
    Parameters
    ----------
    filepath : str
        CSVファイルパス
    dt_ms : float
        時間ステップ[ms]（COMSOLの出力間隔）
    skip_header : int
        スキップするヘッダ行数
    
    Returns
    -------
    coords : (N, 3) 座標
    t_ms : (T,) 時間ベクトル[ms]
    V_mV : (N, T) 電位[mV]
    """
    arr = np.genfromtxt(filepath, delimiter=',', skip_header=skip_header, encoding='utf-8')
    coords = arr[:, 0:3]
    V = arr[:, 3:]  # (N, T)
    
    T = V.shape[1]
    t_ms = np.arange(T) * dt_ms
    V_mV = V * V_TO_MV
    
    return coords, t_ms, V_mV


def build_coord_to_index(coords: np.ndarray, decimals: int = 6) -> Dict[tuple, int]:
    """座標→インデックスの辞書を構築"""
    coord_to_index = {}
    for i in range(coords.shape[0]):
        key = coord_key(coords[i], decimals)
        coord_to_index[key] = i
    return coord_to_index


def coord_key(xyz: np.ndarray, decimals: int = 6) -> tuple:
    """座標を丸めてタプル化（辞書キー用）"""
    return tuple(round(float(v), decimals) for v in xyz)


# =============================================================================
# Test / Example
# =============================================================================

def main():
    """テスト・動作確認用"""
    from pathlib import Path
    
    # パス設定
    PROJECT_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = PROJECT_DIR / "data"
    CONFIG_DIR = DATA_DIR / "config"
    COMSOL_DIR_FREQ = DATA_DIR / "comsol" / "electrode_square"
    COMSOL_DIR_TIME = DATA_DIR / "comsol" / "waveform_pulse"
    
    print("=" * 60)
    print("Test: MultiFreqPotentialsData")
    print("=" * 60)
    
    # 複数周波数データの読み込みテスト
    try:
        multi_data = MultiFreqPotentialsData.from_multi_frequency_csv(
            COMSOL_DIR_FREQ / "potentials_along_ra1_fiber_electrodes_1.csv"
        )
        
        print(f"File: {multi_data.csv_path}")
        print(f"Number of points: {multi_data.n_points}")
        print(f"Number of frequencies: {multi_data.n_frequencies}")
        print(f"Frequencies (first 10): {multi_data.frequencies[:10]}")
        print(f"Frequencies (last 5): {multi_data.frequencies[-5:]}")
        
        # 特定周波数の電位を取得
        test_freq = 1000.0
        V = multi_data.get_potential_at_frequency(test_freq)
        print(f"\nPotential at {test_freq} Hz:")
        print(f"  Shape: {V.shape}")
        print(f"  Range: [{V.real.min():.3f}, {V.real.max():.3f}] mV (real)")
        print(f"  Range: [{V.imag.min():.3f}, {V.imag.max():.3f}] mV (imag)")
        
        # PotentialsDataへの変換
        pot_data = multi_data.to_potentials_data(test_freq)
        print(f"\nConverted to PotentialsData:")
        print(f"  n_points: {pot_data.n_points}")
        print(f"  freqs: {pot_data.freqs}")
        
    except FileNotFoundError as e:
        print(f"File not found: {e}")
        print("Skipping MultiFreqPotentialsData test")
    
    print("\n" + "=" * 60)
    print("Test: PotentialsData (Time Domain)")
    print("=" * 60)
    
    # 時間領域データの読み込みテスト
    try:
        dt_ms = 0.01  # 10 us
        time_data = PotentialsData.from_time_csv(
            COMSOL_DIR_TIME / "potentials_along_enf_fiber_AmpRatio_1.csv",
            dt_ms=dt_ms,
        )
        
        print(f"File: {time_data.csv_path}")
        print(f"Number of points: {time_data.n_points}")
        print(f"Domain type: {time_data.domain_type}")
        
        # 時間情報
        t_ms = time_data.get_time_vector()
        print(f"\nTime information:")
        print(f"  Number of time steps: {len(t_ms)}")
        print(f"  Time step (dt): {dt_ms} ms ({dt_ms * 1000:.1f} us)")
        print(f"  Time range: [{t_ms[0]:.3f}, {t_ms[-1]:.3f}] ms")
        print(f"  Total duration: {t_ms[-1] - t_ms[0]:.3f} ms")
        
        # 電位情報
        V = time_data.V_timeseries_mV
        print(f"\nPotential information:")
        print(f"  Shape: {V.shape} (points, time steps)")
        print(f"  Range: [{V.min():.3f}, {V.max():.3f}] mV")
        print(f"  Mean: {V.mean():.3f} mV")
        
    except FileNotFoundError as e:
        print(f"File not found: {e}")
        print("Skipping Time Domain PotentialsData test")
    
    print("\n" + "=" * 60)
    print("Test: FiberPathData")
    print("=" * 60)
    
    try:
        ra1_path = FiberPathData(
            points=load_csv_points(CONFIG_DIR / "points_along_ra1_fibers.csv"),
            interval_mm=0.1,
        )
        
        unit_ids = ra1_path.get_unit_ids()
        print(f"Number of units: {len(unit_ids)}")
        print(f"Unit IDs (first 10): {unit_ids[:10]}")
        
        # 最初のunitの情報
        uid = unit_ids[0]
        print(f"\nUnit {uid}:")
        print(f"  Length: {ra1_path.get_fiber_length_um(uid):.1f} um")
        print(f"  Cumulative dx: {ra1_path.get_cumulative_dx_um(uid)[:5]} um (first 5)")
        
    except FileNotFoundError as e:
        print(f"File not found: {e}")
        print("Skipping FiberPathData test")
    
    print("\n=== All tests completed ===")


if __name__ == "__main__":
    main()
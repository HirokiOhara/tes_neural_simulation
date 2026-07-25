import numpy as np
from typing import Dict

MM_TO_UM = 1e3

def calculate_cumulative_dx_along_fiber(points: np.ndarray, interval: float = 0.1) -> Dict[int, np.ndarray]:
    '''
    Returns
    -------
    dict[int, np.ndarray]
        {Unit ID: 累積距離配列(um)}
    '''
    unit_ids = np.unique(points[:, 0]).astype(int)
    results: Dict[int, np.ndarray] = {}

    for uid in unit_ids:
        uid = int(uid)
        group = points[points[:, 0] == uid]
        n_points = len(group)

        if n_points == 0:
            results[uid] = np.array([], dtype=float)
            continue
        if n_points == 1:
            results[uid] = np.array([0.0], dtype=float)
            continue

        arr_dx = np.arange(n_points, dtype=float) * float(interval)
        dx_last = np.linalg.norm(group[-1, 1:4] - group[-2, 1:4])
        arr_dx[-1] = arr_dx[-2] + float(dx_last)

        results[uid] = arr_dx * MM_TO_UM

    return results


def calculate_fiber_lengths(points: np.ndarray, interval: float = 0.1) -> Dict[int, float]:
    '''
    Returns
    -------
    dict[int, float]
        {Unit ID: 線維長(um)}  (=累積距離の最後の値)
    '''
    cum = calculate_cumulative_dx_along_fiber(points, interval=interval)
    lengths: Dict[int, float] = {}
    for uid, dx in cum.items():
        if len(dx) > 0:
            lengths[uid] = float(dx[-1])
        else:
            lengths[uid] = float("nan")

    return lengths


if __name__ == '__main__':

    # 初期化
    from pathlib import Path
    from utility import load_csv_points

    PROJECT_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = PROJECT_DIR / 'data'
    MODEL_DIR = DATA_DIR / 'thio-model'
    CONFIG_DIR = DATA_DIR / 'config'

    points = load_csv_points(CONFIG_DIR / 'points_along_line.csv')

    cum_lengths = calculate_cumulative_dx_along_fiber(points)
    lengths = calculate_fiber_lengths(points)

    print(cum_lengths)
    print(lengths)


# result_io.py
"""
モデル非依存のシミュレーション結果CSV出力

resultの共通形式:
{
    "unit_id": int,
    "fiber_length_um": float,
    "point_positions_um": ndarray (n_point,),    # 1D累積距離[um]
    "point_coords_mm": ndarray (n_point, 3),     # 3D座標[mm]
    "v_membrane": ndarray (n_comp, n_time),
    "ap_count": int,
    "spike_times_ms": ndarray,
}
"""
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd


def make_result_summary(result: Dict[str, Any]) -> Dict[str, Any]:
    """1線維のsummary項目（軽量、gather用）。"""
    return {
        "unit_id": int(result["unit_id"]),
        "fiber_length_um": float(result["fiber_length_um"]),
        "ap_count": int(result["ap_count"]),
        "spike_times_ms": np.asarray(result["spike_times_ms"], dtype=np.float64),
    }


def save_results_summary(
    results: Dict[int, Dict[str, Any]],
    output_dir: Path,
    prefix: str = "result",
) -> Path:
    """線維ごとのsummaryを1CSVへ保存する。"""
    rows = []
    for unit_id in sorted(results):
        s = make_result_summary(results[unit_id])
        rows.append({
            "unit_id": s["unit_id"],
            "fiber_length_um": s["fiber_length_um"],
            "ap_count": s["ap_count"],
            "spike_times_ms": str(s["spike_times_ms"].tolist()),
        })

    filepath = Path(output_dir) / f"{prefix}_summary.csv"
    filepath.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        rows, columns=["unit_id", "fiber_length_um", "ap_count", "spike_times_ms"]
    ).to_csv(filepath, index=False)
    print(f"Saved summary: {filepath} ({len(rows)} fibers)")
    return filepath


# ---- 膜電位（1本ごとにストリーミング追記）----

def open_membrane_writer(output_dir: Path, prefix: str, n_time: int) -> Path:
    """膜電位CSVを新規作成しヘッダを書く。"""
    filepath = Path(output_dir) / f"{prefix}_membrane.csv"
    filepath.parent.mkdir(parents=True, exist_ok=True)
    header = (
        ["unit_id", "point_index", "position_um"]
        + [f"V_t{i}" for i in range(n_time)]
    )
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        f.write(",".join(header) + "\n")
    return filepath


def append_one_fiber_membrane(filepath: Path, result: Dict[str, Any]) -> None:
    """1線維分の膜電位をCSVへ追記する（メモリに溜めない）。"""
    unit_id = int(result["unit_id"])
    positions = np.asarray(result["point_positions_um"], dtype=np.float64)
    v = np.asarray(result["v_membrane"], dtype=np.float64)

    with open(filepath, "a", encoding="utf-8", newline="") as f:
        for k in range(len(positions)):
            meta = f"{unit_id},{k},{positions[k]:.10g}"
            volt = ",".join(f"{x:.7g}" for x in v[k, :])
            f.write(f"{meta},{volt}\n")


# ---- 座標（1本ごとにストリーミング追記）----

def open_coords_writer(output_dir: Path, prefix: str) -> Path:
    """座標CSVを新規作成しヘッダを書く。"""
    filepath = Path(output_dir) / f"{prefix}_coords.csv"
    filepath.parent.mkdir(parents=True, exist_ok=True)
    header = ["unit_id", "point_index", "position_um", "x_mm", "y_mm", "z_mm"]
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        f.write(",".join(header) + "\n")
    return filepath


def append_one_fiber_coords(filepath: Path, result: Dict[str, Any]) -> None:
    """1線維分の点座標をCSVへ追記する。"""
    unit_id = int(result["unit_id"])
    positions = np.asarray(result["point_positions_um"], dtype=np.float64)
    coords = np.asarray(result["point_coords_mm"], dtype=np.float64)

    with open(filepath, "a", encoding="utf-8", newline="") as f:
        for k in range(len(positions)):
            f.write(
                f"{unit_id},{k},{positions[k]:.10g},"
                f"{coords[k, 0]:.10g},{coords[k, 1]:.10g},{coords[k, 2]:.10g}\n"
            )


def extract_summary_results(
    results: Dict[int, Dict[str, Any]],
) -> Dict[int, Dict[str, Any]]:
    """MPI gather用にsummaryだけを取り出す。"""
    return {int(uid): make_result_summary(r) for uid, r in results.items()}
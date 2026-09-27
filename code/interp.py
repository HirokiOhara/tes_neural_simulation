import numpy as np
from typing import List


def interpolate_to_axon_nodes(
    V_at_comsol_points: np.ndarray,
    comsol_cumulative_dx_um: np.ndarray,
    axon_node_positions_um: np.ndarray,
) -> np.ndarray:
    """
    COMSOL点の電位 (P, T) を軸索ノード位置 (N,) に線形補間 → (N, T)
    """
    V = np.asarray(V_at_comsol_points, dtype=float)
    dx = np.asarray(comsol_cumulative_dx_um, dtype=float).ravel()
    xq = np.asarray(axon_node_positions_um, dtype=float).ravel()

    if V.shape[0] != len(dx):
        raise ValueError(f"V shape[0]={V.shape[0]} != dx length={len(dx)}")

    xq_clamped = np.clip(xq, dx[0], dx[-1])

    i = np.searchsorted(dx, xq_clamped, side="left")
    i = np.clip(i, 1, len(dx) - 1)
    j = i - 1

    x0, x1 = dx[j], dx[i]
    denom = x1 - x0
    denom[denom == 0] = 1.0
    w = ((xq_clamped - x0) / denom)[:, None]  # (N, 1)

    return (1.0 - w) * V[j, :] + w * V[i, :]  # (N, T)


def superpose_potentials(potential_list: List[np.ndarray]) -> np.ndarray:
    """複数の電位時系列を重畳"""
    if len(potential_list) == 0:
        return np.zeros((0, 0), dtype=np.float64)
    result = potential_list[0].astype(np.float64).copy()
    for v in potential_list[1:]:
        result += v
    return result
import os
from pathlib import Path
import datetime
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from neuron import h

from wrapper_MRGaxon import MRGaxon
from utility import load_csv_points
from get_fiber_length import calculate_cumulative_dx_along_fiber, calculate_fiber_lengths
from get_potential_along_fiber import (
    load_potentials_csv_by_freq,
    list_freqs_in_potentials_csv,
    get_potential_timeseries_along_fiber,
    calculate_potentials_lerp,
    superpose_timeseries,
    load_potentials_csv,
    build_coord_to_index,
)
from simulate_mrg_model import simulate_mrg_fiber



def build_fourier_lookup(fourier_csv_path: str):
    df = pd.read_csv(fourier_csv_path)
    return {float(r["frequency_Hz"]): (float(r["amplitude_mA"]), float(r["phase_rad"]))
            for _, r in df.iterrows()}

def freqs_round_robin(all_freqs, n_pairs=4):
    # e1: idx%4==0, e2:1, e3:2, e4:3
    out = [[] for _ in range(n_pairs)]
    for k, f in enumerate(all_freqs):
        out[k % n_pairs].append(float(f))
    return out

def get_pair_timeseries_singlefreq(
    unit_id,
    points,
    pair_data,
    t_ms,
    freq_hz: float,
    amp_mA: float,
    theta_rad: float,
):
    return get_potential_timeseries_along_fiber(
        unit_id, points, pair_data, float(freq_hz), t_ms, float(amp_mA), float(theta_rad)
    )

def get_pair_timeseries_roundrobin(
    unit_id,
    points,
    pair_data,          # ra1_e1等
    t_ms,
    freqs_assigned,     # そのpairに割当てられた周波数リスト
    fourier_lookup,
):
    """
    そのpairに割当てられた複数周波数について
    get_potential_timeseries_along_fiber(...) を周波数ごとに呼び、
    足し合わせて (P,T) を返す。
    """
    per_freq = []
    for f in freqs_assigned:
        if f not in fourier_lookup:
            continue
        amp, theta = fourier_lookup[f]
        amp *= 20
        v = get_potential_timeseries_along_fiber(
            unit_id, points, pair_data, f, t_ms, amp, theta
        )
        per_freq.append(v)
    return superpose_timeseries(per_freq)




PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
MODEL_DIR = DATA_DIR / "mrg-model"
CONFIG_DIR = DATA_DIR / "config"
COMSOL_DIR = DATA_DIR / "comsol"

os.chdir(MODEL_DIR)
h.nrn_load_dll(str(MODEL_DIR / "nrnmech.dll"))
h.load_file("nrngui.hoc")
h.xopen("MRGaxonBuilder.hoc")

@dataclass
class PotentialsData:
    csv_path: str = ""
    coords: np.ndarray = field(default_factory=lambda: np.empty((0, 3), dtype=float))
    freqs: np.ndarray = field(default_factory=lambda: np.empty((0,), dtype=float))
    V_all: np.ndarray = field(default_factory=lambda: np.empty((0, 0), dtype=np.complex64))
    coord_to_index: dict = field(default_factory=dict)

# --- sim settings ---
dt_ms = 0.01
tstop_ms = 100.0
t_ms = np.arange(0.0, tstop_ms + dt_ms, dt_ms)

# --- unit_id -> fiber type (RA1/RA2/SA1) を決めるために数をカウント ---
fiber_info = pd.read_csv(CONFIG_DIR / "fiber_info_summary.csv")
counts = fiber_info["ReceptorType"].value_counts()
n_ra1 = int(counts.get("RA1", 0))
n_ra2 = int(counts.get("RA2", 0))
n_sa1 = int(counts.get("SA1", 0))

dt_now = datetime.datetime.now()
print(dt_now)

ra1_e1 = PotentialsData()
ra1_e1.csv_path = str(COMSOL_DIR / "electrode_octagon/potentials_along_ra1_fiber_electrodes_4.csv")
ra1_e1.coords, ra1_e1.freqs, ra1_e1.V_all = load_potentials_csv(ra1_e1.csv_path)
ra1_e1.coord_to_index = build_coord_to_index(ra1_e1.coords, decimals=6)
dt_now = datetime.datetime.now()
print(dt_now)

ra1_e2 = PotentialsData()
ra1_e2.csv_path = str(COMSOL_DIR / "electrode_octagon/potentials_along_ra1_fiber_electrodes_10.csv")
ra1_e2.coords, ra1_e2.freqs, ra1_e2.V_all = load_potentials_csv(ra1_e2.csv_path)
ra1_e2.coord_to_index = build_coord_to_index(ra1_e2.coords, decimals=6)
dt_now = datetime.datetime.now()
print(dt_now)

ra1_e3 = PotentialsData()
ra1_e3.csv_path = str(COMSOL_DIR / "electrode_octagon/potentials_along_ra1_fiber_electrodes_16.csv")
ra1_e3.coords, ra1_e3.freqs, ra1_e3.V_all = load_potentials_csv(ra1_e3.csv_path)
ra1_e3.coord_to_index = build_coord_to_index(ra1_e3.coords, decimals=6)
dt_now = datetime.datetime.now()
print(dt_now)

ra1_e4 = PotentialsData()
ra1_e4.csv_path = str(COMSOL_DIR / "electrode_octagon/potentials_along_ra1_fiber_electrodes_21.csv")
ra1_e4.coords, ra1_e4.freqs, ra1_e4.V_all = load_potentials_csv(ra1_e4.csv_path)
ra1_e4.coord_to_index = build_coord_to_index(ra1_e4.coords, decimals=6)
dt_now = datetime.datetime.now()
print(dt_now)

ra1_pairs = [ra1_e1, ra1_e2, ra1_e3, ra1_e4]

# --- round-robin側 ---
fourier_lookup = build_fourier_lookup(CONFIG_DIR / "fourier_components.csv")
all_freqs = np.arange(1000.0, 10000.0 + 100.0, 100.0)
assigned_rr = freqs_round_robin(all_freqs, n_pairs=len(ra1_pairs))

# --- all_same側（単一周波数・合計振幅を指定） ---
f0_hz = 1000.0
A_total_mA = 20.0      # “4電極を足した合計”として欲しい振幅
theta0_rad = 0.0        # 全電極同位相
A_each_mA = A_total_mA / len(ra1_pairs)


# for RA1
points = load_csv_points(CONFIG_DIR / "points_along_ra1_fibers.csv")
cum_lengths = calculate_cumulative_dx_along_fiber(points)
fiber_lengths = calculate_fiber_lengths(points)

target_unit_ids = {218, 23}

for unit_id, length in fiber_lengths.items():
    if unit_id not in target_unit_ids:
        continue

    fiber = MRGaxon(8.7, length_um=length)

    lst_dx_fiber = [
        fiber.distance_to_node_center_from_end(i) for i in range(fiber.n_compartments)
    ]

    results = {}

    # ========= (A) round-robin =========
    per_component_rr = []
    for i, pair in enumerate(ra1_pairs):
        v_pair = get_pair_timeseries_roundrobin(
            unit_id=unit_id,
            points=points,
            pair_data=pair,
            t_ms=t_ms,
            freqs_assigned=assigned_rr[i],
            fourier_lookup=fourier_lookup,
        )
        per_component_rr.append(v_pair)

    v_total_rr = superpose_timeseries(per_component_rr)
    v_interp_rr = calculate_potentials_lerp(lst_dx_fiber, v_total_rr, cum_lengths[unit_id])
    v_matrix_rr, ap_count_rr, spike_times_rr = simulate_mrg_fiber(
        fiber, v_interp_rr, dt_ms, tstop_ms, lst_dx_fiber
    )
    results["round_robin"] = (v_interp_rr, v_matrix_rr, ap_count_rr, spike_times_rr)
    np.savetxt(DATA_DIR / f"temp/vm_round_robin_UnitId_{unit_id}.csv", v_matrix_rr, delimiter=",")

    print(f"[round_robin] unit_id={unit_id} ap_count={ap_count_rr} "
          f"v_interp min={v_interp_rr.min():.4f} max={v_interp_rr.max():.4f}")

    # ========= (B) all_same: 全電極同一f0、合計振幅=A_total =========
    # per_component_all = []
    # for pair in ra1_pairs:
    #     v_pair = get_pair_timeseries_singlefreq(
    #         unit_id=unit_id,
    #         points=points,
    #         pair_data=pair,
    #         t_ms=t_ms,
    #         freq_hz=f0_hz,
    #         amp_mA=A_each_mA,      # ここが「合計振幅固定」の肝
    #         theta_rad=theta0_rad,
    #     )
    #     per_component_all.append(v_pair)

    # v_total_all = superpose_timeseries(per_component_all)
    # v_interp_all = calculate_potentials_lerp(lst_dx_fiber, v_total_all, cum_lengths[unit_id])
    # v_matrix_all, ap_count_all, spike_times_all = simulate_mrg_fiber(
    #     fiber, v_interp_all, dt_ms, tstop_ms, lst_dx_fiber
    # )
    # results["all_same"] = (v_interp_all, v_matrix_all, ap_count_all, spike_times_all)
    # np.savetxt(DATA_DIR / f"temp/vm_all_same_f{int(f0_hz)}_UnitId_{unit_id}.csv", v_matrix_all, delimiter=",")

    # print(f"[all_same f0={f0_hz}Hz A_total={A_total_mA}mA] unit_id={unit_id} ap_count={ap_count_all} "
    #       f"v_interp min={v_interp_all.min():.4f} max={v_interp_all.max():.4f}")

    # # 比較指標（任意）
    # diff = v_interp_all - v_interp_rr
    # print(f"[compare] unit_id={unit_id} RMS(diff)={np.sqrt(np.mean(diff**2)):.4f} "
    #       f"max|diff|={np.max(np.abs(diff)):.4f}")
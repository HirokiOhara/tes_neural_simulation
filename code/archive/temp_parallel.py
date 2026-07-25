import os
from pathlib import Path
import numpy as np
from neuron import h, gui

from wrapper_MRGaxon import MRGaxon
from wrapper_cFiberBuilder import ThioCFiber
from utility import load_csv_points
from get_fiber_length import calculate_cumulative_dx_along_fiber, calculate_fiber_lengths
from get_potential_along_fiber import list_freqs_in_potentials_csv, get_potential_timeseries_along_fiber, calculate_potentials_lerp, superpose_timeseries
from simulate_thio_model import simulate_thio_fiber
from simulate_mrg_model import simulate_mrg_fiber


PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / 'data'
MODEL_DIR = DATA_DIR / 'mrg-model'
CONFIG_DIR = DATA_DIR / 'config'
COMSOL_DIR = DATA_DIR / 'comsol'

os.chdir(MODEL_DIR)
h.nrn_load_dll(str(MODEL_DIR / 'nrnmech.dll'))
h.load_file('nrngui.hoc')
h.xopen('MRGaxonBuilder.hoc')

unit_id = 1
dt_ms = 0.1
tstop_ms = 1.0

points = load_csv_points(CONFIG_DIR / 'points_along_ra1_fibers.csv')

cum_lengths = calculate_cumulative_dx_along_fiber(points)
fiber_lengths = calculate_fiber_lengths(points)

for unit_id, length in fiber_lengths.items():
    fiber = MRGaxon(8.7, length_um=length)

    lst_dx_fiber = [
        fiber.distance_to_node_center_from_end(i) for i in range(fiber.n_compartments)
    ]


    # # 1ファイルの周波数リストの確認
    freqs_in_file = list_freqs_in_potentials_csv(str(COMSOL_DIR / 'electrode_square/potentials_along_ra1_fiber_electrodes_1.csv'))
    print('freqs:', freqs_in_file)

    freq_electrode_pair1 = freqs_in_file[1]
    freq_electrode_pair2 = freqs_in_file[0]

    lst_potentials_complex = [
        (str(COMSOL_DIR / 'electrode_square/potentials_along_ra1_fiber_electrodes_1.csv'), freq_electrode_pair1, 5.0, 0.0),
        (str(COMSOL_DIR / 'electrode_square/potentials_along_ra1_fiber_electrodes_2.csv'), freq_electrode_pair2, 5.0, np.pi),
    ]

    print('freqs:', freq_electrode_pair1)
    print('freqs:', freq_electrode_pair2)

    per_component = []  # 重畳用

    for pot_csv, freq_hz, amp_ma, phi_rad in lst_potentials_complex:
        v = get_potential_timeseries_along_fiber(
            unit_id=unit_id,
            points=points,
            potentials_csv=pot_csv,
            target_freq_hz=float(freq_hz),
            dt_ms=dt_ms,
            tstop_ms=tstop_ms,
            amp_ma=float(amp_ma),
            phi_rad=float(phi_rad),
        )
        v_interporated = calculate_potentials_lerp(lst_dx_fiber, v, cum_lengths[unit_id])
        per_component.append(v_interporated)     # 重畳用

    v_total = superpose_timeseries(per_component)   # 重畳
    print('v_total shape:', v_total.shape)  # (P,T)

    # print(v_total)
    # print(dt_ms)
    # print(tstop_ms)
    # print(lst_dx_fiber)

    # v_matrix, ap_count, spike_times = simulate_mrg_fiber(fiber, v_total, dt_ms, tstop_ms, lst_dx_fiber)

    # print(v_matrix)
    # np.savetxt(DATA_DIR / 'temp.csv', v_matrix, delimiter=',')
    # # for i in range(len(v_matrix[0])):
    # #     print(v_matrix[50][i])
    # print(ap_count)
    # print(spike_times)
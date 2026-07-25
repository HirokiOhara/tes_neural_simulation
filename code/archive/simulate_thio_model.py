from pathlib import Path
import numpy as np
from neuron import h


def setup_apcount(section, x=0.5, threshold=0.0):
    '''指定セクションにAPCounterを設置'''
    apc = h.APCount(section(x))
    apc.thresh = threshold
    spk_times = h.Vector()
    apc.record(spk_times)
    return apc, spk_times


def simulate_thio_fiber(fiber_model, potentials_timeserise_along_fiber, dt_ms, tstop, lst_cumulative_dx):
    '''単一fiberのシミュレーション'''
    lst_cumulative_dt = np.arange(0.0, tstop + dt_ms, dt_ms)

    h.v_init = -58.49   # thio2024, tabel2, cutaneous c-fiber
    h.dt = dt_ms
    h.tstop = float(lst_cumulative_dt[-1])

    t_vec = h.Vector(lst_cumulative_dt.tolist())

    v_stimulation_vectors = []
    v_recorder_vectors = []

    sl = fiber_model.section_list

    for i, sec in enumerate(sl):
        v_vec = h.Vector(potentials_timeserise_along_fiber[i].tolist())
        v_vec.play(sec(0.5)._ref_e_extracellular, t_vec, False)
        v_stimulation_vectors.append(v_vec)
        v_recorders_vec = h.Vector()
        v_recorders_vec.record(sec(0.5)._ref_v)
        v_recorder_vectors.append(v_recorders_vec)

    apc, spk_times = setup_apcount(fiber_model.nodes[-1], x=0.5, threshold=30.0)

    h.finitialize(h.v_init)
    h.continuerun(h.tstop)

    n_time = len(lst_cumulative_dt)
    n_dx = len(lst_cumulative_dx)

    v_matrix = np.zeros((n_dx, n_time), dtype=np.float64)
    for i, vec in enumerate(v_recorder_vectors):
        v_matrix[i, :] = np.array(vec.as_numpy())

    spike_times = np.array(spk_times.as_numpy()) if spk_times.size() > 0 else np.array([])
    ap_count = int(apc.n)

    for sec in h.allsec():
        h.delete_section(sec=sec)

    return v_matrix, ap_count, spike_times


if __name__ == '__main__':

    import os
    from wrapper_cFiberBuilder import ThioCFiber
    from utility import load_csv_points
    from get_fiber_length import calculate_cumulative_dx_along_fiber, calculate_fiber_lengths
    from get_potential_along_fiber import list_freqs_in_potentials_csv, get_potential_timeseries_along_fiber, calculate_potentials_lerp, superpose_timeseries

    PROJECT_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = PROJECT_DIR / 'data'
    MODEL_DIR = DATA_DIR / 'thio-model'
    CONFIG_DIR = DATA_DIR / 'config'
    COMSOL_DIR = DATA_DIR / 'comsol'

    os.chdir(MODEL_DIR)
    h.nrn_load_dll(str(MODEL_DIR / 'nrnmech.dll'))
    h.load_file('nrngui.hoc')
    h.xopen('cFiberBuilder.hoc')
    h.load_file('balance.hoc')

    unit_id = 1
    dt_ms = 0.01
    tstop_ms = 10.0

    points = load_csv_points(CONFIG_DIR / 'points_along_enf_fibers.csv')
    cum_lengths = calculate_cumulative_dx_along_fiber(points)
    fiber_lengths = calculate_fiber_lengths(points)

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


        # # 1ファイルの周波数リストの確認
        freqs_in_file = list_freqs_in_potentials_csv(str(COMSOL_DIR / 'fourier_transform/finger_model/freq_domain_ENF_fiber_electrodes_e1e2.csv'))
        print('freqs:', freqs_in_file)

        freq_electrode_pair1 = freqs_in_file[0]
        freq_electrode_pair2 = freqs_in_file[0]

        lst_potentials_complex = [
            # (str(COMSOL_DIR / '2026-05-24/potentials_same-gnd_pair1.csv'), 2000.0, 0.03, 0.0),
            # (str(COMSOL_DIR / '2026-05-24/potentials_same-gnd_pair4.csv'), 2000.0, 0.03, 0.0),
            (str(COMSOL_DIR / 'fourier_transform/finger_model/freq_domain_ENF_fiber_electrodes_e1e2.csv'), freq_electrode_pair1, 0.004, 0.0),
            (str(COMSOL_DIR / 'fourier_transform/finger_model/freq_domain_ENF_fiber_electrodes_e4e3.csv'), freq_electrode_pair2, 0.004, np.pi),
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
        # print('v_total shape:', v_total.shape)  # (P,T)

        # print(v_total)
        # print(dt_ms)
        # print(tstop_ms)
        # print(lst_dx_fiber)

        v_matrix, ap_count, spike_times = simulate_thio_fiber(fiber, v_total, dt_ms, tstop_ms, lst_dx_fiber)

        print(v_matrix)
        print(ap_count)
        print(spike_times)

        np.savetxt(DATA_DIR / f'temp/temp_{unit_id}.csv', v_matrix, delimiter=',')
        # for i in range(len(v_matrix[0])):
        #     print(v_matrix[50][i])
        print(ap_count)
        print(spike_times)





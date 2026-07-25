from pathlib import Path
import os
from neuron import h, gui

from wrapper_cFiberBuilder import ThioCFiber

# =============================================================================
# パス設定・初期化
# =============================================================================

# 初期化
PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / 'data'
MODEL_DIR = DATA_DIR / 'thio-model'

os.chdir(MODEL_DIR)
h.nrn_load_dll(str(MODEL_DIR / 'nrnmech.dll'))
h.load_file('nrngui.hoc')
h.xopen('cFiberBuilder.hoc')

# =============================================================================
# Table 2 期待値
# =============================================================================

EXPECTED = {
    'gbar_nav7':    35.66  * 0.001,
    'gbar_newnav8': 115.6  * 0.001,
    'gbar_nav9':    0.504  * 0.001,
    'gbar_ka14':    0.044  * 0.001,
    'gbar_kv21':    327.2  * 0.001,
    'gbar_ka34':    1.786  * 0.001,
    'gbar_km':      0.003  * 0.001,
    'gbar_bk':      2.016  * 0.001,
    'gbar_sk':      0.755  * 0.001,
    'gbar_cav12':   0.188  * 0.001,
    'gbar_cav22':   0.361  * 0.001,
    'gbar_hcn':     0.106  * 0.001,
    'gbar_nacx':    9.242  * 0.001,
    'INaKmax22':    0.456  * 0.001,
    'Ra':           27.51,
    'v_init':       -58.49,
}

# =============================================================================
# 確認関数
# =============================================================================

def check_param(name, actual, expected):
    tolerance = abs(expected) * 0.01 + 1e-10
    match = '✓' if abs(actual - expected) < tolerance else '✗'
    print(f'  {name:20s}: {actual:12.6g}  (期待: {expected:.6g}) {match}')

# =============================================================================
# メイン
# =============================================================================

fiber = ThioCFiber(
    fiber_diameter=0.8,
    length_um=100,
    temperature=37,
    particle_index=1
)
sec = fiber.nodes[0]

print('\n' + '=' * 60)
print(' Cutaneous C-fiber (ACT) パラメータ確認')
print('=' * 60)

print('\n[基本パラメータ]')
print(f'  nsegments: {fiber.n_segments}')
print(f'  Length: {fiber.length} um')
print(f'  diam: {fiber._fiber.fiberD} um')
print(f'  L (segment): {fiber._fiber.dx} um')
print(f'  cm: {sec.cm} uF/cm2')

print('\n[内部比抵抗]')
check_param('Ra', sec.Ra, EXPECTED['Ra'])

print('\n[Na チャネル]')
check_param('gbar_nav7', sec.gbar_nav7, EXPECTED['gbar_nav7'])
check_param('gbar_newnav8', sec.gbar_newnav8, EXPECTED['gbar_newnav8'])
check_param('gbar_nav9', sec.gbar_nav9, EXPECTED['gbar_nav9'])

print('\n[Ca チャネル]')
check_param('gbar_cav12', sec.gbar_cav12, EXPECTED['gbar_cav12'])
check_param('gbar_cav22', sec.gbar_cav22, EXPECTED['gbar_cav22'])

print('\n[K チャネル]')
check_param('gbar_kv21', sec.gbar_kv21, EXPECTED['gbar_kv21'])
check_param('gbar_ka34', sec.gbar_ka34, EXPECTED['gbar_ka34'])
check_param('gbar_ka14', sec.gbar_ka14, EXPECTED['gbar_ka14'])
check_param('gbar_km', sec.gbar_km, EXPECTED['gbar_km'])
check_param('gbar_bk', sec.gbar_bk, EXPECTED['gbar_bk'])
check_param('gbar_sk', sec.gbar_sk, EXPECTED['gbar_sk'])

print('\n[その他]')
check_param('gbar_hcn', sec.gbar_hcn, EXPECTED['gbar_hcn'])
check_param('gbar_nacx', sec.gbar_nacx, EXPECTED['gbar_nacx'])
check_param('INaKmax22', sec.INaKmax22_NaKpumpSchild, EXPECTED['INaKmax22'])

print('\n[イオン濃度・平衡電位]')
print(f'  nao: {sec.nao} mM')
print(f'  nai: {sec.nai} mM')
print(f'  ena: {sec.ena:.2f} mV')
print(f'  ko: {sec.ko} mM')
print(f'  ki: {sec.ki} mM')
print(f'  ek: {sec.ek:.2f} mV')

print('\n' + '=' * 60)
print(' 完了')
print('=' * 60)
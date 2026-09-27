from pathlib import Path
import os
from neuron import h, gui

# 初期化
PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / 'data'
MODEL_DIR = DATA_DIR / 'thio-model'

os.chdir(MODEL_DIR)
h.nrn_load_dll(str(MODEL_DIR / 'nrnmech.dll'))
h.load_file('nrngui.hoc')
h.xopen('thio-model.hoc')
h.load_file('balance.hoc')

fiber = h.fiber
sec = fiber.section[0].sec

# 静止膜電位設定
h.v_init = -58.49

# balance前の電流を記録
h.finitialize(h.v_init)
h.fcurrent()

ina_before = sec(0.5).ina
ik_before = sec(0.5).ik
ica_before = sec(0.5).ica

print('=' * 60)
print(' balance() 前後の比較')
print('=' * 60)

print('\n[balance前の総イオン電流]')
print(f'  ina: {ina_before:.6g} mA/cm2')
print(f'  ik:  {ik_before:.6g} mA/cm2')
print(f'  ica: {ica_before:.6g} mA/cm2')

# balance実行
h.balance()
h.fcurrent()

print('\n[balance後の総イオン電流（≈0であるべき）]')
print(f'  ina: {sec(0.5).ina:.6g} mA/cm2')
print(f'  ik:  {sec(0.5).ik:.6g} mA/cm2')
print(f'  ica: {sec(0.5).ica:.6g} mA/cm2')

print('\n[リーク/ポンプ値（balance()で計算）]')
try:
    print(f'  gnaleak: {sec.gnaleak_leak:.6g} S/cm2')
    print(f'  gkleak:  {sec.gkleak_leak:.6g} S/cm2')
    print(f'  gcaleak: {sec.gcaleak_leak:.6g} S/cm2')   ## gcaleakはエラーになるが、Thio モデルでは leak コンダクタンスではなく extrapump でイオン電流をバランスさせる設計だからだと考えられる。 (ohara, 2025.05.24)
except:
    print('  (leak値取得エラー)')

try:
    print(f'  pumpina: {sec.pumpina_extrapump:.6g} mA/cm2')
    print(f'  pumpik:  {sec.pumpik_extrapump:.6g} mA/cm2')
    print(f'  pumpica: {sec.pumpica_extrapump:.6g} mA/cm2')
except:
    print('  (pump値取得エラー)')

print('\n' + '=' * 60)
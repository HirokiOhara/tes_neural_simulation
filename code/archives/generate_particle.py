import os

# =====================================================
# Cutaneous PSO Fiber のパラメータ (Table 2)
# =====================================================

# 単位変換:
#   mS/cm² → S/cm² : ×0.001
#   μA/cm² → mA/cm² : ×0.001

# Particle.dat 用パラメータ（HOCファイルの読み込み順序）
particle_params = [
    ('gbar_nav7',    35.66  * 0.001),   # 行0:  Nav1.7
    ('gbar_newnav8', 115.6  * 0.001),   # 行1:  Nav1.8
    ('gbar_nav9',    0.504  * 0.001),   # 行2:  Nav1.9
    ('gbar_bk',      2.016  * 0.001),   # 行3:  KCa_BK
    ('gbar_cav12',   0.188  * 0.001),   # 行4:  Cav1.2
    ('gbar_cav22',   0.361  * 0.001),   # 行5:  Cav2.2
    ('gbar_km',      0.003  * 0.001),   # 行6:  Kv7 (M)
    ('gbar_hcn',     0.106  * 0.001),   # 行7:  HCN
    ('gbar_kv21',    327.2  * 0.001),   # 行8:  Kv2.1
    ('gbar_ka34',    1.786  * 0.001),   # 行9:  Kv3.4
    ('gbar_ka14',    0.044  * 0.001),   # 行10: Kv1.4
    ('gbar_sk',      0.755  * 0.001),   # 行11: KCa_SK
    ('gbar_nacx',    9.242  * 0.001),   # 行12: NaCa_exchanger
    ('INaKmax22',    0.456  * 0.001),   # 行13: NaK_pump
    ('Ra',           27.51),            # 行14: 軸方向抵抗
]

# HOCファイルで別途設定が必要なパラメータ
additional_params = {
    # Leak conductances (mS/cm² → S/cm²)
    'gnaleak_leak':     0 * 0.001,
    'gkleak_leak':      0 * 0.001,
    'gcaleak_leak':     0 * 0.001,
    
    # Pump currents (μA/cm² → mA/cm²)
    'pumpina_extrapump': 5.131  * 0.001,
    'pumpik_extrapump':  10.080 * 0.001,
    'pumpica_extrapump': 0.049  * 0.001,
    
    # Rest potential
    'v_init': -58.49,
}


# =====================================================
# ファイル作成
# =====================================================

def create_particle_file(particle_index=1):
    '''Particle.dat ファイルを作成'''
    
    os.makedirs('ConductanceSets', exist_ok=True)
    output_file = f'ConductanceSets/Particle{particle_index}.dat'
    
    with open(output_file, 'w') as f:
        for name, value in particle_params:
            f.write(f'{value}\n')
    
    print(f'ファイル作成完了: {output_file}')
    return output_file


def print_all_parameters():
    '''全パラメータを表示'''
    
    print('\n' + '=' * 60)
    print(' Cutaneous C-fiber パラメータ一覧 (Table 2)')
    print('=' * 60)
    
    print('\n[Particle.dat に含まれるパラメータ]')
    print('-' * 60)
    for i, (name, value) in enumerate(particle_params):
        print(f'  行{i:2d}: {name:20s} = {value:>12.6g}')
    
    print('\n[HOCファイルで別途設定が必要なパラメータ]')
    print('-' * 60)
    for name, value in additional_params.items():
        print(f'        {name:25s} = {value:>12.6g}')


# =====================================================
# メイン実行
# =====================================================

if __name__ == '__main__':
    print_all_parameters()
    print('\n')
    create_particle_file(particle_index=1)
import numpy as np
import matplotlib.pyplot as plt
import os
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / 'data'
TEMP_DIR = DATA_DIR / "temp"

offset = 1.0   # 行（位置）ごとの縦オフセット量（適宜調整）
dt = 1.0       # サンプル間隔（不明なら1.0でOK、必要に応じて変更）


## TEMP_DIR 以下の temp_xx.csv をすべて対象（xxは数字想定）
# csv_paths = sorted(TEMP_DIR.glob("vm_UnitId_[0-9]*.csv"))
# csv_paths = sorted(TEMP_DIR.glob("vm_UnitId_23.csv"))
# csv_paths = sorted(TEMP_DIR.glob("vm_all_same_f1000_UnitId_23.csv"))
csv_paths = sorted(TEMP_DIR.glob("vm_round_robin_UnitId_23.csv"))
# csv_paths = sorted(TEMP_DIR.glob("vm_all_same_f3500_UnitId_218.csv"))
# csv_paths = sorted(TEMP_DIR.glob("vm_round_robin_UnitId_218.csv"))

## csvを選択 
# targets = [1, 3, 10]

# csv_paths = []
# for n in targets:
#     p = TEMP_DIR / f"temp_{n}.csv"
#     if p.exists():
#         csv_paths.append(p)
#     else:
#         print(f"not found: {p}")


for i, csv_path in enumerate(csv_paths):
    y = np.loadtxt(csv_path, delimiter=",")  # shape: (n_pos, n_time)
    y = y[::10, :]
    t = np.arange(y.shape[1]) * dt

    fig, ax = plt.subplots()

    for i in range(y.shape[0]):
        ax.plot(t, y[i] + i * offset, lw=1)

    # 目盛り無し（軸線とプロットだけ）
    ax.set_xticks([])
    ax.set_yticks([])

    # 枠線も不要なら次を有効化
    # for spine in ax.spines.values():
    #     spine.set_visible(False)

    # 画像保存（同じ temp ディレクトリに出力）
    out_path = csv_path.with_suffix(".png")  # temp_01.csv -> temp_01.png
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("done")
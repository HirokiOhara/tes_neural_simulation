"""
plot_membrane_potential.py

膜電位データの可視化スクリプト
ra1_all_1d.csv 等を読み込んでプロット

Usage:
    python code/plot_membrane_potential.py
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Tuple, Optional


# =============================================================================
# パス設定
# =============================================================================
PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
OUTPUT_DIR = DATA_DIR / "output"


# =============================================================================
# データ読み込み
# =============================================================================

def load_membrane_potential_data(filepath: Path) -> pd.DataFrame:
    """膜電位CSVを読み込み"""
    df = pd.read_csv(filepath)
    return df


def extract_time_columns(df: pd.DataFrame) -> Tuple[List[str], np.ndarray, int]:
    """
    時間列を抽出し、時間配列を生成
    
    Returns:
        v_cols: 電位列名のリスト ['V_t0', 'V_t1', ...]
        t_indices: 時間インデックス配列 [0, 1, 2, ...]
        n_steps: 時間ステップ数
    """
    v_cols = [col for col in df.columns if col.startswith('V_t')]
    n_steps = len(v_cols)
    t_indices = np.array([int(col.replace('V_t', '')) for col in v_cols])
    
    return v_cols, t_indices, n_steps


def get_unit_ids(df: pd.DataFrame) -> np.ndarray:
    """データに含まれるunit_idの一覧を取得"""
    return df['unit_id'].unique()


# =============================================================================
# プロット関数
# =============================================================================

def plot_single_unit_overview(
    df: pd.DataFrame, 
    unit_id: int, 
    dt_ms: float = 0.01,
    save_path: Optional[Path] = None,
    show: bool = True
):
    """
    単一unit_idの概要プロット
    
    Parameters:
        df: 膜電位データフレーム
        unit_id: 対象のunit_id
        dt_ms: 時間刻み [ms]
        save_path: 保存先パス（Noneなら保存しない）
        show: Trueならプロット表示
    
    Output:
        上段: 全ノードの膜電位（カラーマップ）
        下段: 中央ノードの時系列
    """
    # データ抽出
    unit_df = df[df['unit_id'] == unit_id].copy()
    unit_df = unit_df.sort_values('x_um').reset_index(drop=True)
    
    v_cols, t_indices, n_steps = extract_time_columns(df)
    t_ms = t_indices * dt_ms
    
    # ノードのみ抽出
    node_df = unit_df[unit_df['type'] == 'node'].reset_index(drop=True)
    n_nodes = len(node_df)
    
    if n_nodes == 0:
        print(f"Warning: No nodes found for unit_id={unit_id}")
        return
    
    # 膜電位行列 (n_nodes, n_steps)
    v_matrix = node_df[v_cols].values.astype(float)
    x_positions = node_df['x_um'].values.astype(float)
    
    # プロット
    fig, axes = plt.subplots(3, 1, figsize=(14, 12), 
                              gridspec_kw={'height_ratios': [1, 1, 1]})
    
    # --- 上段: カラーマップ ---
    ax1 = axes[0]
    im = ax1.imshow(v_matrix, aspect='auto', origin='lower',
                    extent=[t_ms[0], t_ms[-1], 0, n_nodes-1],
                    cmap='RdBu_r', vmin=-100, vmax=50)
    ax1.set_xlabel('Time (ms)')
    ax1.set_ylabel('Node index')
    ax1.set_title(f'unit_id={unit_id}: Membrane Potential (nodes only, n={n_nodes})')
    plt.colorbar(im, ax=ax1, label='Vm (mV)')
    
    # --- 下段: 中央ノードの時系列 ---
    ax2 = axes[1]
    first_idx = 0
    ax2.plot(t_ms, v_matrix[first_idx, :], 'b-', linewidth=0.5, label='Membrane potential (first node)')
    ax2.axhline(y=0, color='gray', linestyle='--', alpha=0.5, label='Threshold of AP count (0mV)')
    ax2.axhline(y=-55, color='green', linestyle=':', alpha=0.5, label='Rest (~-55mV)')
    ax2.set_xlabel('Time (ms)')
    ax2.set_ylabel('Membrane potential (mV)')
    ax2.set_title(f'First node (idx={first_idx}, x={x_positions[first_idx]:.1f} um)')
    ax2.legend(loc='upper right')
    ax2.set_xlim([t_ms[0], t_ms[-1]])

    ax3 = axes[2]
    center_idx = n_nodes // 2
    last_idx = n_nodes - 1
    ax3.plot(t_ms, v_matrix[center_idx, :], 'c-', linewidth=0.5, label='Membrane potential (center node)')
    ax3.plot(t_ms, v_matrix[last_idx, :], 'b-', linewidth=0.5, label='Membrane potential (last node)')
    ax3.axhline(y=0, color='gray', linestyle='--', alpha=0.5, label='Threshold of AP count (0mV)')
    ax3.axhline(y=-55, color='green', linestyle=':', alpha=0.5, label='Rest (~-55mV)')
    ax3.set_xlabel('Time (ms)')
    ax3.set_ylabel('Membrane potential (mV)')
    ax3.set_title(f'Center node (idx={center_idx}, x={x_positions[center_idx]:.1f} um) \n Last node (idx={last_idx}, x={x_positions[last_idx]:.1f} um)')
    ax3.legend(loc='upper right')
    ax3.set_xlim([t_ms[0], t_ms[-1]])

    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150)
        print(f"Saved: {save_path}")
    
    if show:
        plt.show()
    else:
        plt.close()


def main():
    """メイン関数"""
    
    # ===== 設定 =====
    csv_filename = "ra1_all_1d.csv"
    dt_ms = 0.01  # シミュレーションの時間刻み [ms]
    
    # ===== データ読み込み =====
    csv_path = OUTPUT_DIR / csv_filename
    print(f"Loading: {csv_path}")
    
    if not csv_path.exists():
        print(f"Error: File not found: {csv_path}")
        return
    
    df = load_membrane_potential_data(csv_path)
    
    print(f"Data shape: {df.shape}")
    print(f"Columns: {df.columns[:5].tolist()} ... {df.columns[-3:].tolist()}")
    
    unit_ids = get_unit_ids(df)
    print(f"unit_ids: {unit_ids}")
    
    # ===== プロット =====
    
    # --- 各ユニットの概要 ---
    print("\n=== Single unit overview ===")
    for uid in unit_ids:
        plot_single_unit_overview(
            df, unit_id=uid, dt_ms=dt_ms, 
            # save_path=OUTPUT_DIR / f"vm_unit{uid}_overview.png"
        )

    
    print("\n=== Done! ===")


if __name__ == "__main__":
    main()
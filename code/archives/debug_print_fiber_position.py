"""
filter_units_by_position.py

fiber_info_summary.csv を読み込み、指定したx,y範囲内のユニットを抽出・表示

Usage:
    python scripts/filter_units_by_position.py
    
    # または引数で範囲指定
    python scripts/filter_units_by_position.py --x_min -5 --x_max 5 --y_min -20 --y_max -10
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, List
import argparse


# =============================================================================
# パス設定
# =============================================================================
PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
CONFIG_DIR = DATA_DIR / "config"


# =============================================================================
# データ読み込み・フィルタリング
# =============================================================================

def load_fiber_info(filepath: Path) -> pd.DataFrame:
    """fiber_info_summary.csv を読み込み"""
    df = pd.read_csv(filepath)
    return df


def filter_units_by_position(
    df: pd.DataFrame,
    x_min: Optional[float] = None,
    x_max: Optional[float] = None,
    y_min: Optional[float] = None,
    y_max: Optional[float] = None,
    receptor_types: Optional[List[str]] = None,
    coord_column_x: str = 'P_x',
    coord_column_y: str = 'P_y',
) -> pd.DataFrame:
    """
    座標範囲でユニットをフィルタリング
    
    Parameters:
        df: fiber_info_summary データフレーム
        x_min, x_max: X座標の範囲 [mm]
        y_min, y_max: Y座標の範囲 [mm]
        receptor_types: 対象レセプタータイプのリスト（Noneなら全タイプ）
        coord_column_x: X座標の列名（デフォルト: 'P_x' = 終末位置）
        coord_column_y: Y座標の列名（デフォルト: 'P_y'）
    
    Returns:
        フィルタリングされたデータフレーム
    """
    mask = pd.Series([True] * len(df))
    
    if x_min is not None:
        mask &= df[coord_column_x] >= x_min
    if x_max is not None:
        mask &= df[coord_column_x] <= x_max
    if y_min is not None:
        mask &= df[coord_column_y] >= y_min
    if y_max is not None:
        mask &= df[coord_column_y] <= y_max
    
    if receptor_types is not None:
        mask &= df['ReceptorType'].isin(receptor_types)
    
    return df[mask].copy()


def print_units_summary(
    df: pd.DataFrame,
    coord_column_x: str = 'P_x',
    coord_column_y: str = 'P_y',
):
    """
    フィルタリング結果を整形して表示
    """
    if len(df) == 0:
        print("No units found in the specified range.")
        return
    
    # レセプタータイプ別にグループ化
    receptor_types = ['RA1', 'RA2', 'SA1', 'ENF']
    
    print("=" * 70)
    print(f"{'Type':<6} {'unit_id':>8} {'x [mm]':>10} {'y [mm]':>10} {'path_len [mm]':>14}")
    print("=" * 70)
    
    for rtype in receptor_types:
        type_df = df[df['ReceptorType'] == rtype].sort_values('GlobalUnitID')
        
        if len(type_df) == 0:
            continue
        
        print(f"\n--- {rtype} ({len(type_df)} units) ---")
        
        for _, row in type_df.iterrows():
            unit_id = row['GlobalUnitID']
            x = row[coord_column_x]
            y = row[coord_column_y]
            path_len = row.get('path_length_mm', np.nan)
            
            print(f"{rtype:<6} {unit_id:>8} {x:>10.3f} {y:>10.3f} {path_len:>14.2f}")
    
    print("\n" + "=" * 70)
    print(f"Total: {len(df)} units")


def print_units_as_list(df: pd.DataFrame):
    """
    unit_idをリスト形式で表示（コピー用）
    """
    receptor_types = ['RA1', 'RA2', 'SA1', 'ENF']
    
    print("\n--- Unit IDs (copy-paste format) ---")
    
    for rtype in receptor_types:
        type_df = df[df['ReceptorType'] == rtype]
        if len(type_df) == 0:
            continue
        
        ids = type_df['GlobalUnitID'].tolist()
        print(f"{rtype}: {ids}")


def get_coordinate_range(df: pd.DataFrame, coord_column_x: str = 'P_x', 
                          coord_column_y: str = 'P_y'):
    """
    データ全体の座標範囲を表示
    """
    x_min, x_max = df[coord_column_x].min(), df[coord_column_x].max()
    y_min, y_max = df[coord_column_y].min(), df[coord_column_y].max()
    
    print(f"Data coordinate range:")
    print(f"  X: [{x_min:.3f}, {x_max:.3f}] mm")
    print(f"  Y: [{y_min:.3f}, {y_max:.3f}] mm")
    
    return (x_min, x_max), (y_min, y_max)


def count_by_receptor_type(df: pd.DataFrame):
    """
    レセプタータイプ別のカウントを表示
    """
    counts = df['ReceptorType'].value_counts()
    print("\nReceptor type counts:")
    for rtype in ['RA1', 'RA2', 'SA1', 'ENF']:
        count = counts.get(rtype, 0)
        print(f"  {rtype}: {count}")


# =============================================================================
# メイン
# =============================================================================

def main():
    """メイン関数"""
    
    # コマンドライン引数のパース
    parser = argparse.ArgumentParser(
        description='Filter units by position from fiber_info_summary.csv'
    )
    parser.add_argument('--x_min', type=float, default=None, help='Minimum X coordinate [mm]')
    parser.add_argument('--x_max', type=float, default=None, help='Maximum X coordinate [mm]')
    parser.add_argument('--y_min', type=float, default=None, help='Minimum Y coordinate [mm]')
    parser.add_argument('--y_max', type=float, default=None, help='Maximum Y coordinate [mm]')
    parser.add_argument('--types', type=str, default=None, 
                        help='Receptor types (comma-separated, e.g., RA1,SA1)')
    parser.add_argument('--csv', type=str, default='fiber_info_summary.csv',
                        help='Input CSV filename')
    parser.add_argument('--info', action='store_true',
                        help='Show data info and exit')
    
    args = parser.parse_args()
    
    # CSVファイルパス
    csv_path = CONFIG_DIR / args.csv
    
    print(f"Loading: {csv_path}")
    
    if not csv_path.exists():
        print(f"Error: File not found: {csv_path}")
        return
    
    df = load_fiber_info(csv_path)
    print(f"Loaded {len(df)} units\n")
    
    # データ情報表示モード
    if args.info:
        get_coordinate_range(df)
        count_by_receptor_type(df)
        return
    
    # レセプタータイプのパース
    receptor_types = None
    if args.types:
        receptor_types = [t.strip().upper() for t in args.types.split(',')]
        print(f"Filtering receptor types: {receptor_types}")
    
    # 座標範囲が指定されていない場合はインタラクティブに入力
    x_min = args.x_min
    x_max = args.x_max
    y_min = args.y_min
    y_max = args.y_max
    
    if all(v is None for v in [x_min, x_max, y_min, y_max]):
        print("\n--- Enter coordinate range (press Enter to skip) ---")
        get_coordinate_range(df)
        print()
        
        try:
            x_min_str = input("X min [mm] (default: no limit): ").strip()
            x_max_str = input("X max [mm] (default: no limit): ").strip()
            y_min_str = input("Y min [mm] (default: no limit): ").strip()
            y_max_str = input("Y max [mm] (default: no limit): ").strip()
            
            x_min = float(x_min_str) if x_min_str else None
            x_max = float(x_max_str) if x_max_str else None
            y_min = float(y_min_str) if y_min_str else None
            y_max = float(y_max_str) if y_max_str else None
        except ValueError:
            print("Invalid input. Using no limits.")
    
    # フィルタリング実行
    print(f"\nFiltering with: x=[{x_min}, {x_max}], y=[{y_min}, {y_max}]")
    
    filtered_df = filter_units_by_position(
        df,
        x_min=x_min,
        x_max=x_max,
        y_min=y_min,
        y_max=y_max,
        receptor_types=receptor_types,
    )
    
    # 結果表示
    print_units_summary(filtered_df)
    print_units_as_list(filtered_df)


if __name__ == "__main__":
    main()
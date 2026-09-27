import numpy as np

def load_csv_points(filepath):
    data = np.loadtxt(filepath, delimiter=',',encoding="utf-8_sig")
    return data[:, :]


if __name__ == '__main__':
    from pathlib import Path

    PROJECT_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = PROJECT_DIR / 'data'
    MODEL_DIR = DATA_DIR / 'thio-model'
    CONFIG_DIR = DATA_DIR / 'config'
    COMSOL_DIR = DATA_DIR / 'comsol'

    lst = load_csv_points(CONFIG_DIR / 'points_along_ra1_fibers.csv')

    print(lst)
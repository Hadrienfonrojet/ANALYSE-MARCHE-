"""Compatibilité : le moteur d'analyse se trouve dans analyses/Analyse_ouvertures.py."""
from analyses.Analyse_ouvertures import analyze, chi_test, run_models

if __name__ == '__main__':
    import pandas as pd
    import config_projet as cfg
    analyze(pd.read_parquet(cfg.DATA_DIR / 'games_clean.parquet'))

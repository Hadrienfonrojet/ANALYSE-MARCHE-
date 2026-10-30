"""Point d'accès conservé à la racine du projet.

Le fil complet, réparti en six parties commentées, est dans
analyses/Analyse_ouvertures.py. Les fonctions sont importables ici pour les
anciens notebooks. La régression utilise désormais un seul modèle multiple.
"""

from analyses.Analyse_ouvertures import analyze, chi_test, statistiques_descriptives
from analyses.Regression_multiple import regression_multiple


if __name__ == "__main__":
    import pandas as pd
    import config_projet as cfg

    analyze(pd.read_parquet(cfg.DATA_DIR / "games_clean.parquet"))

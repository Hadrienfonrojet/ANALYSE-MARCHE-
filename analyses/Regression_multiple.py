"""Une régression multiple pédagogique et son test F de Fisher-Snedecor.

Ce fichier ne réalise PAS un test exact de Fisher : celui-ci porte sur un
petit tableau de contingence et se trouve dans Tests_repetition.py.
Le modèle linéaire du score est descriptif ; le score est borné et discret.
"""

import numpy as np
import pandas as pd
from scipy.stats import f
import statsmodels.formula.api as smf


## Partie 1 - Préparer le DataFrame utilisé par la régression


def prepare_regression(data):
    """Garder les observations dont les variables nécessaires sont connues."""
    columns = [
        "score",
        "repeat_same_color",
        "elo_diff",
        "is_white",
        "format_partie",
        "user_id",
    ]
    missing = set(columns) - set(data.columns)
    if missing:
        raise ValueError(
            "Colonnes de régression absentes : " + ", ".join(sorted(missing))
        )

    sample = data[columns].copy()  ## Nouveau DataFrame limité aux colonnes du modèle.
    for column in ["score", "repeat_same_color", "elo_diff", "is_white"]:
        sample[column] = pd.to_numeric(sample[column], errors="coerce")
    sample = sample.replace([np.inf, -np.inf], np.nan).dropna()
    sample["elo_diff_100"] = sample["elo_diff"] / 100  ## Une unité représente 100 Elo.
    return sample


## Partie 2 - Fonction du test F global classique


def fisher_global_ols(model):
    """Comparer le modèle avec variables au modèle contenant seulement la moyenne.

    H0 : tous les coefficients sauf la constante sont nuls.
    F = ((SCT - SCR) / q) / (SCR / ddl_residus).
    SCT est la somme des carrés autour de la moyenne ; SCR celle des résidus.

    La loi F(q, ddl_residus) est exacte avec erreurs normales, indépendantes et
    de variance constante. Ces conditions ne sont pas garanties pour les scores
    répétés de joueurs : la valeur p classique est un repère pédagogique.
    """
    q = float(model.df_model)
    residual_degrees = float(model.df_resid)
    residual_sum = float(model.ssr)

    if q <= 0 or residual_degrees <= 0 or residual_sum <= 0:
        return {
            "F_classique": np.nan,
            "p_F_classique": np.nan,
            "ddl_numerateur": q,
            "ddl_denominateur": residual_degrees,
        }

    explained_sum = max(0.0, float(model.centered_tss) - residual_sum)
    statistic = (explained_sum / q) / (residual_sum / residual_degrees)
    p_value = f.sf(statistic, q, residual_degrees)  ## Aire à droite dans la loi F.

    return {
        "F_classique": statistic,
        "p_F_classique": p_value,
        "ddl_numerateur": q,
        "ddl_denominateur": residual_degrees,
    }


## Partie 3 - Ajuster un seul modèle et lire ses coefficients


def regression_multiple(data):
    """Associer le score à répétition, écart Elo, couleur et cadence.

    beta de repeat_same_color : différence de score ajustée entre répétition
    et changement, à écart Elo, couleur et cadence comparables dans ce modèle.
    Ce coefficient n'est pas un effet causal.

    La constante, les coefficients, le R² et le F classique sont descriptifs.
    Si au moins 20 joueurs et assez de groupes sont disponibles, on fournit
    aussi des erreurs-types groupées par joueur et un F de Wald approximatif.
    Vingt est un seuil de prudence du projet, pas une garantie statistique.
    """
    sample = prepare_regression(data)
    formula = "score ~ repeat_same_color + elo_diff_100 + is_white + C(format_partie)"
    info = {
        "modele": formula,
        "n": len(sample),
        "joueurs": sample["user_id"].nunique(),
        "statut": "non_estimable",
        "raison": "",
        "r2": np.nan,
        "F_classique": np.nan,
        "p_F_classique": np.nan,
        "F_wald_groupes": np.nan,
        "p_F_wald_groupes": np.nan,
        "ddl_numerateur": np.nan,
        "ddl_denominateur": np.nan,
    }
    empty = pd.DataFrame(
        columns=["variable", "coefficient", "ecart_type_groupe", "p_groupe"]
    )

    if len(sample) < 30 or sample["score"].nunique() < 2:
        info["raison"] = (
            "Au moins 30 lignes et une variation du score sont nécessaires."
        )
        return pd.DataFrame([info]), empty, None

    model = smf.ols(formula, data=sample).fit()
    matrix = model.model.exog  ## Matrice numérique créée à partir de la formule.
    n_parameters = matrix.shape[1]

    # Si une variable est constante ou redondante, ne pas prétendre l'estimer.
    if np.linalg.matrix_rank(matrix) < n_parameters or len(sample) < 5 * n_parameters:
        info["raison"] = "Variables redondantes ou trop peu de lignes pour ce modèle."
        return pd.DataFrame([info]), empty, None

    info.update(fisher_global_ols(model))
    info.update(
        statut="estime",
        raison="F classique illustratif ; observations dépendantes possibles.",
        r2=float(model.rsquared),
    )
    coefficients = pd.DataFrame(
        {
            "variable": model.params.index,
            "coefficient": model.params.to_numpy(),
            "ecart_type_groupe": np.nan,
            "p_groupe": np.nan,
        }
    )

    ## Partie 4 - Complément tenant compte des répétitions au sein du joueur
    if info["joueurs"] >= max(20, n_parameters + 2):
        robust = model.get_robustcov_results(
            cov_type="cluster",
            groups=sample["user_id"],
            use_correction=True,
        )
        coefficients["ecart_type_groupe"] = robust.bse
        coefficients["p_groupe"] = robust.pvalues

        # Tester conjointement tous les coefficients sauf la constante.
        restrictions = np.eye(n_parameters)[1:, :]
        covariance = robust.cov_params()
        restricted_covariance = restrictions @ covariance @ restrictions.T
        if np.linalg.matrix_rank(restricted_covariance) == n_parameters - 1:
            global_test = robust.f_test(restrictions)
            info["F_wald_groupes"] = float(np.asarray(global_test.fvalue).item())
            info["p_F_wald_groupes"] = float(np.asarray(global_test.pvalue).item())
        info["raison"] = (
            "F de Wald groupé approximatif ; adversaires communs non corrigés."
        )
    else:
        info["raison"] += " Trop peu de joueurs pour les valeurs p groupées."

    return pd.DataFrame([info]), coefficients, model

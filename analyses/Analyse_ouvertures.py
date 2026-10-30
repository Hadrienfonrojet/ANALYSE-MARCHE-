"""Fil principal de l'analyse, organisé dans l'ordre demandé pour la lecture.

Partie 1 : créer les DataFrames utiles.
Partie 2 : rappeler la fonction du chi carré.
Partie 3 : appliquer les chi carrés aux questions définies.
Partie 4 : Fisher exact, puis régression multiple et test F de Fisher-Snedecor.
Partie 5 : finir par les statistiques descriptives et les graphiques simples.

Les calculs des tests sont dans Tests_repetition.py ; la régression est dans
Regression_multiple.py. Ce fichier organise ces fonctions sans les masquer.
"""

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config_projet as cfg
from analyses.Tests_repetition import (
    add_transitions,
    chi2_details,
    run_repetition_tests,
    run_fisher_tests,
)
from analyses.Regression_multiple import regression_multiple


## Partie 1 - Créer les DataFrames dont chaque question a besoin


def creer_dataframes(data):
    """Une base complète et deux sous-bases avec un historique disponible.

    La sélection de lignes par .dropna crée un DataFrame, alors qu'une
    affectation data['nouvelle_colonne'] crée une colonne dans la base existante.
    Les ouvertures inconnues ne permettent pas de comparer les familles.
    """
    parties = add_transitions(data)  ## Copie triée contenant les colonnes de passé.
    toutes_couleurs = parties.dropna(subset=["repeat_all", "prev_result_all"]).copy()
    meme_couleur = parties.dropna(
        subset=["repeat_same_color", "prev_result_same_color"]
    ).copy()
    ## Chaque ligne de meme_couleur peut être comparée à une partie antérieure
    ## du même joueur, avec la même couleur et une ouverture connue.
    return {
        "parties": parties,
        "toutes_couleurs": toutes_couleurs,
        "meme_couleur": meme_couleur,
    }


## Partie 2 - Fonction du chi carré et objets qu'elle renvoie


def chi_test(frame, a, b, label, min_expected=5):
    """Renvoyer le résumé ; chi2_details donne aussi observés, attendus, résidus.

    Le calcul commenté est dans Tests_repetition.py, partie 2. Dans le notebook,
    son code est recopié pour qu'il soit visible au moment de l'exécution.
    """
    summary, observed, expected, residuals = chi2_details(
        frame, a, b, label, min_expected
    )
    return summary


## Partie 3 - Appliquer les chi carrés et dire à quoi chaque comparaison sert


def appliquer_chi2(data):
    """Deux questions pour chaque définition de répétition, puis deux sur la couleur.

    Résultat précédent × répétition : décrire le comportement après un résultat.
    Répétition × résultat courant : décrire la performance associée à la répétition.
    Couleur répétée × résultat ou ouverture : distinguer les deux répétitions.
    Les stratifications et le filtrage de sensibilité sont des compléments,
    désactivés ici pour garder un tableau principal de dix comparaisons lisible.
    """
    tests, tables, rates, bootstrap = run_repetition_tests(
        data,
        cfg.RESULTS_DIR / "repetition",
        stratify=False,
        include_sensitivity=False,
    )
    tests.to_csv(cfg.RESULTS_DIR / "tests_chi2.csv", index=False)
    return tests


## Partie 4 - Fisher exact et une régression avec plusieurs variables


def appliquer_fisher_et_regression(data, run_regressions=True):
    """Séparer deux usages du nom Fisher : tableau 2×2 et loi F de régression."""
    fisher, tables = run_fisher_tests(data, cfg.RESULTS_DIR / "fisher")
    if run_regressions:
        summary, coefficients, model = regression_multiple(data)
        summary.to_csv(cfg.RESULTS_DIR / "regression_multiple_resume.csv", index=False)
        coefficients.to_csv(
            cfg.RESULTS_DIR / "regression_multiple_coefficients.csv", index=False
        )
    else:
        summary = pd.DataFrame([{"statut": "desactivee"}])
    return fisher, summary


## Partie 5 - Descriptifs simples à interpréter avant toute conclusion


def statistiques_descriptives(data):
    """Effectif, moyenne, médiane, écart-type, minimum et maximum.

    .std(ddof=1) décrit la dispersion des observations ; ce n'est pas
    l'incertitude sur la moyenne. La moyenne de win est le taux de victoire.
    La moyenne de score compte les nulles comme un demi-point.
    """
    rows = []
    for column in [
        "rating",
        "opponent_rating",
        "elo_diff",
        "score",
        "experience_opening_prior",
    ]:
        values = pd.to_numeric(data[column], errors="coerce")
        rows.append(
            {
                "variable": column,
                "n": values.count(),
                "mean": values.mean(),
                "median": values.median(),
                "std": values.std(ddof=1),
                "min": values.min(),
                "max": values.max(),
            }
        )
    return pd.DataFrame(rows)


def graphiques_simples(data):
    """Quatre figures simples, dont l'ancienne courbe d'expérience conservée."""
    figures = {}
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(data["rating"].dropna(), bins=15, edgecolor="white", color="steelblue")
    ax.set(title="Elo des parties observées", xlabel="Elo", ylabel="Effectif")
    figures["histogramme_elo.png"] = fig

    fig, ax = plt.subplots(figsize=(6, 4))
    counts = (
        data["result"].value_counts().reindex(["Win", "Draw", "Loss"], fill_value=0)
    )
    ax.bar(["Victoire", "Nulle", "Défaite"], counts.to_numpy(), color="steelblue")
    ax.set(title="Résultats observés", ylabel="Effectif")
    figures["effectifs_resultats.png"] = fig

    fig, ax = plt.subplots(figsize=(6, 4))
    means = (
        data.groupby("color", observed=True)["score"].mean().reindex(["white", "black"])
    )
    ax.bar(["Blancs", "Noirs"], means.to_numpy(), color=["steelblue", "darkorange"])
    ax.set(title="Score moyen par couleur", ylabel="Score moyen", ylim=(0, 1))
    figures["score_par_couleur.png"] = fig

    # Le nombre d'observations de chaque classe est exporté avec sa moyenne.
    panel = data.copy()
    panel["experience_bin"] = pd.cut(
        panel["experience_opening_prior"],
        [-1, 0, 1, 4, 9, 1000000],
        labels=["première", "deuxième", "3 à 5", "6 à 10", "11 et plus"],
    )
    experience = (
        panel.groupby("experience_bin", observed=True)
        .agg(
            n=("score", "size"),
            score_mean=("score", "mean"),
            win_rate=("win", "mean"),
        )
        .reset_index()
    )
    experience.to_csv(cfg.RESULTS_DIR / "experience_progression.csv", index=False)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(
        experience["experience_bin"].astype(str), experience["score_mean"], marker="o"
    )
    ax.set(
        title="Expérience observée et score moyen",
        xlabel="Rang de pratique",
        ylabel="Score moyen",
    )
    figures["experience_score.png"] = fig

    for filename, figure in figures.items():
        figure.tight_layout()
        figure.savefig(cfg.RESULTS_DIR / filename, dpi=150)
        plt.close(figure)


def exporter_descriptifs(data):
    """Conserver le descriptif numérique et les tableaux par groupe."""
    statistics = statistiques_descriptives(data)
    statistics.to_csv(cfg.RESULTS_DIR / "statistiques_descriptives.csv", index=False)
    for dimension in ["color", "format_partie", "opening_family", "elo_band"]:
        summary = (
            data.groupby(dimension, observed=True)
            .agg(
                n=("game_id", "size"),
                score_mean=("score", "mean"),
                score_std=("score", "std"),
                win_rate=("win", "mean"),
                rating_mean=("rating", "mean"),
            )
            .reset_index()
        )
        summary.to_csv(
            cfg.RESULTS_DIR / ("description_" + dimension + ".csv"), index=False
        )
    graphiques_simples(data)
    return statistics


## Partie 6 - Exécuter les parties dans l'ordre et indiquer les limites


def analyze(df, run_regressions=None):
    """Entrée unique utilisée par le master, avec sorties consultables une à une."""
    if df.empty:
        raise ValueError("Aucune partie à analyser.")
    enabled = cfg.RUN_REGRESSIONS if run_regressions is None else run_regressions
    frames = creer_dataframes(df)
    data = frames["parties"]
    quality = pd.DataFrame(
        {"variable": data.columns, "missing_pct": data.isna().mean().values * 100}
    )
    quality.to_csv(cfg.RESULTS_DIR / "qualite_donnees.csv", index=False)

    tests = appliquer_chi2(data)
    appliquer_fisher_et_regression(data, enabled)
    exporter_descriptifs(data)

    (cfg.RESULTS_DIR / "LECTURE_RESULTATS.md").write_text(
        "# Lire les résultats\n\n"
        "1. tests_chi2.csv : tableaux catégoriels, effectifs attendus, V de Cramér et Holm.\n"
        "2. fisher/tests_fisher_exact.csv : quatre tableaux 2×2 ; nulles et défaites regroupées.\n"
        "3. regression_multiple_resume.csv : un modèle du score avec répétition, Elo, couleur et cadence. "
        "Le F classique est pédagogique ; le F de Wald groupé est approximatif et exige assez de joueurs.\n"
        "4. statistiques_descriptives.csv et PNG : moyennes, dispersions, effectifs.\n\n"
        "Les parties répétées et les adversaires communs limitent les inférences. "
        "valid ne contrôle que les attentes du chi carré. Aucune analyse ne prouve une cause.\n",
        encoding="utf-8",
    )
    return tests

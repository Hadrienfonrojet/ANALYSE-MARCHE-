"""Trois exercices sur les ouvertures et au maximum trois régressions linéaires.

Exécuter : python analyse.py --demo
L’orthographe du nom de ce fichier reprend celle demandée pour le projet.
"""

import argparse
from pathlib import Path
import json
import hashlib
import platform
import textwrap
import importlib.metadata
import numpy as np
import pandas as pd
from nettoyage import preparer_parties

RESULTATS = {"Win": "victoire", "Loss": "defaite", "Draw": "nulle"}


## Partie 1 — Statistiques descriptives. Taux et effectifs par ouverture sur toute la base.
def statistiques_ouvertures(parties):
    """Une ligne par ouverture connue ; les nulles restent dans le dénominateur."""
    ## Ce DataFrame ne contient que les lignes dont l’ouverture est connue.
    ## L’historique complet reste utilisé pour les séries et les transitions.
    known = parties.dropna(subset=["opening_name"])
    table = known.groupby("opening_name", sort=True).agg(
        n_parties=("game_id", "size"),
        n_joueurs=("user_id", "nunique"),
        victoires=("win", "sum"),
        defaites=("loss", "sum"),
        nulles=("draw", "sum"),
        taux_victoire=("win", "mean"),
        taux_defaite=("loss", "mean"),
        taux_nulle=("draw", "mean"),
        score_moyen=("score", "mean"),
        score_std=("score", "std"),
        classement_moyen=("rating", "mean"),
        ecart_elo_moyen=("elo_diff", "mean"),
    )
    # Ce second taux donne le même poids à chaque joueur au sein de l’ouverture.
    by_user = known.groupby(["opening_name", "user_id"])[["win", "loss", "draw"]].mean()
    balanced = (
        by_user.groupby("opening_name")
        .mean()
        .rename(
            columns={
                "win": "taux_victoire_moyen_joueurs",
                "loss": "taux_defaite_moyen_joueurs",
                "draw": "taux_nulle_moyen_joueurs",
            }
        )
    )
    return table.join(balanced).reset_index()


## Partie 2 — Comparaison temporelle. Un nouveau DataFrame pour une fenêtre temporelle annoncée.
def filtrer_periode(parties, debut, fin):
    """Sélection [début, fin[ en UTC ; la fin est exclue pour éviter les doubles comptes."""
    start, end = pd.to_datetime(debut, utc=True), pd.to_datetime(fin, utc=True)
    if start >= end:
        raise ValueError("La fin de période doit être postérieure au début")
    return parties.loc[parties["date"].ge(start) & parties["date"].lt(end)].copy()


def statistiques_temporelles(parties, debut, fin):
    """Retourner le sous-échantillon et ses taux mensuels par ouverture."""
    intervalle = filtrer_periode(parties, debut, fin)
    intervalle["mois"] = intervalle["date"].dt.strftime("%Y-%m")
    tables = []
    for month, frame in intervalle.groupby("mois", sort=True):
        summary = statistiques_ouvertures(frame)
        summary.insert(0, "mois", month)
        tables.append(summary)
    columns = ["mois"] + statistiques_ouvertures(parties.iloc[:0]).columns.tolist()
    monthly = (
        pd.concat(tables, ignore_index=True)
        if tables
        else pd.DataFrame(columns=columns)
    )
    return intervalle, monthly


## Partie 3 — Séries de résultats. Séries de même résultat avec la même ouverture.
def series_resultats(parties):
    """Mesurer des séries strictement consécutives dans l’historique observé.

    On calcule sur TOUTES les parties triées avant de filtrer une ouverture.
    Un changement de résultat, d’ouverture ou de joueur démarre une autre série.
    Win → Draw → Win donne deux séries de victoire de longueur 1 et une nulle.
    Une ouverture inconnue ou deux dates ex aequo constituent une rupture.
    """
    df = parties.sort_values(["user_id", "date", "game_id"], kind="stable").copy()
    previous = df.shift(1)
    ties = df.duplicated(["user_id", "date"], keep=False)
    same = (
        df["user_id"].eq(previous["user_id"])
        & df["opening_name"].eq(previous["opening_name"])
        & df["result"].eq(previous["result"])
    )
    same = same.fillna(False) & ~ties & ~ties.shift(1, fill_value=False)
    same &= ~df["_chronology_break_before"] & ~df["_chronology_uncertain"]
    df["serie_id"] = (~same).cumsum()
    detail = (
        df.loc[~df["_chronology_uncertain"]]
        .dropna(subset=["opening_name"])
        .groupby("serie_id", sort=False)
        .agg(
            user_id=("user_id", "first"),
            opening_name=("opening_name", "first"),
            result=("result", "first"),
            longueur=("game_id", "size"),
            debut=("date", "min"),
            fin=("date", "max"),
        )
        .reset_index()
    )
    maxima = (
        detail.groupby(["opening_name", "result"])["longueur"].max().unstack("result")
    )
    maxima = maxima.reindex(columns=list(RESULTATS), fill_value=0).fillna(0).astype(int)
    maxima = maxima.rename(
        columns={r: "max_serie_" + name for r, name in RESULTATS.items()}
    ).reset_index()
    return detail, maxima


## Partie 4 — Trois régressions linéaires sur un même échantillon


def preparer_regressions(parties):
    """Réutiliser les transitions immédiates, puis exprimer l’écart Elo pour 100 points.

    La construction temporelle est définie une seule fois dans le projet. Le
    filtrage des valeurs de contrôle manquantes intervient ensuite, sans recréer
    de fausses parties voisines.
    """
    from Analyse_repetition_ouverture import creer_transitions

    df = creer_transitions(parties)
    df["elo_diff_100"] = df["elo_diff_next"] / 100
    return df


def regressions_lineaires(parties):
    """Trois modèles de probabilité linéaire, une équation pour chaque résultat.

    Mêmes observations et contrôles pour Win, Loss et Draw. Les équations sont
    complémentaires car les trois indicateurs somment à 1. Les coefficients sont
    interprétés en points de probabilité. Les erreurs-types sont groupées par compte.
    """
    import statsmodels.formula.api as smf

    data = preparer_regressions(parties)
    required = [
        "win_next",
        "loss_next",
        "draw_next",
        "repeat_opening",
        "win",
        "elo_diff_100",
        "is_white_next",
        "format_partie_next",
        "opening_family_next",
        "user_id",
    ]
    ## Former UNE table complète commune aux trois modèles, puis garder ses groupes.
    ## Ainsi une valeur manquante ne désaligne pas les lignes et les identifiants de joueur.
    sample = data[required].dropna().copy()
    for c in [
        "win_next",
        "loss_next",
        "draw_next",
        "repeat_opening",
        "win",
        "elo_diff_100",
        "is_white_next",
    ]:
        sample[c] = pd.to_numeric(sample[c], errors="coerce").astype(float)
    sample = sample.replace([np.inf, -np.inf], np.nan).dropna()
    control = "repeat_opening + win + elo_diff_100 + is_white_next + C(format_partie_next) + C(opening_family_next)"
    diagnostic, coefficients = [], []
    ## Seule la variable expliquée change : victoire, défaite, puis nulle.
    for outcome, french in [
        ("win_next", "victoire"),
        ("loss_next", "defaite"),
        ("draw_next", "nulle"),
    ]:
        info = {
            "modele": french,
            "n_transitions": len(sample),
            "n_joueurs": sample["user_id"].nunique(),
            "status": "non_estimable",
            "formule": outcome + " ~ " + control,
        }
        if len(sample) < 30 or sample[outcome].nunique() < 2:
            info["motif"] = "Échantillon complet insuffisant ou résultat constant"
            diagnostic.append(info)
            continue
        model = smf.ols(info["formule"], data=sample)
        if (
            np.linalg.matrix_rank(model.exog) < model.exog.shape[1]
            or len(sample) < 5 * model.exog.shape[1]
        ):
            info["motif"] = (
                "Colinéarité ou trop de paramètres pour les observations disponibles"
            )
            diagnostic.append(info)
            continue
        clustered = info["n_joueurs"] >= 20
        fitted = (
            model.fit(
                cov_type="cluster", cov_kwds={"groups": sample["user_id"]}, use_t=True
            )
            if clustered
            else model.fit()
        )
        info.update(
            status="estime",
            r2=float(fitted.rsquared),
            inferer=clustered,
            predictions_hors_0_1=int(
                ((fitted.fittedvalues < 0) | (fitted.fittedvalues > 1)).sum()
            ),
        )
        interval = fitted.conf_int()
        for term in fitted.params.index:
            coefficients.append(
                {
                    "modele": french,
                    "variable": term,
                    "coefficient": fitted.params[term],
                    "effet_points": 100 * fitted.params[term],
                    "se_groupee": fitted.bse[term] if clustered else np.nan,
                    "p_groupee": fitted.pvalues[term] if clustered else np.nan,
                    "borne_inf_points": (
                        100 * interval.loc[term, 0] if clustered else np.nan
                    ),
                    "borne_sup_points": (
                        100 * interval.loc[term, 1] if clustered else np.nan
                    ),
                }
            )
        if not clustered:
            info["motif"] = (
                "Coefficients affichés ; inférence groupée masquée pour moins de 20 comptes"
            )
        diagnostic.append(info)
    coefficient_columns = [
        "modele",
        "variable",
        "coefficient",
        "effet_points",
        "se_groupee",
        "p_groupee",
        "borne_inf_points",
        "borne_sup_points",
    ]
    result = pd.DataFrame(coefficients, columns=coefficient_columns)
    result["p_repetition_holm"] = np.nan
    central = result["variable"].eq("repeat_opening") & result["p_groupee"].notna()
    if central.any():
        from statsmodels.stats.multitest import multipletests

        result.loc[central, "p_repetition_holm"] = multipletests(
            result.loc[central, "p_groupee"], method="holm"
        )[1]
    return pd.DataFrame(diagnostic), result


## Partie 5 — Exporter les tableaux et produire trois graphiques simples


def exporter_tableaux(
    output, parties, bilan, overview, intervalle, monthly, runs, maxima, window_maxima
):
    """Conserver les tableaux des trois exercices, avec leurs effectifs et leurs taux."""
    tables = {
        "exercice1_ouvertures": overview,
        "exercice2_mensuel": monthly,
        "exercice2_intervalle_resume": statistiques_ouvertures(intervalle),
        "exercice3_series": runs,
        "exercice3_maxima": maxima,
        "exercice3_maxima_intervalle": window_maxima,
    }
    for name, table in tables.items():
        table.to_csv(output / (name + ".csv"), index=False)
    parties.to_parquet(output / "parties_nettoyees.parquet", index=False)
    intervalle.to_parquet(output / "nouveau_jeu_intervalle.parquet", index=False)
    pd.DataFrame([bilan]).to_csv(output / "bilan_nettoyage.csv", index=False)
    parties[["rating", "opponent_rating", "elo_diff", "score"]].describe().to_csv(
        output / "descriptifs_numeriques.csv"
    )


def tests_repetition(parties, output):
    """Comparer trois historiques distincts et corriger leurs tests par Holm.

    La correction ne suppose pas que les trois tests soient indépendants. Elle
    ne corrige pas la dépendance des parties d’un même joueur à l’intérieur d’un test.
    """
    from Analyse_repetition_ouverture import (
        preparer_cadres,
        taux_apres_victoire,
        tester_table,
    )
    from statsmodels.stats.multitest import multipletests

    tests, rates = [], {}
    for name, transitions in preparer_cadres(parties).items():
        selected, rate = taux_apres_victoire(transitions)
        result, observed, expected = tester_table(selected)
        tests.append({"cadre": name, **result})
        rates[name] = rate
        rate.to_csv(output / f"taux_repetition_{name}.csv")
        observed.to_csv(output / f"chi2_observe_{name}.csv")
        expected.to_csv(output / f"chi2_attendu_{name}.csv")
    tests = pd.DataFrame(tests)
    for p in ["p_chi2", "p_fisher"]:
        valid = tests[p].notna()
        tests[p + "_holm"] = np.nan
        if valid.any():
            tests.loc[valid, p + "_holm"] = multipletests(
                tests.loc[valid, p], method="holm"
            )[1]
    tests.to_csv(output / "tests_repetition.csv", index=False)
    return tests, rates


def tracer_resultats(overview, monthly, maxima, output):
    """Taux par ouverture, évolution des victoires et maxima des séries."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    top = overview.sort_values(
        ["n_parties", "opening_name"], ascending=[False, True]
    ).head(4)["opening_name"]
    short = overview.set_index("opening_name").reindex(top)
    if len(short):
        short.index = [textwrap.fill(str(name), 25) for name in short.index]
        ax = short[["taux_victoire", "taux_defaite", "taux_nulle"]].plot.bar(
            figsize=(10, 5), rot=0, ylim=(0, 1)
        )
        ax.set(
            xlabel="Ouverture",
            ylabel="Proportion des parties",
            title="Résultats par ouverture, quatre ouvertures les plus jouées",
        )
        ax.legend(["Victoire", "Défaite", "Nulle"])
        plt.tight_layout()
        plt.savefig(output / "taux_ouvertures.png", dpi=140)
        plt.close()
    if not monthly.empty:
        pivot = monthly[monthly.opening_name.isin(top)].pivot(
            index="mois", columns="opening_name", values="taux_victoire"
        )
        ax = pivot.plot(marker="o", figsize=(10, 4), ylim=(0, 1))
        ax.set(
            ylabel="Taux de victoire",
            xlabel="Mois",
            title="Évolution dans la fenêtre sélectionnée",
        )
        ax.set_xticks(range(len(pivot.index)), pivot.index.tolist())
        plt.tight_layout()
        plt.savefig(output / "evolution_victoires.png", dpi=140)
        plt.close()
    if not maxima.empty:
        ax = (
            maxima.set_index("opening_name")
            .reindex(top)[
                ["max_serie_victoire", "max_serie_defaite", "max_serie_nulle"]
            ]
            .plot.bar(figsize=(10, 5), rot=0)
        )
        ax.set(
            ylabel="Nombre de parties consécutives",
            xlabel="Ouverture",
            title="Séries maximales observées",
        )
        ax.set_xticklabels([textwrap.fill(str(name), 25) for name in top], rotation=0)
        ax.legend(["Victoires", "Défaites", "Nulles"])
        plt.tight_layout()
        plt.savefig(output / "series_maximales.png", dpi=140)
        plt.close()


def ecrire_manifeste(frame, output, debut, fin):
    """Documenter l’environnement et l’empreinte des données réellement utilisées."""
    versions = {
        package: importlib.metadata.version(package)
        for package in [
            "numpy",
            "pandas",
            "scipy",
            "statsmodels",
            "matplotlib",
            "pyarrow",
            "python-chess",
        ]
    }
    digest = hashlib.sha256(
        frame.to_csv(index=False, lineterminator="\n").encode()
    ).hexdigest()
    manifest = {
        "python": platform.python_version(),
        "versions": versions,
        "debut_inclus": str(debut),
        "fin_exclue": str(fin),
        "empreinte_table_entree_csv": digest,
        "note": "Fenêtre = sous-échantillon temporel ; les séries y sont mesurées à partir de la borne de début.",
    }
    (output / "reproductibilite.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2)
    )


## Partie 6 — Enchaîner les étapes sans cacher leurs résultats


def analyser(
    frame, output_dir, debut="2024-02-01", fin="2024-03-01", run_regression=True
):
    """Un parcours court : nettoyer, décrire, comparer, modéliser, exporter.

    Les fonctions des parties précédentes sont utilisables séparément dans le
    notebook. Cette fonction les rassemble pour une exécution reproductible.
    """
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise FileExistsError("Utiliser un nouveau dossier de résultats")

    parties, bilan = preparer_parties(frame)
    if parties.empty:
        raise ValueError("Aucune partie valide après nettoyage")

    # Chaque nom désigne un DataFrame dont on peut afficher les premières lignes.
    overview = statistiques_ouvertures(parties)
    intervalle, monthly = statistiques_temporelles(parties, debut, fin)
    runs, maxima = series_resultats(parties)
    _, window_maxima = series_resultats(intervalle)
    exporter_tableaux(
        output,
        parties,
        bilan,
        overview,
        intervalle,
        monthly,
        runs,
        maxima,
        window_maxima,
    )

    tests, rates = tests_repetition(parties, output)
    models, coef = (
        regressions_lineaires(parties)
        if run_regression
        else (pd.DataFrame(), pd.DataFrame())
    )
    models.to_csv(output / "regressions_diagnostics.csv", index=False)
    coef.to_csv(output / "regressions_coefficients.csv", index=False)
    tracer_resultats(overview, monthly, maxima, output)
    ecrire_manifeste(frame, output, debut, fin)
    return {
        "parties": parties,
        "bilan": bilan,
        "ouvertures": overview,
        "intervalle": intervalle,
        "mensuel": monthly,
        "series": runs,
        "maxima": maxima,
        "maxima_intervalle": window_maxima,
        "tests": tests,
        "taux": rates,
        "modeles": models,
        "coefficients": coef,
    }


def main(argv=None):
    """Point d’entrée des trois exercices sur la base fournie ou la démonstration."""
    import config as cfg

    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--demo", action="store_true")
    source.add_argument("--input", type=Path)
    parser.add_argument("--debut", default="2024-01-15")
    parser.add_argument("--fin", default="2024-03-01")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    path = cfg.ROOT / "data_demo/parties_demo.csv" if args.demo else args.input
    raw = pd.read_csv(path) if path.suffix.lower() == ".csv" else pd.read_parquet(path)
    directory = args.output if args.output else cfg.create_run() / "Resultats"
    result = analyser(raw, directory, args.debut, args.fin)
    print("Nettoyage", result["bilan"])
    print(result["ouvertures"].to_string(index=False))
    print(result["maxima"].to_string(index=False))
    print("Résultats enregistrés dans", directory)


if __name__ == "__main__":
    main()

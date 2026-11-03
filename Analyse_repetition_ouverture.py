"""Après une victoire, répéter l’ouverture est-il associé à gagner la suivante ?

Ce module complète le notebook initial, il ne remplace pas ses analyses Hot Hand.
Les tests groupés sont exploratoires ; le bootstrap et la régression regroupent
les observations par compte, sans régler toutes les dépendances entre adversaires.
"""

from pathlib import Path
import json
import warnings
import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, fisher_exact
from statsmodels.stats.multitest import multipletests
from Nettoyage_donnees import clean_games


## Partie 1 - Construire les DataFrames de transitions utiles


def creer_transitions(frame, meme_couleur=False):
    """Une ligne = une partie courante accompagnée de la suivante OBSERVÉE.

    meme_couleur=True cherche la prochaine de cette couleur : il peut exister
    des matchs intermédiaires. On ne l’appelle donc pas « victoire successive ».
    """
    df = clean_games(frame)
    if "game_id" not in df:
        raise ValueError(
            "game_id requis pour distinguer la dernière partie d’une transition"
        )
    for name in ["rating", "format_partie", "elo_diff"]:
        if name not in df:
            df[name] = np.nan
    keys = ["user_id", "color"] if meme_couleur else ["user_id"]
    groups = df.groupby(keys, sort=False)
    for name in [
        "game_id",
        "timestamp",
        "result",
        "win",
        "opening_name",
        "color",
        "format_partie",
        "elo_diff",
        "rating",
    ]:
        ## Créer UNE COLONNE contenant la valeur de la prochaine partie du même groupe.
        ## Par exemple opening_name_next n’est pas une liste de parties du joueur.
        df[name + "_next"] = groups[name].shift(-1)
    df["is_white_next"] = df["color_next"].map({"white": 1.0, "black": 0.0})
    df["delay_minutes"] = (df["timestamp_next"] - df["timestamp"]) / 60000
    df["same_color"] = df["color"].eq(df["color_next"])
    opening = df["opening_name"].astype("string").str.strip()
    following = df["opening_name_next"].astype("string").str.strip()
    unknown = {"", "Inconnue", "Unknown", "UNKNOWN", "None"}
    df["known_pair"] = (
        opening.notna()
        & following.notna()
        & ~opening.isin(unknown)
        & ~following.isin(unknown)
    )
    ## État manquant si une des ouvertures est inconnue : jamais un faux changement.
    df["repeat_opening"] = (
        opening.eq(following).where(df["known_pair"]).astype("Float64")
    )
    ## Le filtrage est fait APRÈS shift : ne pas sauter une nulle ou une ouverture inconnue.
    transitions = df[df["game_id_next"].notna() & df["delay_minutes"].gt(0)].copy()
    transitions["history"] = (
        "prochaine_meme_couleur" if meme_couleur else "immediat_observe"
    )
    return transitions


def preparer_cadres(frame):
    """Trois DataFrames : immédiat, immédiat même couleur, prochaine même couleur."""
    immediate = creer_transitions(frame)
    return {
        "immediat": immediate,
        "immediat_meme_couleur": immediate[immediate["same_color"]].copy(),
        "prochaine_meme_couleur": creer_transitions(frame, meme_couleur=True),
    }


## Partie 2 - Définir χ² et Fisher exact, avec leurs conditions


def tester_table(frame, x="repeat_opening", y="win_next"):
    """Table observée, effectifs attendus et p-values ; association, pas causalité."""
    pair = frame[[x, y]].dropna()
    observed = pd.crosstab(pair[x], pair[y])
    result = {
        "n": len(pair),
        "chi2": np.nan,
        "ddl": np.nan,
        "p_chi2": np.nan,
        "cramer_v": np.nan,
        "min_expected": np.nan,
        "expected_ge5": False,
        "odds_ratio_fisher": np.nan,
        "p_fisher": np.nan,
        "status": "non_estimable",
    }
    expected = pd.DataFrame(index=observed.index, columns=observed.columns, dtype=float)
    if min(observed.shape, default=0) < 2:
        return result, observed, expected
    stat, pvalue, ddl, exp = chi2_contingency(observed, correction=False)
    expected.loc[:, :] = exp
    result.update(
        chi2=float(stat),
        ddl=int(ddl),
        p_chi2=float(pvalue),
        cramer_v=float(
            np.sqrt(
                stat
                / (
                    observed.values.sum()
                    * min(observed.shape[0] - 1, observed.shape[1] - 1)
                )
            )
        ),
        min_expected=float(exp.min()),
        expected_ge5=bool((exp >= 5).all()),
        status="exploratoire_dependance_joueurs",
    )
    if observed.shape == (2, 2):
        odds, fisher_p = fisher_exact(observed.to_numpy(), alternative="two-sided")
        result.update(odds_ratio_fisher=float(odds), p_fisher=float(fisher_p))
    ## Fisher teste un tableau 2×2 ; il ne corrige PAS la répétition des observations par joueur.
    return result, observed, expected


## Partie 3 - Après victoire : appliquer le test, puis quantifier l’écart de taux


def taux_apres_victoire(transitions):
    """Le DataFrame sélectionné contient les transitions après une victoire connue."""
    selected = transitions[
        transitions["result"].eq("Win") & transitions["known_pair"]
    ].copy()
    summary = selected.groupby("repeat_opening", observed=True).agg(
        n=("win_next", "size"),
        joueurs=("user_id", "nunique"),
        victoires_suivantes=("win_next", "sum"),
        taux_victoire=("win_next", "mean"),
    )
    return selected, summary


def bootstrap_joueurs(selected, simulations=1000, seed=42):
    """IC percentile de l’écart répéter − changer, par rééchantillonnage des comptes.

    Tous les enchaînements d’un compte sont rééchantillonnés ensemble. Ce complément
    traite une partie de la dépendance ; les adversaires partagés et la sélection
    des ouvertures restent des limites. Ce n’est pas un test de causalité.
    """
    counts = selected.groupby(["user_id", "repeat_opening"])["win_next"].agg(
        ["sum", "count"]
    )
    users = selected["user_id"].unique()
    answer = {
        "joueurs": len(users),
        "difference": np.nan,
        "ci_low": np.nan,
        "ci_high": np.nan,
        "simulations_valides": 0,
    }
    if len(users) == 0:
        return answer
    stats = []
    for value in [0, 1]:
        sub = selected[selected["repeat_opening"].eq(value)]
        stats.append(sub["win_next"].mean())
    answer["difference"] = stats[1] - stats[0]
    if len(users) < 20 or not np.isfinite(answer["difference"]):
        return answer  ## Vingt comptes est un garde-fou pédagogique, pas une garantie.
    arrays = []
    for value in [0, 1]:
        part = counts.xs(value, level="repeat_opening").reindex(users, fill_value=0)
        arrays.append(part[["sum", "count"]].to_numpy(dtype=float))
    rng = np.random.default_rng(seed)
    differences = []
    for _ in range(simulations):
        sample = rng.integers(0, len(users), len(users))
        a, b = (arr[sample].sum(axis=0) for arr in arrays)
        if a[1] and b[1]:
            differences.append(b[0] / b[1] - a[0] / a[1])
    if differences:
        answer.update(
            ci_low=float(np.quantile(differences, 0.025)),
            ci_high=float(np.quantile(differences, 0.975)),
            simulations_valides=len(differences),
        )
    return answer


## Partie 4 - Une régression multivariable simple, sur les transitions immédiates


def regression_ajustee(selected):
    """Logistique victoire suivante ~ répétition + écart Elo + couleur + cadence.

    L’échantillon est limité aux transitions APRÈS victoire. Les erreurs-types sont
    regroupées par compte ; pas de p-value naïve si trop peu de comptes. Ce modèle
    étudie la répétition, pas le classement causal des familles d’ouvertures.
    """
    import statsmodels.api as sm
    import statsmodels.formula.api as smf

    needed = [
        "win_next",
        "repeat_opening",
        "elo_diff_next",
        "is_white_next",
        "format_partie_next",
        "user_id",
    ]
    sample = selected[needed].copy()
    for c in ["win_next", "repeat_opening", "elo_diff_next", "is_white_next"]:
        sample[c] = pd.to_numeric(sample[c], errors="coerce").astype(float)
    sample = sample.replace([np.inf, -np.inf], np.nan).dropna()
    info = {
        "n": len(sample),
        "joueurs": sample["user_id"].nunique(),
        "status": "non_estimable",
    }
    coefficients = pd.DataFrame()
    if len(sample) < 50 or info["joueurs"] < 20 or sample["win_next"].nunique() < 2:
        info["reason"] = (
            "Effectifs, comptes ou classes insuffisants ; Elo adverse parfois absent des anciens parquets."
        )
        return info, coefficients
    sample["elo_diff_100"] = sample["elo_diff_next"] / 100
    model = smf.glm(
        "win_next ~ repeat_opening + elo_diff_100 + is_white_next + C(format_partie_next)",
        data=sample,
        family=sm.families.Binomial(),
    )
    if (
        np.linalg.matrix_rank(model.exog) < model.exog.shape[1]
        or len(sample) < 10 * model.exog.shape[1]
    ):
        info["reason"] = (
            "Variables constantes/colinéaires ou trop de paramètres pour cet échantillon."
        )
        return info, coefficients
    try:
        with warnings.catch_warnings():
            warnings.simplefilter(
                "error", sm.tools.sm_exceptions.PerfectSeparationWarning
            )
            fit = model.fit(cov_type="cluster", cov_kwds={"groups": sample["user_id"]})
        if not fit.converged or not np.isfinite(fit.bse).all():
            raise ValueError("Non-convergence ou incertitudes non finies")
        interval = fit.conf_int()
        coefficients = pd.DataFrame(
            {
                "variable": fit.params.index,
                "coefficient_logit": fit.params.values,
                "odds_ratio": np.exp(fit.params.values),
                "se_groupees": fit.bse.values,
                "p_groupee": fit.pvalues.values,
                "ci_coefficient_low": interval[0].values,
                "ci_coefficient_high": interval[1].values,
            }
        )
        info.update(
            status="estime_association_ajustee",
            formula="win_next ~ repeat_opening + elo_diff_100 + is_white_next + C(format_partie_next)",
        )
    except (
        ValueError,
        np.linalg.LinAlgError,
        sm.tools.sm_exceptions.PerfectSeparationWarning,
    ) as error:
        info["reason"] = str(error)
    return info, coefficients


## Partie 5 - Descriptifs et graphiques lisibles, puis export des résultats


def descriptifs(parties):
    """Moyenne, médiane, écart-type d’échantillon, min/max ; une variable par ligne."""
    rows = []
    for name in ["rating", "opponent_rating", "elo_diff", "score"]:
        if name in parties:
            col = pd.to_numeric(parties[name], errors="coerce")
            rows.append(
                {
                    "variable": name,
                    "n": col.count(),
                    "mean": col.mean(),
                    "median": col.median(),
                    "std": col.std(),
                    "min": col.min(),
                    "max": col.max(),
                }
            )
    return pd.DataFrame(rows)


def analyser(frame, output_dir, run_regression=True, bootstrap_simulations=1000):
    """Exécuter les trois cadres, sans modifier le DataFrame ni supprimer un fichier."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise FileExistsError(
            "Choisir un dossier de résultats vide pour conserver les anciens résultats."
        )
    parties = clean_games(frame)
    parties.to_parquet(output / "parties_nettoyees.parquet", index=False)
    descriptifs(parties).to_csv(output / "statistiques_descriptives.csv", index=False)
    quality = {
        "lignes_joueur_partie": len(parties),
        "parties_uniques": parties["game_id"].nunique(),
        "joueurs": parties["user_id"].nunique(),
        "nulles": int(parties["result"].eq("Draw").sum()),
        "source": "successives observees ; continuite de collecte non garantie",
    }
    (output / "qualite.json").write_text(
        json.dumps(quality, ensure_ascii=False, indent=2)
    )
    cadres = preparer_cadres(parties)
    tests, bootstrap, rates = [], [], {}
    for name, transitions in cadres.items():
        selected, summary = taux_apres_victoire(transitions)
        rates[name] = summary
        summary.to_csv(output / f"taux_{name}.csv")
        transitions.to_parquet(output / f"transitions_{name}.parquet", index=False)
        result, observed, expected = tester_table(selected)
        result.update(
            cadre=name, question="apres_victoire_repetition_et_victoire_suivante"
        )
        tests.append(result)
        observed.to_csv(output / f"observe_{name}.csv")
        expected.to_csv(output / f"attendu_{name}.csv")
        bootstrap.append(
            {"cadre": name, **bootstrap_joueurs(selected, bootstrap_simulations)}
        )
        if not summary.empty:
            ax = (
                summary["taux_victoire"]
                .rename(index={0.0: "Changer", 1.0: "Répéter"})
                .plot.bar(ylim=(0, 1), rot=0)
            )
            ax.set(title=f"Après victoire — {name}", ylabel="Taux de victoire suivante")
            plt.tight_layout()
            plt.savefig(output / f"taux_{name}.png")
            plt.close()
    tests = pd.DataFrame(tests)
    for p in ["p_chi2", "p_fisher"]:
        valid = tests[p].notna()
        tests[p + "_holm"] = np.nan
        if valid.any():
            tests.loc[valid, p + "_holm"] = multipletests(
                tests.loc[valid, p], method="holm"
            )[1]
    tests.to_csv(output / "tests_repetition.csv", index=False)
    pd.DataFrame(bootstrap).to_csv(output / "bootstrap_joueurs.csv", index=False)
    chosen, _ = taux_apres_victoire(cadres["immediat"])
    info, coefficients = (
        regression_ajustee(chosen)
        if run_regression
        else ({"status": "desactivee"}, pd.DataFrame())
    )
    (output / "regression_diagnostic.json").write_text(
        json.dumps(info, ensure_ascii=False, indent=2)
    )
    coefficients.to_csv(output / "regression_coefficients.csv", index=False)
    parties.groupby(["color", "opening_name"], dropna=False).agg(
        n=("score", "size"),
        score_mean=("score", "mean"),
        score_std=("score", "std"),
        win_rate=("win", "mean"),
    ).to_csv(output / "descriptifs_ouvertures_couleur.csv")
    if (
        "rating" in parties
        and pd.to_numeric(parties["rating"], errors="coerce").notna().any()
    ):
        pd.to_numeric(parties["rating"], errors="coerce").hist(bins=20)
        plt.xlabel("Classement du joueur")
        plt.ylabel("Nombre de parties")
        plt.tight_layout()
        plt.savefig(output / "histogramme_rating.png")
        plt.close()
    parties["result"].value_counts().reindex(
        ["Win", "Draw", "Loss"], fill_value=0
    ).plot.bar(rot=0)
    plt.ylabel("Nombre de parties")
    plt.tight_layout()
    plt.savefig(output / "resultats.png")
    plt.close()
    (output / "LECTURE_RESULTATS.md").write_text(
        "# Lire les résultats\n\nLes tests répondent à : après victoire, répéter est-il associé à gagner la suivante ?\nLes tableaux indiquent les effectifs et taux ; les χ²/Fisher restent exploratoires car les comptes contribuent plusieurs matchs. Holm corrige les trois cadres, séparément pour χ² et Fisher.\nLe bootstrap rééchantillonne les comptes ; la logistique ajuste sur Elo relatif, couleur et cadence de la suivante. Le diagnostic explique les modèles non estimables.\nProchaine même couleur n’est pas nécessairement la partie suivante immédiate. Les trous de collecte, les adversaires partagés et le choix de stratégie limitent toute conclusion causale.\n"
    )
    return {
        "tests": tests,
        "taux": rates,
        "bootstrap": pd.DataFrame(bootstrap),
        "regression": info,
        "coefficients": coefficients,
        "cadres": cadres,
    }

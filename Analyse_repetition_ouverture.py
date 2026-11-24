"""Fonctions de transition et tests exploratoires par répétition d’ouverture."""

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, fisher_exact
from Nettoyage_donnees import clean_games


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


def analyser(frame, output_dir, run_regression=True):
    """Lancer les trois exercices et les trois modèles linéaires du projet."""
    from analyse_statisitques import analyser as lancer

    return lancer(frame, output_dir, run_regression=run_regression)

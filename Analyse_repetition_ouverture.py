"""Fonctions de transition et tests exploratoires par répétition d’ouverture."""

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency
from nettoyage import clean_games


## Partie 1 — Construire les DataFrames de parties successives


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
        "date",
        "timestamp",
        "loss",
        "draw",
        "opening_family",
        "is_white",
        "_chronology_segment",
        "_date_ambiguous",
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
    # Comparer seulement des parties dont l’ordre est connu et sans rejet entre elles.
    valide = df["game_id_next"].notna() & df["delay_minutes"].gt(0)
    valide &= df["_chronology_segment"].eq(df["_chronology_segment_next"])
    valide &= ~df["_date_ambiguous"] & ~df["_date_ambiguous_next"].eq(True)
    valide &= ~df["_chronology_uncertain"]
    if meme_couleur:
        valide &= df["color"].notna()
    transitions = df.loc[valide].copy()
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


## Partie 2 — Définir le test du χ²


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
        "status": "non_estimable",
    }
    expected = pd.DataFrame(index=observed.index, columns=observed.columns, dtype=float)
    if min(observed.shape, default=0) < 2:
        return result, observed, expected
    ## H0 : la répétition et le résultat suivant sont indépendants.
    ## Attendu d’une case = total de sa ligne × total de sa colonne / total général.
    ## χ² = somme de (observé − attendu)² / attendu ; ddl = (lignes − 1) × (colonnes − 1).
    ## Ici le défaut est un tableau 2×2 : victoire suivante contre défaite OU nulle.
    ## Les comptes contribuent plusieurs fois : les p-values restent exploratoires.
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
    return result, observed, expected


## Partie 3 — Appliquer la comparaison après une victoire


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


## Partie 4 — Complément : rééchantillonner des joueurs entiers


def analyser(frame, output_dir, run_regression=True):
    """Lancer les trois exercices et les trois modèles linéaires du projet."""
    from analyse import analyser as lancer

    return lancer(frame, output_dir, run_regression=run_regression)

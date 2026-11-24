"""Préparer les parties sans effacer les sources ni inventer de succession.

Entrée : un DataFrame de parties brutes ou identifiées.
Sortie : un DataFrame normalisé et un dictionnaire de bilan.
Les colonnes internes commençant par _chronology protègent les analyses de séries.
"""

from pathlib import Path

import numpy as np
import pandas as pd

RESULTATS = {
    "win": "Win",
    "victoire": "Win",
    "loss": "Loss",
    "defeat": "Loss",
    "défaite": "Loss",
    "defaite": "Loss",
    "draw": "Draw",
    "nul": "Draw",
    "nulle": "Draw",
}
STATUTS_SANS_RESULTAT = {"created", "started", "aborted", "nostart", "unknownfinish"}


## Partie 1 — Harmoniser les dates et les identifiants


def convertir_dates(valeurs, millisecondes=False):
    """Accepter les dates ISO et les timestamps en secondes ou millisecondes.

    Toutes les dates retournées utilisent le fuseau UTC. Une valeur illisible
    devient NaT : on la compte dans le bilan au lieu de lui inventer une date.
    """
    if pd.api.types.is_datetime64_any_dtype(valeurs):
        return pd.to_datetime(valeurs, errors="coerce", utc=True)

    nombres = pd.to_numeric(valeurs, errors="coerce")
    dates = pd.to_datetime(
        valeurs.where(nombres.isna()), errors="coerce", utc=True, format="mixed"
    )
    en_ms = nombres.abs().ge(100_000_000_000) | millisecondes
    for masque, unite in [(en_ms, "ms"), (~en_ms, "s")]:
        selection = nombres.notna() & masque
        dates.loc[selection] = pd.to_datetime(
            nombres.loc[selection], unit=unite, errors="coerce", utc=True
        )
    return dates


def normaliser_identifiants(df):
    """Créer les colonnes normalisées sur la copie de travail reçue."""
    df["user_id"] = (
        df["user_id"].astype("string").str.strip().str.lower().replace("", pd.NA)
    )
    colonne_date = next(
        (c for c in ["date", "timestamp_ms", "timestamp"] if c in df), None
    )
    if colonne_date is None:
        raise ValueError("Date requise : date ISO, timestamp_ms ou timestamp")
    df["date"] = convertir_dates(df[colonne_date], colonne_date == "timestamp_ms")
    reconstruits = 0
    if "game_id" not in df:
        df["game_id"] = df["user_id"] + "_" + df["date"].astype("string")
        reconstruits = len(df)
    df["game_id"] = df["game_id"].astype("string").str.strip().replace("", pd.NA)
    df["result"] = df["result"].astype("string").str.strip().str.lower().map(RESULTATS)
    return df, reconstruits


## Partie 2 — Écarter les lignes invalides en conservant les ruptures d’historique


def selectionner_parties(df, bilan):
    """Ne jamais raccorder les deux côtés d’une partie rejetée.

    Un rejet daté crée une rupture avant la prochaine partie conservée. Un rejet
    non datable d’un compte connu rend son ordre incertain : ses statistiques
    descriptives restent utilisables, mais ses transitions et séries sont écartées.
    Les doublons exacts de compte/partie ne créent pas de rupture artificielle.
    """
    identite = df["user_id"].notna() & df["date"].notna() & df["game_id"].notna()
    valide = identite & df["result"].notna()
    if "status" in df:
        statut = df["status"].astype("string").str.strip().str.lower()
        valide &= ~statut.isin(STATUTS_SANS_RESULTAT)
    if "variant" in df:
        variante = df["variant"].astype("string").str.strip().str.lower()
        valide &= variante.isna() | variante.eq("standard")

    bilan["lignes_invalides_rejetees"] = int((~valide).sum())
    bilan["identifiants_manquants_rejetes"] = int(df["game_id"].isna().sum())
    comptes_non_dates = df.loc[df["date"].isna() & df["user_id"].notna(), "user_id"]
    df["_rejet"] = ~valide
    df["_chronology_uncertain"] = df.get(
        "_chronology_uncertain", pd.Series(False, index=df.index)
    ).fillna(False).astype(bool) | df["user_id"].isin(comptes_non_dates)
    if "_chronology_break_before" not in df:
        df["_chronology_break_before"] = False

    # Un doublon n’ajoute pas une partie à l’historique. On préfère sa ligne valide.
    avant = len(df)
    df = df.sort_values("_rejet", kind="stable")
    doublon = df.duplicated(["user_id", "game_id"]) & df["game_id"].notna()
    df = df.loc[~doublon].copy()
    bilan["doublons_retires"] = avant - len(df)
    df = df.sort_values(["user_id", "date", "game_id"], kind="stable")

    # Ce compteur augmente à chaque rejet : deux valeurs différentes signalent un trou.
    df["_rejets_cumules"] = df.groupby("user_id", sort=False)["_rejet"].cumsum()
    df = df.loc[~df["_rejet"]].copy()
    precedent = df.groupby("user_id", sort=False)["_rejets_cumules"].shift(1)
    rupture = df["_rejets_cumules"].gt(precedent.fillna(0))
    df["_chronology_break_before"] = (
        df["_chronology_break_before"].fillna(False).astype(bool) | rupture
    )
    df["_chronology_segment"] = df.groupby("user_id", sort=False)[
        "_chronology_break_before"
    ].cumsum()
    df["_date_ambiguous"] = df.duplicated(["user_id", "date"], keep=False)
    return df.drop(columns=["_rejet", "_rejets_cumules"]).reset_index(drop=True)


## Partie 3 — Créer les variables descriptives et les indicateurs de résultat


def creer_variables(df):
    """Ajouter une colonne par variable ; aucune de ces colonnes n’est une liste de parties."""
    df["timestamp"] = df["date"].astype("int64") // 1_000_000
    df["opening_name"] = df["opening_name"].astype("string").str.strip()
    inconnue = (
        df["opening_name"].str.lower().isin(["", "inconnue", "unknown", "none", "nan"])
    )
    df["opening_name"] = df["opening_name"].mask(inconnue)
    df["opening_family"] = df["opening_name"].str.split(":").str[0].str.strip()

    for colonne in ["rating", "opponent_rating"]:
        valeurs = df[colonne] if colonne in df else pd.Series(np.nan, index=df.index)
        df[colonne] = pd.to_numeric(valeurs, errors="coerce").replace(
            [np.inf, -np.inf], np.nan
        )
        df.loc[df[colonne] < 0, colonne] = np.nan
    df["elo_diff"] = df["rating"] - df["opponent_rating"]

    categories = {
        "color": ["white", "black"],
        "format_partie": ["bullet", "blitz", "rapid", "classical"],
    }
    for colonne, autorisees in categories.items():
        if colonne not in df:
            df[colonne] = pd.NA
        df[colonne] = df[colonne].astype("string").str.strip().str.lower()
        df[colonne] = df[colonne].where(df[colonne].isin(autorisees))

    ## Créer trois colonnes binaires : leur moyenne donne le taux du résultat concerné.
    for colonne, resultat in [("win", "Win"), ("loss", "Loss"), ("draw", "Draw")]:
        df[colonne] = df["result"].eq(resultat).astype(int)
    df["score"] = df["result"].map({"Win": 1.0, "Draw": 0.5, "Loss": 0.0})
    df["is_white"] = df["color"].map({"white": 1.0, "black": 0.0})
    suivante = df.groupby("user_id", sort=False)
    valide = suivante["_chronology_segment"].shift(-1).eq(df["_chronology_segment"])
    valide &= suivante["date"].shift(-1).gt(df["date"])
    valide &= ~df["_date_ambiguous"] & ~suivante["_date_ambiguous"].shift(-1).eq(True)
    valide &= ~df["_chronology_uncertain"]
    df["win_next"] = suivante["win"].shift(-1).where(valide)
    return df


## Partie 4 — Point d’entrée et sauvegarde sans écrasement


def preparer_parties(frame):
    """Retourner (parties, bilan) sans modifier le DataFrame source."""
    df = frame.copy().rename(columns=lambda c: str(c).strip())
    if not {"user_id", "result", "opening_name"}.issubset(df):
        raise ValueError("Colonnes requises : user_id, result, opening_name")
    bilan = {"lignes_brutes": len(df)}
    df, reconstruits = normaliser_identifiants(df)
    if reconstruits:
        bilan["identifiants_reconstruits"] = reconstruits
    df = creer_variables(selectionner_parties(df, bilan))
    bilan.update(
        lignes_nettoyees=len(df),
        parties_uniques=df["game_id"].nunique(),
        joueurs=df["user_id"].nunique(),
        ouvertures_manquantes=int(df["opening_name"].isna().sum()),
        elo_adverse_manquant=int(df["opponent_rating"].isna().sum()),
        dates_ex_aequo=int(df["_date_ambiguous"].sum()),
        ruptures_historique=int(df["_chronology_break_before"].sum()),
        joueurs_chronologie_incertaine=df.loc[
            df["_chronology_uncertain"], "user_id"
        ].nunique(),
    )
    return df, bilan


def clean_games(frame):
    """Obtenir seulement la table ; utiliser preparer_parties pour afficher le bilan."""
    return preparer_parties(frame)[0]


def sauvegarder_nettoyage(frame, destination):
    """Écrire un nouveau Parquet, conserver les sources et refuser tout écrasement."""
    path = Path(destination)
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df = clean_games(frame)
    df.to_parquet(path, index=False)
    return df

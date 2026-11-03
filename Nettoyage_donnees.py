"""Nettoyer une COPIE des données, sans supprimer les fichiers ni les parties nulles."""

## ####################################################################
## ANCIEN NETTOYAGE DU NOTEBOOK — NON EXÉCUTÉ
## def clean_games(df):
##     if "game_id" in df.columns:
##         df = df.drop_duplicates(subset=["user_id", "game_id"])
##     else:
##         df = df.drop_duplicates(subset=["user_id", "timestamp"])
##
##     if "timestamp" not in df.columns and "timestamp_ms" in df.columns:
##         df = df.copy()
##         df.loc[:, "timestamp"] = df["timestamp_ms"]
##
##     df = df.sort_values(["user_id", "timestamp"])
##     df = df[df["result"] != "Draw"].copy()
##
##     df["win"] = (df["result"] == "Win").astype(int)
##     df["win_next"] = df.groupby("user_id")["win"].shift(-1)
##
##     return df
## FIN ANCIEN NETTOYAGE
## ####################################################################

from pathlib import Path
import numpy as np
import pandas as pd


## Partie 1 - Harmoniser les dates, les comptes et les catégories


def clean_games(frame):
    """Une ligne = une partie vue par un joueur ; les nulles restent chronologiques."""
    df = frame.copy()
    if "timestamp" not in df and "timestamp_ms" in df:
        df["timestamp"] = df["timestamp_ms"]
    required = {"user_id", "timestamp", "result", "color", "opening_name"}
    if not required.issubset(df):
        raise ValueError("Colonnes manquantes : " + str(sorted(required - set(df))))

    df["user_id"] = df["user_id"].astype("string").str.strip().str.lower()
    df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["user_id", "timestamp"])
    df = df[df["user_id"].ne("") & df["result"].isin(["Win", "Loss", "Draw"])].copy()
    if "status" in df:
        ## Un match annulé ou encore en cours n’est pas une nulle analysable.
        df = df[~df["status"].isin(["created", "started", "aborted", "noStart"])].copy()

    if "game_id" in df and df["game_id"].isna().any():
        raise ValueError("Identifiants de partie manquants : vérifier la source.")
    keys = ["user_id", "game_id"] if "game_id" in df else ["user_id", "timestamp"]
    df = df.drop_duplicates(keys)
    order = ["user_id", "timestamp"] + (["game_id"] if "game_id" in df else [])
    df = df.sort_values(order, kind="stable").reset_index(drop=True)

    ## Ces indicateurs sont des COLONNES : une valeur par partie, pas des listes.
    df["win"] = df["result"].eq("Win").astype(int)
    df["score"] = df["result"].map({"Win": 1.0, "Draw": 0.5, "Loss": 0.0})
    ## Ne pas retirer les nulles avant shift : Win → Draw → Win ne fait pas 2 victoires successives.
    df["win_next"] = df.groupby("user_id", sort=False)["win"].shift(-1)
    df["is_white"] = df["color"].map({"white": 1.0, "black": 0.0})
    if "rating" in df and "opponent_rating" in df:
        df["elo_diff"] = pd.to_numeric(df["rating"], errors="coerce") - pd.to_numeric(
            df["opponent_rating"], errors="coerce"
        )
    else:
        df["elo_diff"] = (
            np.nan
        )  ## rating_diff de l’ancien importeur est une variation APRÈS match.
    return df


## Partie 2 - Sauvegarder en parallèle de la base brute, sans écrasement


def sauvegarder_nettoyage(frame, destination):
    """Refuser d’écraser une ancienne sortie ; le Master fournit un dossier daté."""
    path = Path(destination)
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cleaned = clean_games(frame)
    cleaned.to_parquet(path, index=False)
    return cleaned

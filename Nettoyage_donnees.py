"""Normaliser les parties et conserver un bilan quantifié du nettoyage."""

from pathlib import Path
import numpy as np
import pandas as pd

RESULTATS = {
    "win": "Win",
    "victoire": "Win",
    "loss": "Loss",
    "defeat": "Loss",
    "défaite": "Loss",
    "draw": "Draw",
    "nul": "Draw",
    "nulle": "Draw",
}


def preparer_parties(frame):
    """Retourner une copie propre et les effectifs contrôlés à chaque étape.

    Une ligne correspond au point de vue d’un compte sur une partie. Les doublons
    portent sur (user_id, game_id), car deux adversaires collectés donnent deux
    points de vue. Les observations rejetées ne sont jamais retirées du fichier brut.
    """
    df = frame.copy()
    bilan = {"lignes_brutes": len(df)}
    df = df.rename(columns={c: str(c).strip() for c in df.columns})
    if not {"user_id", "result", "opening_name"}.issubset(df):
        raise ValueError("Colonnes requises : user_id, result, opening_name")
    date_column = next(
        (c for c in ["date", "timestamp_ms", "timestamp"] if c in df), None
    )
    if date_column is None:
        raise ValueError("Date requise : date ISO, timestamp_ms ou timestamp")
    raw_dates = df[date_column]
    if pd.api.types.is_datetime64_any_dtype(raw_dates):
        dates = pd.to_datetime(raw_dates, errors="coerce", utc=True)
    else:
        numbers = pd.to_numeric(raw_dates, errors="coerce")
        dates = pd.to_datetime(
            raw_dates.where(numbers.isna()), errors="coerce", utc=True, format="mixed"
        )
        # Les timestamps numériques >= 10^11 sont exprimés en millisecondes.
        unit_ms = numbers.abs().ge(100_000_000_000) | (date_column == "timestamp_ms")
        for mask, unit in [
            (numbers.notna() & unit_ms, "ms"),
            (numbers.notna() & ~unit_ms, "s"),
        ]:
            dates.loc[mask] = pd.to_datetime(
                numbers.loc[mask], unit=unit, errors="coerce", utc=True
            )
    df["date"] = dates
    df["user_id"] = (
        df["user_id"].astype("string").str.strip().str.lower().replace("", pd.NA)
    )
    df["result"] = df["result"].astype("string").str.strip().str.lower().map(RESULTATS)
    valid = df["user_id"].notna() & df["date"].notna() & df["result"].notna()
    if "status" in df:
        valid &= ~df["status"].isin(["created", "started", "aborted", "noStart"])
    bilan["lignes_invalides_rejetees"] = int((~valid).sum())
    df = df.loc[valid].copy()
    if "game_id" not in df:
        df["game_id"] = df["user_id"] + "_" + df["date"].astype(str)
        bilan["identifiants_reconstruits"] = len(df)
    else:
        df["game_id"] = df["game_id"].astype("string").str.strip().replace("", pd.NA)
        bilan["identifiants_manquants_rejetes"] = int(df["game_id"].isna().sum())
        df = df.dropna(subset=["game_id"])
    before = len(df)
    df = df.drop_duplicates(["user_id", "game_id"])
    bilan["doublons_retires"] = before - len(df)
    df = df.sort_values(["user_id", "date", "game_id"], kind="stable").reset_index(
        drop=True
    )
    df["timestamp"] = df["date"].astype("int64") // 1_000_000
    df["opening_name"] = df["opening_name"].astype("string").str.strip()
    unknown = (
        df["opening_name"].str.lower().isin(["", "inconnue", "unknown", "none", "nan"])
    )
    df["opening_name"] = df["opening_name"].mask(unknown)
    df["opening_family"] = df["opening_name"].str.split(":").str[0].str.strip()
    for column in ["rating", "opponent_rating"]:
        source = df[column] if column in df else pd.Series(np.nan, index=df.index)
        df[column] = pd.to_numeric(source, errors="coerce").replace(
            [np.inf, -np.inf], np.nan
        )
        df.loc[df[column] < 0, column] = np.nan
    df["elo_diff"] = df["rating"] - df["opponent_rating"]
    for column in ["color", "format_partie"]:
        if column not in df:
            df[column] = pd.NA
        df[column] = df[column].astype("string").str.strip().str.lower()
    df["color"] = df["color"].where(df["color"].isin(["white", "black"]))
    df["format_partie"] = df["format_partie"].where(
        df["format_partie"].isin(["bullet", "blitz", "rapid", "classical"])
    )
    for label, result in [("win", "Win"), ("loss", "Loss"), ("draw", "Draw")]:
        df[label] = df["result"].eq(result).astype(int)
    df["score"] = df["result"].map({"Win": 1.0, "Draw": 0.5, "Loss": 0.0})
    df["is_white"] = df["color"].map({"white": 1.0, "black": 0.0})
    df["win_next"] = df.groupby("user_id", sort=False)["win"].shift(-1)
    bilan.update(
        lignes_nettoyees=len(df),
        parties_uniques=df["game_id"].nunique(),
        joueurs=df["user_id"].nunique(),
        ouvertures_manquantes=int(df["opening_name"].isna().sum()),
        elo_adverse_manquant=int(df["opponent_rating"].isna().sum()),
        dates_ex_aequo=int(df.duplicated(["user_id", "date"], keep=False).sum()),
    )
    return df, bilan


def clean_games(frame):
    """Interface courte de nettoyage utilisée par les autres modules."""
    return preparer_parties(frame)[0]


def sauvegarder_nettoyage(frame, destination):
    """Sauvegarder une table nettoyée dans un nouveau fichier Parquet."""
    path = Path(destination)
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df = clean_games(frame)
    df.to_parquet(path, index=False)
    return df

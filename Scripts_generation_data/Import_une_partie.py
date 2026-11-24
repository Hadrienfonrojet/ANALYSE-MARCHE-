"""Exporter séquentiellement les parties Lichess et préserver leur provenance."""

import json
from pathlib import Path
import time
import pandas as pd
import requests
import config_projet as cfg

DATA_DIR = str(cfg.DATA_DIR)


def telecharger_parties(username, token=None, params=None, session=None, max_retries=3):
    """Une requête à la fois, timeout et attente d’au moins 60 secondes après 429."""
    http = session or requests
    headers = {"Accept": "application/x-ndjson"}
    if token:
        headers["Authorization"] = "Bearer " + token
    url = f"https://lichess.org/api/games/user/{username}"
    for attempt in range(max_retries):
        response = http.get(
            url, params=params or {}, headers=headers, timeout=(15, 180), stream=True
        )
        if response.status_code == 429:
            try:
                delay = max(60, int(response.headers.get("Retry-After", 60)))
            finally:
                response.close()
            if attempt == max_retries - 1:
                raise RuntimeError(
                    f"Limite API après {max_retries} tentatives pour {username}"
                )
            time.sleep(delay)
            continue
        try:
            response.raise_for_status()
            return [json.loads(line) for line in response.iter_lines() if line]
        finally:
            response.close()
    raise RuntimeError("Téléchargement incomplet")


def extract_games_user(
    username,
    format_partie,
    nb_parties,
    token=None,
    max_retries=3,
    since=None,
    until=None,
):
    """Une ligne par match du joueur, avec coups et adversaire avant identification."""
    params = {
        "max": nb_parties,
        "rated": "true",
        "perfType": format_partie,
        "opening": "true",
        "moves": "true",
        "finished": "true",
    }
    if since is not None:
        params["since"] = since
    if until is not None:
        params["until"] = until
    games = telecharger_parties(username, token, params, max_retries=max_retries)
    # Garder la réponse brute avant toute transformation, même pour une collecte vide.
    directory = Path(DATA_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    raw_path = directory / f"api_{username.lower()}_{format_partie}.ndjson"
    if raw_path.exists():
        raise FileExistsError(raw_path)
    raw_path.write_text(
        "".join(json.dumps(g, ensure_ascii=False) + "\n" for g in games)
    )
    rows = []
    for game in games:
        players = game.get("players", {})
        colors = [
            c
            for c in ("white", "black")
            if players.get(c, {}).get("user", {}).get("id", "").lower()
            == username.lower()
        ]
        if len(colors) != 1:
            raise ValueError("Le compte demandé est absent d’une partie exportée")
        color = colors[0]
        opponent = players.get("black" if color == "white" else "white", {})
        opening = game.get("opening") or {}
        winner = game.get("winner")
        rows.append(
            {
                "user_id": username.lower(),
                "game_id": game.get("id"),
                "timestamp_ms": game.get("createdAt"),
                "last_move_at": game.get("lastMoveAt"),
                "status": game.get("status"),
                "variant": game.get("variant", "standard"),
                "result": (
                    "Draw" if winner is None else ("Win" if winner == color else "Loss")
                ),
                "color": color,
                "rating": players[color].get("rating"),
                "opponent_rating": opponent.get("rating"),
                "opponent_id": opponent.get("user", {}).get("id"),
                "format_partie": format_partie,
                "moves": game.get("moves"),
                "api_eco": opening.get("eco"),
                "api_opening_name": opening.get("name"),
                "opening_name": opening.get("name"),
                "eco": opening.get("eco"),
            }
        )
    return pd.DataFrame(rows)


def import_games_df(
    nb_parties_extraites, token=None, max_workers=1, since=None, until=None
):
    """Collecter les comptes du fichier de sélection, par cadence, séquentiellement."""
    if max_workers != 1:
        raise ValueError("La collecte Lichess utilise une seule requête à la fois")
    users = (
        pd.read_parquet(Path(DATA_DIR) / "users_list_global.parquet")["user_id"]
        .dropna()
        .unique()
    )
    frames = []
    for cadence in cfg.FORMATS:
        by_cadence = [
            extract_games_user(
                user, cadence, nb_parties_extraites, token, since=since, until=until
            )
            for user in users
        ]
        nonempty = [f for f in by_cadence if not f.empty]
        if nonempty:
            result = pd.concat(nonempty, ignore_index=True)
            result.to_parquet(Path(DATA_DIR) / f"games_{cadence}.parquet", index=False)
            frames.append(result)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

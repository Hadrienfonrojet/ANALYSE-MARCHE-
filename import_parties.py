"""Importer les parties par l’API Lichess et conserver la réponse brute.

Aucun fichier local n’est supprimé. Une reprise utilise seulement une réponse
complète dont les paramètres et l’empreinte correspondent à la demande actuelle.
"""

import hashlib
import json
from pathlib import Path
import time

import pandas as pd
import requests

import config as cfg

DATA_DIR = str(cfg.DATA_DIR)


## Partie 1 — Une requête à la fois, avec attente et erreurs explicites


def telecharger_parties(username, token=None, params=None, session=None, max_retries=3):
    """Retourner les objets JSON ; lever une erreur si le téléchargement échoue.

    Une liste vide signifie une requête réussie sans partie. Elle ne signifie
    jamais un problème de connexion. Aucun jeton n’est écrit dans les fichiers.
    """
    if max_retries < 1:
        raise ValueError("Prévoir au moins une tentative")
    http = session or requests
    headers = {"Accept": "application/x-ndjson"}
    if token:
        headers["Authorization"] = "Bearer " + token
    url = f"https://lichess.org/api/games/user/{username}"

    for attempt in range(max_retries):
        try:
            response = http.get(
                url,
                params=params or {},
                headers=headers,
                timeout=(15, 180),
                stream=True,
            )
            try:
                if response.status_code == 429:
                    # Lichess demande une pause : attendre au moins une minute.
                    try:
                        delay = max(60, int(response.headers.get("Retry-After", 60)))
                    except (TypeError, ValueError):
                        delay = 60
                else:
                    response.raise_for_status()
                    return [json.loads(line) for line in response.iter_lines() if line]
            finally:
                response.close()
        except (requests.ConnectionError, requests.Timeout):
            if attempt == max_retries - 1:
                raise
            delay = 5 * (2**attempt)
        if attempt == max_retries - 1:
            raise RuntimeError(
                f"Limite API après {max_retries} tentatives pour {username}"
            )
        time.sleep(delay)
    raise RuntimeError("Téléchargement incomplet")


## Partie 2 — Conserver une réponse complète et contrôler toute reprise


def lire_ou_telecharger(username, cadence, params, token=None, max_retries=3):
    """Réutiliser seulement le même compte, la même requête et le même contenu.

    Le cache est propre au dossier de collecte. Changer max, since, until ou la
    cadence demande un nouveau dossier, plutôt que d’écraser une ancienne base.
    Un échec réseau n’écrit ni réponse vide ni marqueur de réussite.
    """
    directory = Path(DATA_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    raw_path = directory / f"api_{username}_{cadence}.ndjson"
    manifest_path = raw_path.with_suffix(".json")
    query = {"username": username, "params": params}

    if raw_path.exists() or manifest_path.exists():
        if not raw_path.is_file() or not manifest_path.is_file():
            raise FileExistsError(
                "Cache incomplet : conserver ce dossier et créer une nouvelle collecte"
            )
        manifest = json.loads(manifest_path.read_text())
        payload = raw_path.read_bytes()
        if manifest.get("query") != query or manifest.get("status") != "complete":
            raise FileExistsError(
                "Paramètres différents : utiliser une nouvelle collecte"
            )
        if hashlib.sha256(payload).hexdigest() != manifest.get("sha256"):
            raise ValueError("La réponse brute a changé : reprise refusée")
        return [json.loads(line) for line in payload.splitlines() if line]

    games = telecharger_parties(username, token, params, max_retries=max_retries)
    payload = "".join(json.dumps(g, ensure_ascii=False) + "\n" for g in games).encode(
        "utf-8"
    )
    # Écriture exclusive : ne jamais remplacer un fichier déjà présent.
    with raw_path.open("xb") as stream:
        stream.write(payload)
    manifest = {
        "query": query,
        "status": "complete",
        "n_parties": len(games),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }
    with manifest_path.open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
    return games


## Partie 3 — Transformer UNE partie en UNE ligne du point de vue du joueur


def partie_vers_ligne(game, username, cadence):
    """Retrouver la couleur avant de définir victoire, défaite et nul."""
    players = game.get("players", {})
    colors = [
        c
        for c in ("white", "black")
        if players.get(c, {}).get("user", {}).get("id", "").lower() == username
    ]
    if len(colors) != 1:
        raise ValueError("Le compte demandé est absent d’une partie exportée")
    color = colors[0]
    opponent = players.get("black" if color == "white" else "white", {})
    opening = game.get("opening") or {}
    winner = game.get("winner")
    return {
        "user_id": username,
        "game_id": game.get("id"),
        "timestamp_ms": game.get("createdAt"),
        "last_move_at": game.get("lastMoveAt"),
        "status": game.get("status"),
        "variant": game.get("variant", "standard"),
        "result": "Draw" if winner is None else ("Win" if winner == color else "Loss"),
        "color": color,
        "rating": players[color].get("rating"),
        "opponent_rating": opponent.get("rating"),
        "opponent_id": opponent.get("user", {}).get("id"),
        "format_partie": cadence,
        "moves": game.get("moves"),
        "api_eco": opening.get("eco"),
        "api_opening_name": opening.get("name"),
        "opening_name": opening.get("name"),
        "eco": opening.get("eco"),
    }


def extract_games_user(
    username,
    format_partie,
    nb_parties,
    token=None,
    max_retries=3,
    since=None,
    until=None,
):
    """Collecter un compte et une cadence ; conserver les paramètres de la requête."""
    username = username.strip().lower()
    if not username or any(
        c not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for c in username
    ):
        raise ValueError("Identifiant Lichess invalide")
    if format_partie not in cfg.FORMATS or nb_parties < 1:
        raise ValueError("Cadence ou nombre de parties invalide")
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
    games = lire_ou_telecharger(username, format_partie, params, token, max_retries)
    return pd.DataFrame(
        [partie_vers_ligne(game, username, format_partie) for game in games]
    )


## Partie 4 — Réunir les joueurs sélectionnés et les cadences


def import_games_df(
    nb_parties_extraites, token=None, max_workers=1, since=None, until=None
):
    """Un DataFrame réunit les parties ; un échec arrête l’exécution sans effacer le brut."""
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
        nonempty = [frame for frame in by_cadence if not frame.empty]
        if nonempty:
            result = pd.concat(nonempty, ignore_index=True)
            # La réponse brute fait foi ; cette table dérivée peut être reconstruite à la reprise.
            result.to_parquet(Path(DATA_DIR) / f"games_{cadence}.parquet", index=False)
            frames.append(result)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

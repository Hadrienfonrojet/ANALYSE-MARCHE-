"""Fonctions communes de l'API Lichess : réseau et conversion d'une partie.

Les parcours de joueurs sont détaillés dans Import_des_users.py et la collecte
multi-joueurs dans Import_une_partie.py. Les deux anciennes fonctions publiques
restent disponibles ici pour les notebooks et appels existants.
"""

import json
import time

import requests


## Partie 1 - Lire le flux de parties avec une gestion explicite des échecs réseau
# ------------------------------------------------------------------------


def request_games(username, fmt, n, token=None, retries=4):
    """Renvoyer les objets JSON une fois chacun, même après une reprise.

    opening=true demande la classification Lichess ; moves=true conserve les coups.
    sort=dateAsc sélectionne un historique croissant : on ne prétend pas analyser
    nécessairement les parties les plus récentes. En cas de limitation 429,
    Retry-After est respecté avec un minimum de 60 secondes.
    """
    if n < 1 or retries < 1:
        raise ValueError("Le nombre de parties et de tentatives doit être positif.")

    headers = {"Accept": "application/x-ndjson"}
    if token:
        headers["Authorization"] = "Bearer " + token

    parameters = {
        "max": n,
        "rated": "true",
        "perfType": fmt,
        "opening": "true",
        "moves": "true",
        "sort": "dateAsc",
        "variant": "standard",
        "finished": "true",
    }
    seen = set()

    for attempt in range(retries):
        try:
            # Le contexte ferme la réponse aussi lorsqu'une erreur HTTP survient.
            with requests.get(
                "https://lichess.org/api/games/user/" + username,
                params=parameters,
                headers=headers,
                stream=True,
                timeout=(15, 120),
            ) as response:
                if response.status_code == 429:
                    delay = response.headers.get("Retry-After", "60")
                    seconds = int(delay) if delay.isdigit() else 60
                    time.sleep(max(60, seconds))
                    continue

                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    try:
                        game = json.loads(line)
                    except json.JSONDecodeError as error:
                        raise RuntimeError(
                            "Réponse JSON Lichess invalide ; collecte interrompue."
                        ) from error
                    identifier = game.get("id")
                    if identifier and identifier not in seen:
                        seen.add(identifier)
                        yield game
                return

        except requests.RequestException as error:
            if attempt == retries - 1:
                raise RuntimeError(
                    f"Collecte échouée pour {username} ({fmt})."
                ) from error
            time.sleep(2**attempt)

    raise RuntimeError(f"Limite API persistante pour {username} ({fmt}).")


## Partie 2 - Choisir le point de vue du joueur et extraire les variables
# ---------------------------------------------------------------


def parse_game(g, user, fmt, origin):
    """Convertir une partie terminée en une observation joueur/partie.

    Une partie anonyme, sans identifiant ou sans le joueur demandé est écartée.
    L'absence de winner ne suffit pas pour classer une partie commencée comme nulle :
    seuls des statuts terminaux reconnus sont admis.
    """
    players = g.get("players") or {}
    if not all(color in players for color in ["white", "black"]):
        return None
    if not g.get("id") or g.get("createdAt") is None:
        return None

    identities = {
        color: ((players[color] or {}).get("user") or {}).get("id", "").lower()
        for color in ["white", "black"]
    }
    user = str(user).strip().lower()
    if user not in identities.values() or not user:
        return None

    terminal = {
        "mate",
        "resign",
        "stalemate",
        "timeout",
        "draw",
        "outoftime",
        "cheat",
        "variantEnd",
    }
    status = g.get("status")
    if status not in terminal:
        return None

    color = "white" if identities["white"] == user else "black"
    opponent_color = "black" if color == "white" else "white"
    winner = g.get("winner")
    if winner not in (None, "white", "black"):
        return None
    if winner is None and status not in {"draw", "stalemate", "outoftime"}:
        return None

    result = "Draw" if winner is None else ("Win" if winner == color else "Loss")
    me = players[color] or {}
    other = players[opponent_color] or {}
    opening = g.get("opening") or {}
    clock = g.get("clock") or {}
    rating, opponent_rating = me.get("rating"), other.get("rating")
    difference = (
        rating - opponent_rating
        if isinstance(rating, (int, float))
        and isinstance(opponent_rating, (int, float))
        else None
    )

    return {
        "game_id": g["id"],
        "user_id": user,
        "seed_origin": origin,
        "format_partie": fmt,
        "timestamp_ms": g["createdAt"],
        "last_move_ms": g.get("lastMoveAt"),
        "result": result,
        "win": int(result == "Win"),
        "score": {"Win": 1.0, "Draw": 0.5, "Loss": 0.0}[result],
        "is_draw": int(result == "Draw"),
        "color": color,
        "is_white": int(color == "white"),
        "rating": rating,
        "opponent_rating": opponent_rating,
        "rating_diff_opponent": difference,
        "rating_diff": me.get("ratingDiff"),
        "opponent_id": (other.get("user") or {}).get("id"),
        "eco": opening.get("eco"),
        "opening_name": opening.get("name"),
        "opening_ply": opening.get("ply"),
        "moves": g.get("moves", ""),
        "status": status,
        "rated": g.get("rated"),
        "variant": g.get("variant", ""),
        "speed": g.get("speed"),
        "clock_initial": clock.get("initial"),
        "clock_increment": clock.get("increment"),
    }


## Partie 3 - Compatibilité avec les anciens notebooks
# ---------------------------------------------


def discover_stratified(
    seeds, token=None, target_per_seed=30, neighbors_per_user=10, seed=42
):
    """Le parcours est désormais expliqué dans le fichier historique des users."""
    from Scripts_generation_data.Import_des_users import discover_stratified as discover

    return discover(seeds, token, target_per_seed, neighbors_per_user, seed)


def collect_games(users, token=None, n_per_format=60):
    """L'assemblage est désormais expliqué dans le fichier historique des parties."""
    from Scripts_generation_data.Import_une_partie import import_games_enriched

    return import_games_enriched(users, token, n_per_format)

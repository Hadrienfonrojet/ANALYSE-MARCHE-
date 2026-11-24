"""Sélectionner les adversaires récents et documenter la graine aléatoire."""

from pathlib import Path
import random
import pandas as pd
import config_projet as cfg
from Scripts_generation_data.Import_une_partie import telecharger_parties

DATA_DIR = str(cfg.DATA_DIR)


def get_recent_opponents(username, token=None, nb_games_to_check=10):
    """Extraire les comptes uniques des adversaires depuis l’API NDJSON."""
    games = telecharger_parties(username, token, {"max": nb_games_to_check})
    opponents = set()
    for game in games:
        for color in ["white", "black"]:
            user = game.get("players", {}).get(color, {}).get("user", {}).get("id")
            if user and user.lower() != username.lower():
                opponents.add(user.lower())
    return sorted(opponents)


def discover_users_random_walk(
    seed_user, target_count, token=None, branching_factor=5, random_seed=73
):
    """Explorer le réseau d’adversaires ; le réseau API peut évoluer entre deux dates."""
    if target_count < 1 or branching_factor < 1:
        raise ValueError("Les nombres de comptes et de branches doivent être positifs")
    rng = random.Random(random_seed)
    users = [seed_user.strip().lower()]
    known = set(users)
    current = users[0]
    for _ in range(target_count * 3):
        if len(users) >= target_count:
            break
        candidates = [
            name for name in get_recent_opponents(current, token) if name not in known
        ]
        take = min(len(candidates), branching_factor, target_count - len(users))
        if take:
            batch = rng.sample(candidates, take)
            users.extend(batch)
            known.update(batch)
            current = rng.choice(batch)
        else:
            current = rng.choice(sorted(known))
    result = pd.DataFrame({"user_id": users})
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    result.to_parquet(Path(DATA_DIR) / "users_list_global.parquet", index=False)
    return result

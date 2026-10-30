"""Découvrir les joueurs à étudier à partir de leurs adversaires Lichess.

Ce fichier contient le véritable parcours des joueurs, et pas seulement un renvoi.
Il reprend les noms de fonctions historiques du projet. Le parcours est réalisé
sur un graphe : un compte est relié aux adversaires trouvés dans ses parties.
Il ne constitue pas un échantillon aléatoire représentatif de tous les joueurs.

Entrées : pseudos de départ, nombre de joueurs et jeton facultatif.
Sortie : Data/users_list_stratified.parquet dans l'expérience courante.
"""

from collections import deque
import random
import time

import pandas as pd

import config_projet as cfg
from Scripts_generation_data.Collecte_enrichie import request_games


# 1. Lire les adversaires d'un compte
# -----------------------------------

def get_recent_opponents(username, token=None, nb_games_to_check=10):
    """Retourner des adversaires uniques à partir des parties demandées à l'API.

    Le nom historique 'recent' est conservé pour les anciens appels. La requête
    commune est triée par date croissante : ce sont les parties sélectionnées
    par cette requête, pas nécessairement les plus récentes du compte.
    Les comptes anonymes, absents et le compte lui-même sont exclus.
    """
    username = str(username).strip().lower()
    opponents = set()

    for game in request_games(username, 'blitz', nb_games_to_check, token):
        for color in ['white', 'black']:
            player = game.get('players', {}).get(color) or {}
            identity = (player.get('user') or {}).get('id')

            if identity:
                opponent = identity.strip().lower()
                if opponent and opponent != username:
                    opponents.add(opponent)

    return sorted(opponents)


# 2. Parcourir plusieurs graines sans compter deux fois le même compte
# --------------------------------------------------------------------

def discover_stratified(seeds, token=None, target_per_seed=30,
                        neighbors_per_user=10, seed=42):
    """Parcours en largeur des adversaires, avec origine et profondeur.

    target_per_seed est un maximum, pas une garantie : le graphe peut s'épuiser.
    Une graine peut avoir des adversaires déjà trouvés depuis une autre graine.
    visited évite de compter plusieurs fois le même joueur dans le panel.
    La profondeur est 0 pour la graine, 1 pour son adversaire, etc.
    Le générateur aléatoire fixe seulement l'ordre de parcours des adversaires.
    """
    if target_per_seed < 1 or neighbors_per_user < 1:
        raise ValueError('Les nombres de joueurs et de parties doivent être positifs.')

    seeds = [str(name).strip().lower() for name in seeds if pd.notna(name) and str(name).strip()]
    if not seeds:
        raise ValueError('Configurer au moins un pseudo de départ.')

    rng = random.Random(seed)
    visited = set()
    records = []

    for origin in dict.fromkeys(seeds):
        queue = deque([(origin, 0)])
        count = 0

        while queue and count < target_per_seed:
            username, depth = queue.popleft()
            if username in visited:
                continue

            visited.add(username)
            count += 1
            records.append({
                'user_id': username,
                'seed_origin': origin,
                'discovery_depth': depth,
            })

            # Ne pas interroger inutilement les adversaires du dernier compte.
            if count >= target_per_seed:
                continue

            opponents = get_recent_opponents(username, token, neighbors_per_user)
            rng.shuffle(opponents)
            queue.extend((name, depth + 1) for name in opponents if name not in visited)
            time.sleep(0.15)

    users = pd.DataFrame(records)
    cfg.DATA_DIR.mkdir(parents=True, exist_ok=True)
    users.to_parquet(cfg.DATA_DIR / 'users_list_stratified.parquet', index=False)

    return users


# 3. Conserver les points d'entrée historiques
# ---------------------------------------------

def discover_users_random_walk(seed_user, target_count, token=None, branching_factor=5):
    """Lancer le parcours depuis un compte et garder aussi le nom de sortie ancien.

    Le nom historique est conservé, mais l'algorithme est un parcours en largeur
    avec ordre mélangé, pas une marche aléatoire au sens probabiliste strict.
    """
    users = discover_stratified([seed_user], token, target_count, branching_factor)
    users.to_parquet(cfg.DATA_DIR / 'users_list_global.parquet', index=False)
    return users


def discover_users_five_seeds(seed_users, token=None, target_per_seed=30):
    """Même fonction depuis plusieurs graines ; cinq sont conseillées, pas imposées."""
    return discover_stratified(seed_users, token, target_per_seed)

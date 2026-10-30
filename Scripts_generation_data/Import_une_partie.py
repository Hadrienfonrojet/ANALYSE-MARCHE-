"""Fonctions de collecte utilisant uniquement les métadonnées de l'API Lichess."""
import pandas as pd
import config_projet as cfg
from Scripts_generation_data.Collecte_enrichie import request_games, parse_game, collect_games

def extract_games_user(username, format_partie, nb_parties, token=None, max_retries=4):
    username = username.lower()
    rows = [parse_game(g, username, format_partie, username)
            for g in request_games(username, format_partie, nb_parties, token, max_retries)]
    return pd.DataFrame([row for row in rows if row is not None])

def import_games_enriched(users_df, token=None, n_per_format=60):
    return collect_games(users_df, token, n_per_format)

def import_games_df(nb_parties_extraites, token=None, max_workers=1):
    # Les requêtes restent séquentielles pour respecter les limites de Lichess.
    users = pd.read_parquet(cfg.DATA_DIR / 'users_list_stratified.parquet')
    return collect_games(users, token, nb_parties_extraites)

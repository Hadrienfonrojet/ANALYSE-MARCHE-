"""Découverte de joueurs par les adversaires renvoyés par l'API Lichess."""
from Scripts_generation_data.Collecte_enrichie import discover_stratified, request_games

def get_recent_opponents(username, token=None, nb_games_to_check=10):
    opponents = set()
    for game in request_games(username, 'blitz', nb_games_to_check, token):
        for player in game.get('players', {}).values():
            name = (player.get('user') or {}).get('id', '').lower()
            if name and name != username.lower():
                opponents.add(name)
    return sorted(opponents)

def discover_users_random_walk(seed_user, target_count, token=None, branching_factor=5):
    return discover_stratified([seed_user], token, target_count, branching_factor)

def discover_users_five_seeds(seed_users, token=None, target_per_seed=30):
    return discover_stratified(seed_users, token, target_per_seed)

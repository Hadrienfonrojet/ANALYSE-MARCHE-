"""Inspection explicite des métadonnées des parties, sans afficher de jeton."""
import os
import config_projet as cfg
from config_projet import SEED_USERS
from Scripts_generation_data.Collecte_enrichie import request_games

def inspect_games(username, fmt='classical', n=5, token=None):
    games = list(request_games(username, fmt, n, token))
    for game in games:
        print({'id': game.get('id'), 'opening': game.get('opening')})
    return games

def main():
    return inspect_games(SEED_USERS[0], token=cfg.get_lichess_token())

if __name__ == '__main__':
    main()

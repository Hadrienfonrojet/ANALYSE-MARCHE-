"""Inspection explicite des métadonnées des parties, sans afficher de jeton."""

import os
import config_projet as cfg
from config_projet import SEED_USERS
from Scripts_generation_data.Collecte_enrichie import request_games


def inspect_games(username, fmt="classical", n=5, token=None):
    games = list(request_games(username, fmt, n, token))
    for game in games:
        print({"id": game.get("id"), "opening": game.get("opening")})
    return games


def main():
    return inspect_games(SEED_USERS[0], token=cfg.get_lichess_token())


if __name__ == "__main__":
    main()




## avant maxime 
# inspect_lichess.py
import requests
import json

# ⚡ Modifier ici le joueur et le format que tu veux inspecter
username = "yuuki-asuna"
format_partie = "classical"
nb_parties = 5
token = "lip_jwKnD5eHwEVhDubisYt5"  

url = f"https://lichess.org/api/games/user/{username}"
params = {
    "max": nb_parties,
    "rated": "true",
    "perfType": format_partie,
}
headers = {
    "Accept": "application/x-ndjson",
    "Authorization": f"Bearer {token}"
}

response = requests.get(url, params=params, headers=headers)

if response.status_code != 200:
    print(f"Erreur {response.status_code} pour {username}")
    exit()

lines = response.text.strip().split("\n")
for i, line in enumerate(lines):
    if not line.strip():
        continue

    game_data = json.loads(line)
    print(f"\n=== Partie {i+1} ===")
    print("Clés disponibles dans game_data :")
    print(game_data.keys())

    # Vérifier si 'opening' est présent
    opening = game_data.get("opening", None)
    if opening:
        print("Opening détectée :", opening)
        print("  ECO :", opening.get("eco"))
        print("  Name :", opening.get("name"))
    else:
        print("Aucune ouverture détectée pour cette partie.")

    # Afficher les premiers coups et le PGN pour info
    moves = game_data.get("moves", "")
    print("Coups (extrait) :", moves[:50], "...")
    print("PGN disponible :", "Oui" if game_data.get("pgn") else "Non")

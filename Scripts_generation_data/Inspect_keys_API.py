"""Observer les champs d’une partie Lichess via un appel explicite."""

import argparse
from Scripts_generation_data.Import_une_partie import telecharger_parties
import config_projet as cfg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("username")
    args = parser.parse_args()
    games = telecharger_parties(
        args.username,
        cfg.get_lichess_token(),
        {"max": 1, "opening": "true", "moves": "true"},
    )
    for game in games:
        print("Champs", sorted(game))
        print("Ouverture API", game.get("opening"))
        print("Coups", str(game.get("moves", ""))[:100])


if __name__ == "__main__":
    main()

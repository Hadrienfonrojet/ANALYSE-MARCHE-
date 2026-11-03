"""Référentiel officiel Lichess, compatible avec le projet original.
Le bloc commenté conserve l’ancienne liste ; seule la partie suivante s’exécute.
"""

## ########################################################################
## ANCIEN FICHIER : LISTE MANUELLE DE 50 OUVERTURES — NON EXÉCUTÉ
## # create_openings_df.py
## import pandas as pd
## import os
##
## # Liste d'exemple : 50 ouvertures populaires avec ECO, nom, premiers coups
## eco_db = [
##     {"eco": "A00", "name": "Uncommon / Flank Opening", "moves": ["a3"]},
##     {"eco": "A01", "name": "Nimzowitsch–Larsen Attack", "moves": ["b3"]},
##     {"eco": "A02", "name": "Bird's Opening", "moves": ["f4"]},
##     {"eco": "A04", "name": "Réti Opening", "moves": ["Nf3"]},
##     {"eco": "A10", "name": "English Opening", "moves": ["c4"]},
##     {"eco": "B01", "name": "Scandinavian Defense", "moves": ["e4", "d5"]},
##     {"eco": "B02", "name": "Alekhine's Defense", "moves": ["e4", "Nf6"]},
##     {"eco": "B07", "name": "Pirc Defense", "moves": ["e4", "d6", "d4", "Nf6"]},
##     {"eco": "B08", "name": "Pirc Defense, Classical", "moves": ["e4", "d6", "d4", "Nf6", "Nc3", "g6"]},
##     {"eco": "B10", "name": "Caro-Kann Defense", "moves": ["e4", "c6"]},
##     {"eco": "B12", "name": "Caro-Kann Defense, Advance", "moves": ["e4", "c6", "d4", "d5", "e5"]},
##     {"eco": "B20", "name": "Sicilian Defense", "moves": ["e4", "c5"]},
##     {"eco": "B21", "name": "Sicilian Defense, Smith-Morra", "moves": ["e4", "c5", "d4"]},
##     {"eco": "B22", "name": "Sicilian, Alapin", "moves": ["e4", "c5", "c3"]},
##     {"eco": "B23", "name": "Sicilian, Closed", "moves": ["e4", "c5", "Nc3"]},
##     {"eco": "B27", "name": "Sicilian, Closed, Classical", "moves": ["e4", "c5", "Nc3", "Nc6"]},
##     {"eco": "B30", "name": "Sicilian, Najdorf", "moves": ["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6"]},
##     {"eco": "B40", "name": "Sicilian, Kan", "moves": ["e4", "c5", "Nc3", "Nc6", "Nf3", "e6"]},
##     {"eco": "C00", "name": "French Defense", "moves": ["e4", "e6"]},
##     {"eco": "C02", "name": "French, Advance", "moves": ["e4", "e6", "d4", "d5", "e5"]},
##     {"eco": "C10", "name": "French, Classical", "moves": ["e4", "e6", "d4", "d5", "Nc3"]},
##     {"eco": "C20", "name": "King's Pawn Game", "moves": ["e4"]},
##     {"eco": "C21", "name": "Center Game", "moves": ["e4", "e5", "d4"]},
##     {"eco": "C23", "name": "Bishop's Opening", "moves": ["e4", "e5", "Bc4"]},
##     {"eco": "C25", "name": "Vienna Game", "moves": ["e4", "e5", "Nc3"]},
##     {"eco": "C30", "name": "King's Gambit", "moves": ["e4", "e5", "f4"]},
##     {"eco": "C40", "name": "King's Knight Opening", "moves": ["e4", "e5", "Nf3"]},
##     {"eco": "C41", "name": "Philidor Defense", "moves": ["e4", "e5", "Nf3", "d6"]},
##     {"eco": "C42", "name": "Petrov's Defense", "moves": ["e4", "e5", "Nf3", "Nf6"]},
##     {"eco": "C43", "name": "Bishop's Opening", "moves": ["e4", "e5", "Bc4", "Bc5"]},
##     {"eco": "C44", "name": "King's Pawn Game", "moves": ["e4", "e5", "Nf3", "Nc6"]},
##     {"eco": "C45", "name": "Scotch Game", "moves": ["e4", "e5", "Nf3", "Nc6", "d4"]},
##     {"eco": "C50", "name": "Italian Game", "moves": ["e4", "e5", "Nf3", "Nc6", "Bc4"]},
##     {"eco": "C55", "name": "Two Knights Defense", "moves": ["e4", "e5", "Nf3", "Nc6", "Bc4", "Nf6"]},
##     {"eco": "C60", "name": "Ruy Lopez", "moves": ["e4", "e5", "Nf3", "Nc6", "Bb5"]},
##     {"eco": "C65", "name": "Ruy Lopez, Berlin Defense", "moves": ["e4", "e5", "Nf3", "Nc6", "Bb5", "Nf6"]},
##     {"eco": "C70", "name": "Ruy Lopez, Morphy Defense", "moves": ["e4", "e5", "Nf3", "Nc6", "Bb5", "a6"]},
##     {"eco": "C78", "name": "Ruy Lopez, Modern Steinitz Defense", "moves": ["e4", "e5", "Nf3", "Nc6", "Bb5", "d6"]},
##     {"eco": "C80", "name": "Ruy Lopez, Open", "moves": ["e4", "e5", "Nf3", "Nc6", "Bb5", "a6", "Ba4", "Nf6"]},
##     {"eco": "D00", "name": "Queen's Pawn Game", "moves": ["d4"]},
##     {"eco": "D02", "name": "Queen's Pawn Game, Chigorin", "moves": ["d4", "d5", "Nc3"]},
##     {"eco": "D06", "name": "Queen's Gambit", "moves": ["d4", "d5", "c4"]},
##     {"eco": "D10", "name": "Queen's Gambit Declined", "moves": ["d4", "d5", "c4", "e6"]},
##     {"eco": "D20", "name": "Queen's Gambit Accepted", "moves": ["d4", "d5", "c4", "dxc4"]},
##     {"eco": "D30", "name": "Queen's Gambit Declined, Tarrasch", "moves": ["d4", "d5", "c4", "e6", "Nc3", "Nf6"]},
##     {"eco": "D35", "name": "Queen's Gambit Declined, Exchange", "moves": ["d4", "d5", "c4", "e6", "Nc3", "dxc4"]},
##     {"eco": "D40", "name": "King's Indian Defense", "moves": ["d4", "Nf6", "c4", "g6"]},
##     {"eco": "D50", "name": "Queen's Gambit Declined, Orthodox", "moves": ["d4", "d5", "c4", "e6", "Nc3", "Nf6", "Nf3", "Be7"]},
##     {"eco": "E00", "name": "Catalan Opening", "moves": ["d4", "Nf6", "c4", "e6", "g3"]},
##     {"eco": "E10", "name": "King's Indian Attack", "moves": ["Nf3", "d5", "g3"]},
## ]
##
## # Transformer la liste en DataFrame
## df_openings = pd.DataFrame(eco_db)
##
## # Répertoire Data du projet (même dossier que Master_file.py)
## DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "Data")
## os.makedirs(DATA_DIR, exist_ok=True)
##
## # Chemin complet pour sauvegarder
## save_path = os.path.join(DATA_DIR, "openings.parquet")
##
## # Sauvegarde en parquet
## df_openings.to_parquet(save_path)
##
## print(f"DataFrame ouvertures créé et sauvegardé dans {save_path}")
## print(df_openings.head())
## FIN ANCIEN FICHIER : LISTE MANUELLE DE 50 OUVERTURES
## ########################################################################

"""Télécharger et réunir les cinq tables officielles d'ouvertures Lichess.

Le gros référentiel est construit AVANT l'identification : a.tsv à e.tsv
contiennent code ECO, nom et suite de coups PGN. Chaque ligne est rejouée avec
python-chess pour obtenir sa position finale et sa profondeur en demi-coups.
L'identification des parties est ensuite faite dans Identification_ouvertures.py.

Les fichiers sources et la version utilisée sont conservés dans References/.
Le référentiel réuni est aussi copié dans le dossier Data de chaque expérience.
"""

from datetime import datetime, timezone
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path

import chess
import chess.pgn
import pandas as pd
import requests

import config_projet as cfg


## Partie 1 - Construire une position comparable, en ignorant les compteurs de coups
# -------------------------------------------------------------------------


def position_key(board):
    """Pièces, trait, droits de roque et en passant légal, sans les compteurs.

    Comparer ces quatre champs permet de reconnaître certaines transpositions :
    des ordres de coups différents peuvent atteindre la même position.
    """
    return " ".join(board.fen(en_passant="legal").split()[:4])


## Partie 2 - Télécharger les sources, sans remplacer les autres expériences
# -----------------------------------------------------------------


def download_sources(source_dir=None):
    """Récupérer a.tsv à e.tsv depuis une révision officielle figée.

    Une version figée rend les classifications reproductibles. Pour utiliser une
    autre version, changer OPENINGS_REFERENCE_REV dans config_projet.py.
    Les fichiers déjà présents dans ce dossier de version ne sont pas retéléchargés.
    """
    directory = (
        Path(source_dir) if source_dir is not None else cfg.OPENINGS_REFERENCE_DIR
    )
    directory.mkdir(parents=True, exist_ok=True)

    for letter in "abcde":
        path = directory / (letter + ".tsv")
        if path.is_file():
            continue

        url = f"https://raw.githubusercontent.com/lichess-org/chess-openings/{cfg.OPENINGS_REFERENCE_REV}/{letter}.tsv"
        with requests.get(url, timeout=(15, 90)) as response:
            response.raise_for_status()
            content = response.content

        # Vérifier le format avant de conserver le fichier dans le cache.
        frame = pd.read_csv(StringIO(content.decode("utf-8-sig")), sep="\t", dtype=str)
        if not {"eco", "name", "pgn"}.issubset(frame.columns) or frame.empty:
            raise ValueError("Référentiel Lichess invalide : " + url)
        temporary = path.with_suffix(".tsv.tmp")
        temporary.write_bytes(content)
        temporary.replace(path)

    return directory


## Partie 3 - Transformer toutes les lignes officielles en une grande table
# -----------------------------------------------------------------


def read_reference(source_dir):
    """Garder toutes les ouvertures, y compris celles absentes de la collecte.

    Une ligne de référence décrit une position atteinte après une suite PGN.
    Le nom d'une variante n'est pas attribué à ses préfixes : il faut atteindre
    sa position finale pour pouvoir la reconnaître dans une partie.
    """
    frames = []
    for letter in "abcde":
        path = Path(source_dir) / (letter + ".tsv")
        frame = pd.read_csv(path, sep="\t", dtype=str)
        if not {"eco", "name", "pgn"}.issubset(frame.columns):
            raise ValueError("Colonnes manquantes dans " + str(path))
        frame["source_file"] = path.name
        frames.append(frame)

    reference = pd.concat(
        frames, ignore_index=True
    )  ## Un grand DataFrame réunit les cinq tables.
    reference = reference.dropna(subset=["eco", "name", "pgn"])
    reference = reference.drop_duplicates(["eco", "name", "pgn"]).reset_index(drop=True)
    positions, depths, uci_lines = [], [], []

    for row in reference.itertuples(index=False):
        game = chess.pgn.read_game(StringIO(row.pgn))
        if game is None or game.errors:
            raise ValueError("PGN de référence invalide : " + row.name)

        board = game.board()
        moves = list(game.mainline_moves())
        if not moves:
            raise ValueError("Référence sans coups : " + row.name)
        for move in moves:
            board.push(move)

        positions.append(position_key(board))
        depths.append(len(moves))
        uci_lines.append(" ".join(move.uci() for move in moves))

    reference["position_key"] = (
        positions  ## Une colonne de positions finales, une par ouverture officielle.
    )
    reference["reference_ply"] = depths
    reference["uci"] = uci_lines
    reference["family"] = reference["name"].str.split(":").str[0].str.strip()
    reference["eco_group"] = reference["eco"].str[0]
    reference["source_revision"] = cfg.OPENINGS_REFERENCE_REV

    return reference.sort_values(["eco", "name", "pgn"]).reset_index(drop=True)


import re

## Partie 1 - Préparer l'index des positions officielles
# -----------------------------------------------


def build_position_index(reference, max_fullmoves=10):
    """Indexer les positions dont la variante est atteinte dans la limite choisie.

    Un coup complet = un coup blanc et un coup noir = deux demi-coups (plies).
    Les variantes nécessitant plus de coups que la limite restent dans la grande
    table, mais elles ne peuvent pas être attribuées à une partie avant leur terme.
    """
    if max_fullmoves < 1:
        raise ValueError("La limite de coups doit être positive.")
    required = {"position_key", "reference_ply", "eco", "name", "family"}
    if not required.issubset(reference.columns):
        raise ValueError(
            "Utiliser le référentiel complet avec positions et profondeurs."
        )

    selected = reference[reference["reference_ply"].le(2 * max_fullmoves)]
    selected = selected.sort_values(
        ["reference_ply", "eco", "name"], ascending=[False, True, True]
    )
    index = {}
    for row in selected.to_dict("records"):
        index.setdefault(row["position_key"], []).append(row)
    return index


## Partie 2 - Rejouer la partie, au maximum sur cinq ou dix coups complets
# -----------------------------------------------------------------


def identify_opening(moves, index, max_fullmoves=10, min_fullmoves=5):
    """Retenir la variante officielle la plus précise atteinte dans cette fenêtre.

    On exige au moins min_fullmoves coups complets effectivement disponibles.
    Une référence courte reste possible : par exemple une famille reconnue après
    deux coups. La profondeur exacte est retournée pour ne pas prétendre que sa
    variante a été reconnue après dix coups lorsqu'elle ne l'a pas été.

    Les transpositions sont reconnues lorsqu'une même position complète est
    atteinte. Si plusieurs noms décrivent cette position, tous les candidats sont
    conservés ; le choix affiché est déterministe (profondeur, puis ECO et nom).
    """
    if min_fullmoves < 1 or max_fullmoves < min_fullmoves:
        raise ValueError("Choisir 1 <= minimum de coups <= maximum de coups.")

    result = {
        "eco": "UNKNOWN",
        "opening_name": "Inconnue",
        "opening_identification_source": "reference_position",
        "opening_identification_status": "coups_absents",
        "opening_match_ply": None,
        "opening_reference_ply": None,
        "opening_plies_examined": 0,
        "opening_candidate_count": 0,
        "opening_candidates": "[]",
    }
    if not isinstance(moves, str) or not moves.strip():
        return result

    tokens = []
    for token in moves.split():
        # L'API renvoie du SAN sans numéros ; accepter aussi 1.e4 ou 1...e5.
        token = re.sub(r"^\d+\.(?:\.\.)?", "", token)
        if not token:
            continue
        if token in ["1-0", "0-1", "1/2-1/2", "*"]:
            break
        tokens.append(token)

    if len(tokens) < 2 * min_fullmoves:
        result["opening_identification_status"] = "partie_trop_courte"
        return result

    board = chess.Board()
    best = None
    best_rank = (-1, -1)
    result["opening_identification_status"] = "aucune_correspondance"

    for ply, token in enumerate(tokens[: 2 * max_fullmoves], 1):
        try:
            move = board.parse_san(token)
            if not move:
                raise ValueError(
                    "Un coup nul ne constitue pas un coup d’ouverture valide."
                )
            board.push(move)
        except ValueError:
            result["opening_identification_status"] = "coups_invalides"
            result["opening_plies_examined"] = ply - 1
            return result

        result["opening_plies_examined"] = ply
        candidates = index.get(position_key(board), [])
        if candidates:
            chosen = candidates[0]
            rank = (int(chosen["reference_ply"]), ply)
            if rank > best_rank:
                best_rank = rank
                best = chosen, ply, candidates

    if best is not None:
        chosen, match_ply, candidates = best
        aliases = sorted({(row["eco"], row["name"]) for row in candidates})
        result.update(
            {
                "eco": chosen["eco"],
                "opening_name": chosen["name"],
                "opening_identification_status": (
                    "identifiee" if len(aliases) == 1 else "plusieurs_noms"
                ),
                "opening_match_ply": match_ply,
                "opening_reference_ply": int(chosen["reference_ply"]),
                "opening_candidate_count": len(aliases),
                "opening_candidates": json.dumps(
                    [{"eco": eco, "name": name} for eco, name in aliases],
                    ensure_ascii=False,
                ),
            }
        )

    return result


## Partie 3 - Appliquer aux parties en conservant l'étiquette API séparément
# ------------------------------------------------------------------


def identify_games(raw, reference, max_fullmoves=None, min_fullmoves=None):
    """Une même partie vue par deux joueurs n'est reconstruite qu'une fois.

    Des bases historiques sans colonne moves restent explicitement non identifiées.
    Les statistiques ne confondent pas l'étiquette API avec le résultat local.
    """
    maximum = cfg.OPENING_MAX_FULLMOVES if max_fullmoves is None else max_fullmoves
    minimum = cfg.OPENING_MIN_FULLMOVES if min_fullmoves is None else min_fullmoves
    if minimum < 1 or maximum < minimum:
        raise ValueError("Choisir 1 <= minimum de coups <= maximum de coups.")
    index = build_position_index(reference, maximum)
    data = raw.copy()  ## Nouveau DataFrame : conserver intacte la base brute fournie.

    # Si le panel est réanalysé, conserver les étiquettes API originales.
    for column in ["eco", "opening_name"]:
        api_column = "api_" + column
        if api_column not in data:
            data[api_column] = data[column] if column in data else None

    cache, records = {}, []
    for row in data.to_dict("records"):
        moves = row.get("moves")
        variant = row.get("variant")
        key = (str(moves), str(variant))
        if key not in cache:
            result = identify_opening(moves, index, maximum, minimum)
            if isinstance(variant, str) and variant not in ("", "standard"):
                result = identify_opening(None, index, maximum, minimum)
                result["opening_identification_status"] = "variante_non_standard"
            cache[key] = result
        records.append(cache[key])

    identified = pd.DataFrame(
        records, index=data.index
    )  ## Une ligne de diagnostic par observation.
    for column in identified:
        data[column] = identified[column]

    return data


## Partie 4 - Conserver le contrat attendu par Import_une_partie.py


def creer_openings(data_dir=None, source_dir=None):
    """Créer openings.parquet avec eco, name, moves ET les positions officielles."""
    directory = download_sources(source_dir)
    reference = read_reference(directory)
    ## uci contient les coups sans ambiguïté ; on les rejoue pour construire SAN.
    all_san = []
    for line in reference["uci"]:
        board = chess.Board()
        san = []
        for token in line.split():
            move = chess.Move.from_uci(token)
            san.append(board.san(move))
            board.push(move)
        all_san.append(san)
    reference["moves"] = all_san
    target = Path(data_dir) if data_dir is not None else cfg.DATA_DIR
    target.mkdir(parents=True, exist_ok=True)
    reference.to_parquet(target / "openings.parquet", index=False)
    return reference


if __name__ == "__main__":
    print(creer_openings()[["eco", "name"]].head())

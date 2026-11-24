"""Réunir les cinq tables Lichess et identifier les ouvertures par position."""

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
    metadata = {
        "revision": cfg.OPENINGS_REFERENCE_REV,
        "rows": len(reference),
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "sha256": {
            letter
            + ".tsv": sha256((directory / (letter + ".tsv")).read_bytes()).hexdigest()
            for letter in "abcde"
        },
    }
    (target / "openings_sources.json").write_text(json.dumps(metadata, indent=2))
    return reference


if __name__ == "__main__":
    print(creer_openings()[["eco", "name"]].head())

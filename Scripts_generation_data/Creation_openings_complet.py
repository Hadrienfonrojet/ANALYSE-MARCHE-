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


## Partie 4 - Fonction publique du master et du notebook
# ------------------------------------------------


def build_openings(raw=None, source_dir=None, refresh=False):
    """Créer ou lire le référentiel complet officiel, puis le copier dans le run.

    raw reste accepté pour les anciens appels build_openings(raw), mais il
    n'est plus utilisé pour limiter la table aux ouvertures rencontrées.
    source_dir permet de fournir cinq TSV locaux, notamment dans les tests.
    refresh reconstruit le cache à partir des sources de la révision choisie.
    """
    cache_dir = cfg.OPENINGS_CACHE_DIR
    cache = cache_dir / "openings_complet.parquet"
    manifest = cache_dir / "sources_reference.json"
    cache_valid = False

    if source_dir is None and cache.is_file() and manifest.is_file() and not refresh:
        metadata = json.loads(manifest.read_text(encoding="utf-8"))
        cache_valid = metadata.get("revision") == cfg.OPENINGS_REFERENCE_REV

    if cache_valid:
        reference = pd.read_parquet(cache)
    else:
        directory = Path(source_dir) if source_dir is not None else download_sources()
        reference = read_reference(directory)

        if source_dir is None:
            cache_dir.mkdir(parents=True, exist_ok=True)
            reference.to_parquet(cache, index=False)
            reference.to_csv(cache_dir / "openings_complet.csv", index=False)
            metadata = {
                "repository": "https://github.com/lichess-org/chess-openings",
                "revision": cfg.OPENINGS_REFERENCE_REV,
                "built_utc": datetime.now(timezone.utc).isoformat(),
                "rows": len(reference),
                "sha256": {
                    letter
                    + ".tsv": sha256(
                        (directory / (letter + ".tsv")).read_bytes()
                    ).hexdigest()
                    for letter in "abcde"
                },
            }
            manifest.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    cfg.DATA_DIR.mkdir(parents=True, exist_ok=True)
    reference.to_parquet(cfg.DATA_DIR / "openings_complet.parquet", index=False)
    reference.to_csv(cfg.DATA_DIR / "openings_complet.csv", index=False)
    return reference


if __name__ == "__main__":
    print(build_openings())




## avant avec maxime. 
# create_openings_df.py
import pandas as pd
import os

# Liste d'exemple : 50 ouvertures populaires avec ECO, nom, premiers coups
eco_db = [
    {"eco": "A00", "name": "Uncommon / Flank Opening", "moves": ["a3"]},
    {"eco": "A01", "name": "Nimzowitsch–Larsen Attack", "moves": ["b3"]},
    {"eco": "A02", "name": "Bird's Opening", "moves": ["f4"]},
    {"eco": "A04", "name": "Réti Opening", "moves": ["Nf3"]},
    {"eco": "A10", "name": "English Opening", "moves": ["c4"]},
    {"eco": "B01", "name": "Scandinavian Defense", "moves": ["e4", "d5"]},
    {"eco": "B02", "name": "Alekhine's Defense", "moves": ["e4", "Nf6"]},
    {"eco": "B07", "name": "Pirc Defense", "moves": ["e4", "d6", "d4", "Nf6"]},
    {"eco": "B08", "name": "Pirc Defense, Classical", "moves": ["e4", "d6", "d4", "Nf6", "Nc3", "g6"]},
    {"eco": "B10", "name": "Caro-Kann Defense", "moves": ["e4", "c6"]},
    {"eco": "B12", "name": "Caro-Kann Defense, Advance", "moves": ["e4", "c6", "d4", "d5", "e5"]},
    {"eco": "B20", "name": "Sicilian Defense", "moves": ["e4", "c5"]},
    {"eco": "B21", "name": "Sicilian Defense, Smith-Morra", "moves": ["e4", "c5", "d4"]},
    {"eco": "B22", "name": "Sicilian, Alapin", "moves": ["e4", "c5", "c3"]},
    {"eco": "B23", "name": "Sicilian, Closed", "moves": ["e4", "c5", "Nc3"]},
    {"eco": "B27", "name": "Sicilian, Closed, Classical", "moves": ["e4", "c5", "Nc3", "Nc6"]},
    {"eco": "B30", "name": "Sicilian, Najdorf", "moves": ["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6"]},
    {"eco": "B40", "name": "Sicilian, Kan", "moves": ["e4", "c5", "Nc3", "Nc6", "Nf3", "e6"]},
    {"eco": "C00", "name": "French Defense", "moves": ["e4", "e6"]},
    {"eco": "C02", "name": "French, Advance", "moves": ["e4", "e6", "d4", "d5", "e5"]},
    {"eco": "C10", "name": "French, Classical", "moves": ["e4", "e6", "d4", "d5", "Nc3"]},
    {"eco": "C20", "name": "King's Pawn Game", "moves": ["e4"]},
    {"eco": "C21", "name": "Center Game", "moves": ["e4", "e5", "d4"]},
    {"eco": "C23", "name": "Bishop's Opening", "moves": ["e4", "e5", "Bc4"]},
    {"eco": "C25", "name": "Vienna Game", "moves": ["e4", "e5", "Nc3"]},
    {"eco": "C30", "name": "King's Gambit", "moves": ["e4", "e5", "f4"]},
    {"eco": "C40", "name": "King's Knight Opening", "moves": ["e4", "e5", "Nf3"]},
    {"eco": "C41", "name": "Philidor Defense", "moves": ["e4", "e5", "Nf3", "d6"]},
    {"eco": "C42", "name": "Petrov's Defense", "moves": ["e4", "e5", "Nf3", "Nf6"]},
    {"eco": "C43", "name": "Bishop's Opening", "moves": ["e4", "e5", "Bc4", "Bc5"]},
    {"eco": "C44", "name": "King's Pawn Game", "moves": ["e4", "e5", "Nf3", "Nc6"]},
    {"eco": "C45", "name": "Scotch Game", "moves": ["e4", "e5", "Nf3", "Nc6", "d4"]},
    {"eco": "C50", "name": "Italian Game", "moves": ["e4", "e5", "Nf3", "Nc6", "Bc4"]},
    {"eco": "C55", "name": "Two Knights Defense", "moves": ["e4", "e5", "Nf3", "Nc6", "Bc4", "Nf6"]},
    {"eco": "C60", "name": "Ruy Lopez", "moves": ["e4", "e5", "Nf3", "Nc6", "Bb5"]},
    {"eco": "C65", "name": "Ruy Lopez, Berlin Defense", "moves": ["e4", "e5", "Nf3", "Nc6", "Bb5", "Nf6"]},
    {"eco": "C70", "name": "Ruy Lopez, Morphy Defense", "moves": ["e4", "e5", "Nf3", "Nc6", "Bb5", "a6"]},
    {"eco": "C78", "name": "Ruy Lopez, Modern Steinitz Defense", "moves": ["e4", "e5", "Nf3", "Nc6", "Bb5", "d6"]},
    {"eco": "C80", "name": "Ruy Lopez, Open", "moves": ["e4", "e5", "Nf3", "Nc6", "Bb5", "a6", "Ba4", "Nf6"]},
    {"eco": "D00", "name": "Queen's Pawn Game", "moves": ["d4"]},
    {"eco": "D02", "name": "Queen's Pawn Game, Chigorin", "moves": ["d4", "d5", "Nc3"]},
    {"eco": "D06", "name": "Queen's Gambit", "moves": ["d4", "d5", "c4"]},
    {"eco": "D10", "name": "Queen's Gambit Declined", "moves": ["d4", "d5", "c4", "e6"]},
    {"eco": "D20", "name": "Queen's Gambit Accepted", "moves": ["d4", "d5", "c4", "dxc4"]},
    {"eco": "D30", "name": "Queen's Gambit Declined, Tarrasch", "moves": ["d4", "d5", "c4", "e6", "Nc3", "Nf6"]},
    {"eco": "D35", "name": "Queen's Gambit Declined, Exchange", "moves": ["d4", "d5", "c4", "e6", "Nc3", "dxc4"]},
    {"eco": "D40", "name": "King's Indian Defense", "moves": ["d4", "Nf6", "c4", "g6"]},
    {"eco": "D50", "name": "Queen's Gambit Declined, Orthodox", "moves": ["d4", "d5", "c4", "e6", "Nc3", "Nf6", "Nf3", "Be7"]},
    {"eco": "E00", "name": "Catalan Opening", "moves": ["d4", "Nf6", "c4", "e6", "g3"]},
    {"eco": "E10", "name": "King's Indian Attack", "moves": ["Nf3", "d5", "g3"]},
]

# Transformer la liste en DataFrame
df_openings = pd.DataFrame(eco_db)

# Répertoire Data du projet (même dossier que Master_file.py)
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "Data")
os.makedirs(DATA_DIR, exist_ok=True)

# Chemin complet pour sauvegarder
save_path = os.path.join(DATA_DIR, "openings.parquet")

# Sauvegarde en parquet
df_openings.to_parquet(save_path)

print(f"DataFrame ouvertures créé et sauvegardé dans {save_path}")
print(df_openings.head())

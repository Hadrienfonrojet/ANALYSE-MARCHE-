"""Paramètres communs du projet, lus par le master et le notebook.

Les valeurs du .env privé remplacent les valeurs par défaut ci-dessous.
Aucun secret n'est copié dans les résultats ni dans le manifeste d'expérience.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv


## Partie 1 - Localiser le projet et lire la configuration privée

ROOT = (
    Path(__file__).resolve().parent
)  ## Dossier contenant ce fichier de configuration.
load_dotenv(ROOT / ".env")  ## Lire le .env local s'il existe, sans l'envoyer ailleurs.

# Chemins historiques, remplacés quand create_run() crée une expérience.
DATA_DIR = ROOT / "Data"
RESULTS_DIR = ROOT / "Resultats"
DATA_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)
RUN_DIR = None


## Partie 2 - Choisir les comptes et la taille de collecte

# SEED_USERS est une liste de pseudos, pas un DataFrame de parties.
SEED_USERS = [
    name.strip().lower()
    for name in os.getenv("LICHESS_SEEDS", "yuuki-asuna").split(",")
    if name.strip()
]
FORMATS = ["bullet", "blitz", "rapid", "classical"]
USERS_PER_SEED = int(os.getenv("USERS_PER_SEED", "30"))
GAMES_PER_FORMAT = int(os.getenv("GAMES_PER_FORMAT", "60"))


## Partie 3 - Référentiel complet et fenêtre d'identification

# Révision figée des cinq tables officielles pour reproduire la classification.
OPENINGS_REFERENCE_REV = "712a58be746c143f4ab935b68acc50f4bac813eb"
OPENINGS_CACHE_DIR = ROOT / "References"
OPENINGS_REFERENCE_DIR = (
    OPENINGS_CACHE_DIR / "lichess_openings" / OPENINGS_REFERENCE_REV
)

# Un coup complet = un coup blanc + un coup noir, soit deux demi-coups.
OPENING_MAX_FULLMOVES = int(os.getenv("OPENING_MAX_FULLMOVES", "10"))
OPENING_MIN_FULLMOVES = int(os.getenv("OPENING_MIN_FULLMOVES", "5"))


## Partie 4 - Analyse et stockage facultatif

# Une seule régression multiple lisible remplace les anciennes batteries de modèles.
RUN_REGRESSIONS = os.getenv("RUN_REGRESSIONS", "true").lower() == "true"
S3_BUCKET = os.getenv("S3_BUCKET", "hadrien2703")
S3_PREFIX = os.getenv("S3_PREFIX", "diffusion/projet_ouvertures").strip("/")


def get_lichess_token():
    """Lire le jeton au moment de l'appel ; aucun jeton n'est écrit dans le code."""
    return os.getenv("LICHESS_TOKEN") or None


## Partie 5 - Créer une expérience sans effacer les précédentes


def create_run():
    """Créer Data/ et Resultats/ sous un nouvel identifiant daté.

    Les variables globales de chemin sont mises à jour ; les modules lisent
    cfg.DATA_DIR au moment du calcul pour pointer sur cette nouvelle expérience.
    """
    global RUN_DIR, DATA_DIR, RESULTS_DIR

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    run_id = timestamp + "_" + uuid4().hex[:8]
    RUN_DIR = ROOT / "Collectes" / run_id
    RUN_DIR.mkdir(parents=True, exist_ok=False)  ## Ne pas réutiliser un ancien dossier.

    DATA_DIR = RUN_DIR / "Data"
    RESULTS_DIR = RUN_DIR / "Resultats"
    DATA_DIR.mkdir()
    RESULTS_DIR.mkdir()

    parameters = {
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "seeds": SEED_USERS,
        "formats": FORMATS,
        "run_regressions": RUN_REGRESSIONS,
    }
    (RUN_DIR / "experience.json").write_text(
        json.dumps(parameters, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return RUN_DIR

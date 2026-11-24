"""Paramètres publics, chemins du projet et lecture du .env privé."""

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import json
import os
from dotenv import load_dotenv

## Partie 1 — Chemins : aucun dossier n’est créé lors d’un simple import

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
DATA_DIR = ROOT / "Data"
RESULTS_DIR = ROOT / "Resultats"
RUN_DIR = None

## Partie 2 — Collecte : comptes, cadences et plafond par requête

SEED_USERS = [
    u.strip().lower()
    for u in os.getenv("LICHESS_SEEDS", "yuuki-asuna").split(",")
    if u.strip()
]
FORMATS = ["bullet", "blitz", "rapid", "classical"]
USERS_PER_SEED = int(os.getenv("USERS_PER_SEED", "30"))
GAMES_PER_FORMAT = int(os.getenv("GAMES_PER_FORMAT", "60"))
RANDOM_SEED = 73

## Partie 3 — Identification : une version figée et une profondeur de 5 à 10 coups

OPENINGS_REFERENCE_REV = "712a58be746c143f4ab935b68acc50f4bac813eb"
OPENINGS_CACHE_DIR = ROOT / "References"
OPENINGS_REFERENCE_DIR = (
    OPENINGS_CACHE_DIR / "lichess_openings" / OPENINGS_REFERENCE_REV
)
OPENING_MAX_FULLMOVES = int(os.getenv("OPENING_MAX_FULLMOVES", "10"))
OPENING_MIN_FULLMOVES = int(os.getenv("OPENING_MIN_FULLMOVES", "5"))
RUN_REGRESSIONS = os.getenv("RUN_REGRESSIONS", "true").lower() == "true"
## "famille" : Sicilian Defense, French Defense… (environ 40 groupes, effectifs suffisants).
## "variante" : nom complet du référentiel (des centaines de groupes de 1 à 5 parties).
NIVEAU_OUVERTURE = os.getenv("NIVEAU_OUVERTURE", "famille")

## Partie 4 — Destination publique de configuration, identifiants privés dans .env

S3_BUCKET = os.getenv("S3_BUCKET", "hadrien2703")
S3_PREFIX = os.getenv("S3_PREFIX", "diffusion/projet_ouvertures").strip("/")


def get_lichess_token():
    """Lire le jeton au moment de la requête, sans l’enregistrer dans les résultats."""
    return os.getenv("LICHESS_TOKEN") or os.getenv("jeton_api") or None


## Partie 5 — Créer un nouveau dossier à chaque expérience


def create_run():
    """Créer une collecte unique, conserver Data et Resultats, écrire les paramètres."""
    global RUN_DIR, DATA_DIR, RESULTS_DIR
    run_id = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:8]
    )
    RUN_DIR = ROOT / "Collectes" / run_id
    DATA_DIR, RESULTS_DIR = RUN_DIR / "Data", RUN_DIR / "Resultats"
    DATA_DIR.mkdir(parents=True, exist_ok=False)
    RESULTS_DIR.mkdir()
    parameters = {
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "seeds": SEED_USERS,
        "formats": FORMATS,
        "random_seed": RANDOM_SEED,
        "run_regressions": RUN_REGRESSIONS,
        "niveau_ouverture": NIVEAU_OUVERTURE,
        "reference_revision": OPENINGS_REFERENCE_REV,
        "opening_max_fullmoves": OPENING_MAX_FULLMOVES,
        "opening_min_fullmoves": OPENING_MIN_FULLMOVES,
        "games_per_format": GAMES_PER_FORMAT,
    }
    (RUN_DIR / "experience.json").write_text(
        json.dumps(parameters, ensure_ascii=False, indent=2)
    )
    return RUN_DIR
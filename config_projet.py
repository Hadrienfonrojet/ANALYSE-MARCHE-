"""Paramètres du projet. Renseigner 5 véritables pseudos via LICHESS_SEEDS dans .env."""
import os
from pathlib import Path
from dotenv import load_dotenv
ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env')
DATA_DIR = ROOT / 'Data'
RESULTS_DIR = ROOT / 'Resultats'
DATA_DIR.mkdir(exist_ok=True); RESULTS_DIR.mkdir(exist_ok=True)
SEED_USERS = [s.strip().lower() for s in os.getenv('LICHESS_SEEDS','yuuki-asuna').split(',') if s.strip()]
FORMATS = ['bullet','blitz','rapid','classical']
S3_BUCKET = os.getenv('S3_BUCKET','hadrien2703')
S3_PREFIX = os.getenv('S3_PREFIX','diffusion/projet_ouvertures').strip('/')

# Une expérience = un nouveau dossier ; aucun dossier existant n'est effacé.
from datetime import datetime, timezone
from uuid import uuid4
import json
RUN_DIR = None

def create_run():
    global RUN_DIR, DATA_DIR, RESULTS_DIR
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ') + '_' + uuid4().hex[:8]
    RUN_DIR = ROOT / 'Collectes' / run_id
    RUN_DIR.mkdir(parents=True, exist_ok=False)
    DATA_DIR = RUN_DIR / 'Data'
    RESULTS_DIR = RUN_DIR / 'Resultats'
    DATA_DIR.mkdir(); RESULTS_DIR.mkdir()
    (RUN_DIR / 'experience.json').write_text(json.dumps({
        'run_id': run_id, 'created_utc': datetime.now(timezone.utc).isoformat(),
        'seeds': SEED_USERS, 'formats': FORMATS,
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    return RUN_DIR

USERS_PER_SEED = int(os.getenv('USERS_PER_SEED', '30'))
GAMES_PER_FORMAT = int(os.getenv('GAMES_PER_FORMAT', '60'))

def get_lichess_token():
    """Lire le secret au moment de la requête, sans le stocker dans les sorties."""
    return os.getenv('LICHESS_TOKEN') or None

# Référentiel officiel figé : a.tsv à e.tsv, disponibles même hors réseau.
OPENINGS_REFERENCE_REV = '712a58be746c143f4ab935b68acc50f4bac813eb'
OPENINGS_CACHE_DIR = ROOT / 'References'
OPENINGS_REFERENCE_DIR = OPENINGS_CACHE_DIR / 'lichess_openings' / OPENINGS_REFERENCE_REV

# Un coup complet = un coup blanc + un coup noir.
OPENING_MAX_FULLMOVES = int(os.getenv('OPENING_MAX_FULLMOVES', '10'))
OPENING_MIN_FULLMOVES = int(os.getenv('OPENING_MIN_FULLMOVES', '5'))

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

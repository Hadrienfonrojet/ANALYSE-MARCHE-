"""Collecte API Lichess, référentiel observé, nettoyage, analyse et export optionnel."""
import argparse
import os
import pandas as pd
from config_projet import SEED_USERS, DATA_DIR
from Scripts_generation_data.Collecte_enrichie import discover_stratified, collect_games
from Scripts_generation_data.Creation_openings_complet import build_openings
from Nettoyage_donnees import prepare
from Analyse_ouvertures import analyze

def run_pipeline(users_per_seed=30, games_per_format=60, skip_collect=False, upload=False):
    if users_per_seed < 1 or games_per_format < 1:
        raise ValueError('Les nombres de joueurs et de parties doivent être positifs.')
    if skip_collect:
        raw = pd.read_parquet(DATA_DIR / 'games_enrichies_raw.parquet')
    else:
        if not SEED_USERS or any(s.startswith('pseudo_') for s in SEED_USERS):
            raise ValueError('Renseigner de vrais pseudos dans LICHESS_SEEDS.')
        token = os.getenv('LICHESS_TOKEN') or os.getenv('jeton_api')
        users = discover_stratified(SEED_USERS, token, users_per_seed)
        raw = collect_games(users, token, games_per_format)
    openings = build_openings(raw)
    clean = prepare(raw, openings)
    tests = analyze(clean)
    if upload:
        from Stockage_SSPCloud import upload_outputs
        upload_outputs()
    return clean, tests

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--users-per-seed', type=int, default=30)
    parser.add_argument('--games-per-format', type=int, default=60)
    parser.add_argument('--skip-collect', action='store_true')
    parser.add_argument('--upload', action='store_true')
    return run_pipeline(**vars(parser.parse_args(argv)))

if __name__ == '__main__':
    main()

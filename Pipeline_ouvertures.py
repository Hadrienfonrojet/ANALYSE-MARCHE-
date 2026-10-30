"""Collecte API Lichess, référentiel observé, nettoyage, analyse et export optionnel."""
import argparse
import os
import pandas as pd
import config_projet as cfg
from config_projet import SEED_USERS
from Scripts_generation_data.Collecte_enrichie import discover_stratified, collect_games
from Scripts_generation_data.Creation_openings_complet import build_openings
from Nettoyage_donnees import prepare
from Analyse_ouvertures import analyze

def run_pipeline(users_per_seed=cfg.USERS_PER_SEED, games_per_format=cfg.GAMES_PER_FORMAT, skip_collect=False, upload=False, raw_file=None):
    if users_per_seed < 1 or games_per_format < 1:
        raise ValueError('Les nombres de joueurs et de parties doivent être positifs.')
    source = None
    if skip_collect:
        if raw_file is None:
            raise ValueError('--skip-collect exige --raw-file chemin/vers/games_enrichies_raw.parquet')
        source = pd.io.common.stringify_path(raw_file)
        if not __import__('pathlib').Path(source).is_file():
            raise FileNotFoundError(source)
    run_dir = cfg.create_run()
    print('Expérience :', run_dir)
    if skip_collect:
        raw = pd.read_parquet(source)
        raw.to_parquet(cfg.DATA_DIR / 'games_enrichies_raw.parquet', index=False)
    else:
        if not SEED_USERS or any(s.startswith('pseudo_') for s in SEED_USERS):
            raise ValueError('Renseigner de vrais pseudos dans LICHESS_SEEDS.')
        token = cfg.get_lichess_token()
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
    parser.add_argument('--users-per-seed', type=int, default=cfg.USERS_PER_SEED)
    parser.add_argument('--games-per-format', type=int, default=cfg.GAMES_PER_FORMAT)
    parser.add_argument('--skip-collect', action='store_true')
    parser.add_argument('--upload', action='store_true')
    parser.add_argument('--raw-file', help='Fichier brut à réanalyser dans une nouvelle expérience')
    return run_pipeline(**vars(parser.parse_args(argv)))

if __name__ == '__main__':
    main()

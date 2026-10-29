"""Point d'entrée complémentaire, préserve Master_file.py et le pipeline historique."""
import argparse, os
from config_projet import SEED_USERS,DATA_DIR
from Scripts_generation_data.Collecte_enrichie import discover_stratified,collect_games
from Nettoyage_donnees import prepare
from Analyse_ouvertures import analyze
import pandas as pd

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--users-per-seed',type=int,default=30)
    parser.add_argument('--games-per-format',type=int,default=60)
    parser.add_argument('--skip-collect',action='store_true')
    parser.add_argument('--upload',action='store_true')
    args=parser.parse_args()
    if not args.skip_collect:
        if len(SEED_USERS)!=5: raise ValueError('Configurer exactement cinq pseudos réels dans LICHESS_SEEDS du fichier .env')
        token=os.getenv('jeton_api') or os.getenv('LICHESS_TOKEN')
        users=discover_stratified(SEED_USERS,token,args.users_per_seed)
        raw=collect_games(users,token,args.games_per_format)
    else:
        raw=pd.read_parquet(DATA_DIR/'games_enrichies_raw.parquet')
    openings_path=DATA_DIR/'openings_complet.parquet'
    if not openings_path.exists():
        from Scripts_generation_data.Creation_openings_complet import build_openings
        build_openings()
    clean=prepare(raw,pd.read_parquet(openings_path) if openings_path.exists() else None)
    analyze(clean)
    if args.upload:
        from Stockage_SSPCloud import upload_outputs
        upload_outputs()
if __name__=='__main__': main()

"""Comprendre et lancer toutes les étapes du projet Lichess.

Ordre de lecture conseillé
-------------------------
1. docs/Introduction_aux_ouvertures.md : que représente une ouverture ?
2. Ce fichier : comment les étapes s'enchaînent et quels fichiers elles produisent.
3. Scripts_generation_data/Creation_openings_complet.py : référentiel des ouvertures.
4. Analyse_data.ipynb : hypothèses, calculs et interprétation des tests.

Exemple depuis la racine du dépôt :
    python Master_file.py --users-per-seed 1 --games-per-format 5

Le programme ne supprime aucune ancienne collecte. Chaque lancement crée un
nouveau dossier Collectes/<identifiant>/ avec ses données et ses résultats.
Les fonctions ci-dessous font réellement le travail d'orchestration ; elles
peuvent aussi être appelées séparément dans Python pour comprendre chaque étape.
"""

import argparse
import json
from pathlib import Path

import pandas as pd
import config_projet as cfg
from Scripts_generation_data.Import_des_users import discover_stratified
from Scripts_generation_data.Import_une_partie import (
    import_games_enriched as collect_games,
)
from Scripts_generation_data.Creation_openings_complet import build_openings
from Nettoyage_donnees import prepare
from Analyse_ouvertures import analyze


def verifier_parametres(users_per_seed, games_per_format, skip_collect, raw_file):
    """Vérifier les entrées avant de créer un dossier ou de lancer des requêtes.

    --skip-collect réutilise un fichier brut existant. Il ne relance pas l'API.
    Sans cette option, les pseudos viennent de config_projet.py et du .env privé.
    """
    if users_per_seed < 1 or games_per_format < 1:
        raise ValueError("Les nombres de joueurs et de parties doivent être positifs.")
    if skip_collect:
        if raw_file is None:
            raise ValueError(
                "--skip-collect exige --raw-file chemin/vers/games_enrichies_raw.parquet"
            )
        source = Path(raw_file).expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        return source
    if raw_file is not None:
        raise ValueError(
            "Utiliser --skip-collect avec --raw-file pour réanalyser une base."
        )
    if not cfg.SEED_USERS or any(s.startswith("pseudo_") for s in cfg.SEED_USERS):
        raise ValueError("Renseigner de vrais pseudos dans LICHESS_SEEDS.")
    return None


def creer_experience(users_per_seed, games_per_format, source=None, opening_moves=None):
    """Créer un dossier neuf et enregistrer les paramètres non secrets.

    experience.json indique la taille de collecte demandée et l'origine des
    données. Les anciens dossiers restent présents. Aucun jeton n'y est écrit.
    """
    run_dir = cfg.create_run()
    manifest = run_dir / "experience.json"
    parameters = json.loads(manifest.read_text(encoding="utf-8"))
    parameters.update(
        users_per_seed=users_per_seed,
        games_per_format=games_per_format,
        mode="reanalyse" if source is not None else "collecte",
        source_file=str(source) if source is not None else None,
        opening_reference_revision=cfg.OPENINGS_REFERENCE_REV,
        opening_max_fullmoves=opening_moves or cfg.OPENING_MAX_FULLMOVES,
        opening_min_fullmoves=cfg.OPENING_MIN_FULLMOVES,
    )
    manifest.write_text(
        json.dumps(parameters, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Dossier de cette expérience :", run_dir)
    return run_dir


def obtenir_parties(users_per_seed, games_per_format, source=None):
    """Collecter les parties via l'API, ou copier une ancienne base dans ce run.

    discover_stratified découvre les comptes à partir de leurs adversaires.
    collect_games demande les parties et leur champ opening à l'API Lichess.
    Sorties : users_list_stratified.parquet et games_enrichies_raw.parquet.
    La réanalyse ne modifie pas le fichier source.
    """
    if source is not None:
        print("1. Lecture de la base existante :", source)
        raw = pd.read_parquet(source)
        raw.to_parquet(cfg.DATA_DIR / "games_enrichies_raw.parquet", index=False)
    else:
        print("1. Découverte des joueurs et collecte des parties Lichess")
        token = cfg.get_lichess_token()
        users = discover_stratified(cfg.SEED_USERS, token, users_per_seed)
        raw = collect_games(users, token, games_per_format)
    if raw.empty:
        raise ValueError(
            "Aucune partie disponible ; impossible de construire les analyses."
        )
    print("Observations brutes :", len(raw))
    return raw


def creer_referentiel_ouvertures(raw):
    """Télécharger et réunir les cinq tables officielles complètes Lichess.

    Le fichier source de cette étape est :
    Scripts_generation_data/Creation_openings_complet.py.
    Sortie : Data/openings_complet.parquet dans le dossier de cette expérience.
    Ce référentiel contient toutes les lignes officielles a.tsv à e.tsv, même
    si ces ouvertures ne figurent pas dans les parties collectées.
    """
    print("2. Référentiel complet officiel Lichess : a.tsv à e.tsv")
    openings = build_openings()
    print("Lignes officielles ECO, nom et suite de coups :", len(openings))
    print("Fichier des ouvertures :", cfg.DATA_DIR / "openings_complet.parquet")
    return openings


def nettoyer_et_construire_variables(raw, openings, opening_moves=None):
    """Préparer les variables utiles aux analyses, sans supprimer de fichiers.

    prepare nettoie les doublons joueur/partie, calcule le score, les tranches
    Elo et les historiques de répétition avec ou sans distinction de couleur.
    Sorties : Data/games_clean.parquet et Data/players_openings.parquet.
    """
    print("3. Nettoyage et construction des variables de répétition")
    clean = prepare(raw, openings, max_fullmoves=opening_moves)
    clean["opening_identification_status"].value_counts().to_csv(
        cfg.RESULTS_DIR / "bilan_identification_ouvertures.csv"
    )
    print("Observations analysables :", len(clean))
    return clean


def lancer_analyses(clean):
    """Produire les descriptifs, les χ², les tableaux détaillés et les graphiques.

    Le détail pédagogique des tests se trouve dans Analyse_data.ipynb.
    Les fonctions du χ² et des répétitions sont dans analyses/Tests_repetition.py.
    Sorties : Resultats/ et Resultats/repetition/ de cette expérience.
    Les analyses sont corrélationnelles ; les valeurs p restent exploratoires
    car des parties d'un même joueur ne sont pas indépendantes.
    """
    print("4. Analyses descriptives et tests statistiques")
    tests = analyze(clean)
    print("Tableaux et figures :", cfg.RESULTS_DIR)
    print(
        "Tests de répétition :",
        cfg.RESULTS_DIR / "repetition/tests_repetition_chi2.csv",
    )
    return tests


def run_pipeline(
    users_per_seed=cfg.USERS_PER_SEED,
    games_per_format=cfg.GAMES_PER_FORMAT,
    skip_collect=False,
    upload=False,
    raw_file=None,
    opening_moves=None,
):
    """Exécuter les étapes dans l'ordre et renvoyer les données et les tests.

    L'envoi SSP Cloud intervient uniquement si upload=True. Les identifiants
    sont lus dans l'environnement privé ; boto3 est installé par requirements.txt.
    """
    if opening_moves is not None and opening_moves < cfg.OPENING_MIN_FULLMOVES:
        raise ValueError("La limite est inférieure au minimum de coups configuré.")
    source = verifier_parametres(
        users_per_seed, games_per_format, skip_collect, raw_file
    )
    creer_experience(users_per_seed, games_per_format, source, opening_moves)
    raw = obtenir_parties(users_per_seed, games_per_format, source)
    openings = creer_referentiel_ouvertures(raw)
    clean = nettoyer_et_construire_variables(raw, openings, opening_moves)
    tests = lancer_analyses(clean)
    if upload:
        print("5. Envoi de cette expérience vers SSP Cloud")
        from Stockage_SSPCloud import upload_outputs

        upload_outputs()
    print("Expérience terminée. Anciennes collectes conservées.")
    return clean, tests


def main(argv=None):
    """Lire les options puis appeler le déroulé détaillé ci-dessus."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--users-per-seed",
        type=int,
        default=cfg.USERS_PER_SEED,
        help="Nombre maximum de joueurs découverts par graine",
    )
    parser.add_argument(
        "--games-per-format",
        type=int,
        default=cfg.GAMES_PER_FORMAT,
        help="Nombre maximum de parties par joueur et cadence",
    )
    parser.add_argument(
        "--skip-collect",
        action="store_true",
        help="Réutiliser une base brute existante",
    )
    parser.add_argument("--raw-file", help="Chemin de la base brute à réanalyser")
    parser.add_argument(
        "--opening-moves",
        type=int,
        choices=[5, 10],
        default=cfg.OPENING_MAX_FULLMOVES,
        help="Identifier avec les 5 ou 10 premiers coups complets",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Envoyer les sorties vers SSP Cloud après analyse",
    )
    return run_pipeline(**vars(parser.parse_args(argv)))


if __name__ == "__main__":
    main()





## avant maxime 
import subprocess
import sys
import os
import shutil
import pandas as pd
from dotenv import load_dotenv

from Scripts_generation_data.Import_des_users import discover_users_random_walk

try:
    import boto3
except ModuleNotFoundError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "boto3"])
    import boto3

load_dotenv()

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "Data")
OPENINGS_FILE = os.path.join(DATA_DIR, "openings.parquet")
os.makedirs(DATA_DIR, exist_ok=True)

def nettoyer_data(data_dir):
    for file in os.listdir(data_dir):
        path = os.path.join(data_dir, file)
        if os.path.isfile(path): os.remove(path)

def prepare_output_folder(src=DATA_DIR):
    dst = os.path.join(BASE_DIR, "Data_projet_info")
    if os.path.exists(dst): shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return dst

def upload_folder_to_s3(local_folder, bucket, prefix):
    s3 = boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
        endpoint_url=f"https://{os.getenv('AWS_S3_ENDPOINT', 'minio.lab.sspcloud.fr')}",
        region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    )
    
    try:
        objs = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        if "Contents" in objs:
            for o in objs["Contents"]: s3.delete_object(Bucket=bucket, Key=o["Key"])
    except: pass

    print(f"🚀 Upload vers s3://{bucket}/{prefix}...")
    for root, _, files in os.walk(local_folder):
        for file in files:
            path = os.path.join(root, file)
            rel = os.path.relpath(path, local_folder)
            key = f"{prefix}/{rel}"
            try: s3.upload_file(path, bucket, key, ExtraArgs={'ACL': 'public-read'})
            except: s3.upload_file(path, bucket, key)
    
    print("✅ Upload terminé.")

def lancer_creation_openings():
    script = os.path.join(BASE_DIR, "Scripts_generation_data", "Creation_Df_openings.py")
    subprocess.run([sys.executable, script], check=True)

def main():
    print("=== DÉBUT DU PIPELINE (MODE RANDOM WALK) ===")

    # 1. Nouveaux Inputs
    seed_user = input("Pseudo du joueur de départ (ex: 'thibault') : ")
    target_users = int(input("Combien de joueurs uniques voulez-vous trouver ? "))
    nb_parties = int(input("Combien de parties à télécharger par joueur ? "))

    token = os.environ.get("jeton_api")
    if not token:
        print("❌ Erreur : 'jeton_api' manquant.")
        return

    nettoyer_data(DATA_DIR)
    lancer_creation_openings()

    # 2. Découverte des users par Marche Aléatoire
    discover_users_random_walk(seed_user, target_users, token)

    # 3. Import des parties
    from Scripts_generation_data.Import_une_partie import import_games_df
    print(f"\n=== Téléchargement des parties ===")
    df_games = import_games_df(nb_parties, token)

    if not df_games.empty:
        df_games.to_parquet(os.path.join(DATA_DIR, "dfs_games.parquet"), index=False)
        out = prepare_output_folder()
        upload_folder_to_s3(out, "tristant", "diffusion")
        nettoyer_data(DATA_DIR)
        print("✅ Terminé avec succès.")
    else:
        print("⚠️ Aucune partie récupérée.")

if __name__ == "__main__":
    main()

"""Pipeline original complété ; une collecte = un dossier conservé."""

## ########################################################################
## ANCIEN MASTER À SUPPRESSIONS AUTOMATIQUES — NON EXÉCUTÉ
## import subprocess
## import sys
## import os
## import shutil
## import pandas as pd
## from dotenv import load_dotenv
##
## from Scripts_generation_data.Import_des_users import discover_users_random_walk
##
## try:
##     import boto3
## except ModuleNotFoundError:
##     subprocess.check_call([sys.executable, "-m", "pip", "install", "boto3"])
##     import boto3
##
## load_dotenv()
##
## BASE_DIR = os.path.dirname(__file__)
## DATA_DIR = os.path.join(BASE_DIR, "Data")
## OPENINGS_FILE = os.path.join(DATA_DIR, "openings.parquet")
## os.makedirs(DATA_DIR, exist_ok=True)
##
## def nettoyer_data(data_dir):
##     for file in os.listdir(data_dir):
##         path = os.path.join(data_dir, file)
##         if os.path.isfile(path): os.remove(path)
##
## def prepare_output_folder(src=DATA_DIR):
##     dst = os.path.join(BASE_DIR, "Data_projet_info")
##     if os.path.exists(dst): shutil.rmtree(dst)
##     shutil.copytree(src, dst)
##     return dst
##
## def upload_folder_to_s3(local_folder, bucket, prefix):
##     s3 = boto3.client(
##         "s3",
##         aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
##         aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
##         aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
##         endpoint_url=f"https://{os.getenv('AWS_S3_ENDPOINT', 'minio.lab.sspcloud.fr')}",
##         region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1")
##     )
##
##     try:
##         objs = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
##         if "Contents" in objs:
##             for o in objs["Contents"]: s3.delete_object(Bucket=bucket, Key=o["Key"])
##     except: pass
##
##     print(f"🚀 Upload vers s3://{bucket}/{prefix}...")
##     for root, _, files in os.walk(local_folder):
##         for file in files:
##             path = os.path.join(root, file)
##             rel = os.path.relpath(path, local_folder)
##             key = f"{prefix}/{rel}"
##             try: s3.upload_file(path, bucket, key, ExtraArgs={'ACL': 'public-read'})
##             except: s3.upload_file(path, bucket, key)
##
##     print("✅ Upload terminé.")
##
## def lancer_creation_openings():
##     script = os.path.join(BASE_DIR, "Scripts_generation_data", "Creation_Df_openings.py")
##     subprocess.run([sys.executable, script], check=True)
##
## def main():
##     print("=== DÉBUT DU PIPELINE (MODE RANDOM WALK) ===")
##
##     # 1. Nouveaux Inputs
##     seed_user = input("Pseudo du joueur de départ (ex: 'thibault') : ")
##     target_users = int(input("Combien de joueurs uniques voulez-vous trouver ? "))
##     nb_parties = int(input("Combien de parties à télécharger par joueur ? "))
##
##     token = os.environ.get("jeton_api")
##     if not token:
##         print("❌ Erreur : 'jeton_api' manquant.")
##         return
##
##     nettoyer_data(DATA_DIR)
##     lancer_creation_openings()
##
##     # 2. Découverte des users par Marche Aléatoire
##     discover_users_random_walk(seed_user, target_users, token)
##
##     # 3. Import des parties
##     from Scripts_generation_data.Import_une_partie import import_games_df
##     print(f"\n=== Téléchargement des parties ===")
##     df_games = import_games_df(nb_parties, token)
##
##     if not df_games.empty:
##         df_games.to_parquet(os.path.join(DATA_DIR, "dfs_games.parquet"), index=False)
##         out = prepare_output_folder()
##         upload_folder_to_s3(out, "ANCIEN_BUCKET", "diffusion")
##         nettoyer_data(DATA_DIR)
##         print("✅ Terminé avec succès.")
##     else:
##         print("⚠️ Aucune partie récupérée.")
##
## if __name__ == "__main__":
##     main()
## FIN ANCIEN MASTER À SUPPRESSIONS AUTOMATIQUES
## ########################################################################

import argparse
import importlib
import json
import os
from pathlib import Path
import time

import pandas as pd
import requests
import config_projet as cfg
from Nettoyage_donnees import sauvegarder_nettoyage
from Stockage_SSPCloud import upload_folder_to_s3
from Scripts_generation_data.Creation_Df_openings import creer_openings, identify_games


## Partie 1 - Garder les importeurs originaux ; choisir la liste de comptes


def preparer_utilisateurs(users=None, token=None):
    """--users utilise directement les cinq comptes ; sinon marche depuis les graines."""
    module = importlib.import_module("Scripts_generation_data.Import_des_users")
    module.DATA_DIR = str(
        cfg.DATA_DIR
    )  ## Seul le dossier de sortie est adapté pour cette collecte.
    if users:
        names = list(dict.fromkeys(u.strip().lower() for u in users if u.strip()))
        if not names:
            raise ValueError("Liste de comptes vide")
        result = pd.DataFrame({"user_id": names})
    else:
        frames = [
            module.discover_users_random_walk(seed, cfg.USERS_PER_SEED, token)
            for seed in cfg.SEED_USERS
        ]
        if not frames:
            raise ValueError("Aucune graine définie dans LICHESS_SEEDS")
        result = pd.concat(frames, ignore_index=True).drop_duplicates("user_id")
    result.to_parquet(cfg.DATA_DIR / "users_list_global.parquet", index=False)
    if cfg.RUN_DIR is not None:
        manifest = cfg.RUN_DIR / "experience.json"
        if manifest.exists():
            parameters = json.loads(manifest.read_text())
            parameters["selection_mode"] = (
                "liste_directe" if users else "decouverte_adversaires"
            )
            parameters["selected_users"] = result["user_id"].tolist()
            parameters["games_per_format"] = cfg.GAMES_PER_FORMAT
            manifest.write_text(json.dumps(parameters, ensure_ascii=False, indent=2))
    return result


## Partie 2 - Ajouter les coups et l’adversaire sans modifier Import_une_partie.py


def enrichir_parties(raw, token=None, session=None):
    """Réexporter les IDs par lots de 300, pour compléter les colonnes absentes.

    Le fichier d’import original reste inchangé. Ce deuxième passage API est donc
    volontaire : il récupère moves, status et les deux joueurs qui n’étaient pas
    conservés. Les IDs sont dédoublonnés avant les requêtes. La base brute reste
    sauvegardée même si ce complément échoue.
    """
    records = {}
    ids = raw["game_id"].dropna().astype(str).unique().tolist()
    http = session or requests
    headers = {"Accept": "application/x-ndjson", "Content-Type": "text/plain"}
    if token:
        headers["Authorization"] = "Bearer " + token
    for start in range(0, len(ids), 300):
        batch = ids[start : start + 300]
        for attempt in range(3):
            response = http.post(
                "https://lichess.org/api/games/export/_ids",
                data=",".join(batch),
                params={"moves": "true", "opening": "true"},
                headers=headers,
                timeout=(15, 180),
            )
            if response.status_code != 429:
                response.raise_for_status()
                break
            response.close()
            time.sleep(60)  ## Pause Lichess, une requête à la fois.
        else:
            raise RuntimeError(
                "Limite API : complément interrompu ; base brute conservée."
            )
        try:
            for line in response.iter_lines():
                if line:
                    game = json.loads(line)
                    records[game["id"]] = game
        finally:
            response.close()

    enriched = []
    for row in raw.to_dict("records"):
        game = records.get(str(row["game_id"]))
        if game is None:
            raise ValueError("Partie absente du complément : " + str(row["game_id"]))
        players = game.get("players", {})
        user = str(row["user_id"]).lower()
        colors = [
            c
            for c in ("white", "black")
            if players.get(c, {}).get("user", {}).get("id", "").lower() == user
        ]
        if len(colors) != 1:
            raise ValueError("Compte introuvable dans la partie : " + user)
        color = colors[0]
        opponent = players.get("black" if color == "white" else "white", {})
        opening = game.get("opening") or {}
        row.update(
            moves=game.get("moves"),
            variant=game.get("variant", "standard"),
            status=game.get("status"),
            api_eco=opening.get("eco"),
            api_opening_name=opening.get("name"),
            opponent_id=opponent.get("user", {}).get("id"),
            opponent_rating=opponent.get("rating"),
            color=color,
            rating=players[color].get("rating"),
            timestamp_ms=game.get("createdAt"),
            last_move_at=game.get("lastMoveAt"),
        )
        winner = game.get("winner")
        row["result"] = (
            "Draw" if winner is None else ("Win" if winner == color else "Loss")
        )
        enriched.append(row)
    return pd.DataFrame(enriched)


## Partie 3 - Un seul main, et aucune suppression de données


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--users", nargs="+", help="Comptes choisis ; accepte notamment cinq pseudos"
    )
    parser.add_argument(
        "--raw-file", type=Path, help="Réutiliser un parquet local, sans collecte"
    )
    parser.add_argument(
        "--enrich-api",
        action="store_true",
        help="Compléter un ancien parquet depuis ses IDs ; accès API explicite",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Conserver aussi la collecte sur S3 Hadrien",
    )
    args = parser.parse_args(argv)
    if args.raw_file and not args.raw_file.is_file():
        raise FileNotFoundError(args.raw_file)
    if cfg.GAMES_PER_FORMAT < 1 or cfg.USERS_PER_SEED < 1:
        raise ValueError("Paramètres de collecte strictement positifs requis")
    cfg.create_run()
    print("Nouvelle collecte conservée :", cfg.RUN_DIR)
    token = cfg.get_lichess_token() or os.getenv("jeton_api") or ""
    reference = creer_openings()

    if args.raw_file:
        raw = pd.read_parquet(args.raw_file)
    else:
        preparer_utilisateurs(args.users, token)
        parties = importlib.import_module("Scripts_generation_data.Import_une_partie")
        parties.DATA_DIR = str(cfg.DATA_DIR)
        ## Recharger seulement le dictionnaire, sans réécrire les fonctions d’origine.
        parties.openings_dict = {
            tuple(row.moves): (row.eco, row.name) for row in reference.itertuples()
        }
        raw = parties.import_games_df(cfg.GAMES_PER_FORMAT, token, max_workers=1)
    if raw.empty:
        raise ValueError("Aucune partie : dossier conservé pour diagnostic")
    raw.to_parquet(cfg.DATA_DIR / "dfs_games_brut.parquet", index=False)
    if args.enrich_api or not args.raw_file:
        raw = enrichir_parties(raw, token)
        raw.to_parquet(cfg.DATA_DIR / "dfs_games_enrichi.parquet", index=False)
    identified = identify_games(raw, reference)
    ## Si les coups sont absents, l’identification est inconnue, jamais remplacée par une fausse précision.
    identified.to_parquet(cfg.DATA_DIR / "dfs_games.parquet", index=False)
    cleaned = sauvegarder_nettoyage(identified, cfg.DATA_DIR / "games_clean.parquet")
    from Analyse_repetition_ouverture import analyser

    analyser(cleaned, cfg.RESULTS_DIR, run_regression=cfg.RUN_REGRESSIONS)
    if args.upload:
        upload_folder_to_s3(cfg.RUN_DIR)
    print("Terminé ; données locales conservées :", cfg.RUN_DIR)
    return cfg.RUN_DIR


if __name__ == "__main__":
    main()

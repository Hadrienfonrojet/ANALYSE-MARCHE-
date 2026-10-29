import subprocess
import sys
import os
import shutil
import pandas as pd
from dotenv import load_dotenv
from config_projet import S3_BUCKET, S3_PREFIX

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
    
    print(f"🚀 Upload vers s3://{bucket}/{prefix}...")
    for root, _, files in os.walk(local_folder):
        for file in files:
            path = os.path.join(root, file)
            rel = os.path.relpath(path, local_folder)
            key = f"{prefix}/{rel}"
            s3.upload_file(path, bucket, key)
    
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
        upload_folder_to_s3(out, S3_BUCKET, S3_PREFIX)
        nettoyer_data(DATA_DIR)
        print("✅ Terminé avec succès.")
    else:
        print("⚠️ Aucune partie récupérée.")

if __name__ == "__main__":
    main()
# EXTENSION : le pipeline enrichi et l'envoi SSP Cloud non destructif sont
# disponibles en lançant séparément : python Pipeline_ouvertures.py --upload
# L'envoi historique respecte aussi la configuration, sans suppression ni ACL publique.

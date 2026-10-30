"""Stockage versionné S3/MinIO sans suppression de l'existant, sans ACL publiques."""
import os
from pathlib import Path
import boto3
from botocore.config import Config
import config_projet as cfg
from config_projet import S3_BUCKET, S3_PREFIX

def client():
    endpoint=os.getenv('AWS_S3_ENDPOINT','minio.lab.sspcloud.fr')
    if not endpoint.startswith('http'):endpoint='https://'+endpoint
    return boto3.client('s3',endpoint_url=endpoint,region_name=os.getenv('AWS_DEFAULT_REGION','us-east-1'),config=Config(signature_version='s3v4'))

def upload_outputs():
    if cfg.RUN_DIR is None: raise ValueError('Créer ou sélectionner une expérience avant envoi')
    s3=client(); count=0
    for root in (cfg.DATA_DIR,cfg.RESULTS_DIR):
        for p in root.rglob('*'):
            if p.is_file() and not p.name.startswith('.'):
                key=f'{S3_PREFIX}/{cfg.RUN_DIR.name}/{root.name}/{p.relative_to(root).as_posix()}'
                s3.upload_file(str(p),S3_BUCKET,key); count+=1
                print('s3://'+S3_BUCKET+'/'+key)
    print('Objets envoyés:',count)

def download_file(name='games_clean.parquet', folder='Data', run_id=None):
    if cfg.RUN_DIR is None or not run_id:
        raise ValueError('Créer une expérience locale et préciser le run_id distant')
    if folder not in ('Data', 'Resultats') or Path(name).name != name or Path(run_id).name != run_id:
        raise ValueError('Nom de fichier, dossier ou identifiant invalide')
    dest = (cfg.DATA_DIR if folder == 'Data' else cfg.RESULTS_DIR) / name
    if dest.exists(): raise FileExistsError(dest)
    client().download_file(S3_BUCKET, f'{S3_PREFIX}/{run_id}/{folder}/{name}', str(dest))
    return dest
if __name__=='__main__': upload_outputs()

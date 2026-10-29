"""Stockage versionné S3/MinIO sans suppression de l'existant, sans ACL publiques."""
import os
from pathlib import Path
import boto3
from botocore.config import Config
from config_projet import DATA_DIR,RESULTS_DIR,S3_BUCKET,S3_PREFIX

def client():
    endpoint=os.getenv('AWS_S3_ENDPOINT','minio.lab.sspcloud.fr')
    if not endpoint.startswith('http'):endpoint='https://'+endpoint
    return boto3.client('s3',endpoint_url=endpoint,region_name=os.getenv('AWS_DEFAULT_REGION','us-east-1'),config=Config(signature_version='s3v4'))

def upload_outputs():
    s3=client(); count=0
    for root in (DATA_DIR,RESULTS_DIR):
        for p in root.rglob('*'):
            if p.is_file() and not p.name.startswith('.'):
                key=f'{S3_PREFIX}/{root.name}/{p.relative_to(root).as_posix()}'
                s3.upload_file(str(p),S3_BUCKET,key); count+=1
                print('s3://'+S3_BUCKET+'/'+key)
    print('Objets envoyés:',count)

def download_file(name='games_clean.parquet',folder='Data'):
    dest=(DATA_DIR if folder=='Data' else RESULTS_DIR)/name
    client().download_file(S3_BUCKET,f'{S3_PREFIX}/{folder}/{name}',str(dest))
    return dest
if __name__=='__main__': upload_outputs()

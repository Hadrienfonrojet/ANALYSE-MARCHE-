"""Conserver les données locales et S3 sous un identifiant de collecte unique."""

import os
from pathlib import Path
import boto3
import config_projet as cfg


## Partie 1 - Le client lit les identifiants dans l’environnement privé


def client():
    endpoint = os.getenv("AWS_S3_ENDPOINT", "minio.lab.sspcloud.fr")
    if not endpoint.startswith(("https://", "http://")):
        endpoint = "https://" + endpoint
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
    )


## Partie 2 - Envoyer une NOUVELLE collecte sans effacer les anciennes


def upload_folder_to_s3(local_folder, bucket=None, prefix=None, s3_client=None):
    """Un seul envoi par identifiant ; un marqueur distant empêche les réutilisations.

    Un échec d’envoi laisse tous les fichiers locaux intacts. Pas d’ACL publique,
    pas de delete_object, pas de synchronisation qui supprimerait l’existant.
    """
    root = Path(local_folder)
    if not root.is_dir():
        raise ValueError("Dossier de collecte absent")
    bucket = bucket or cfg.S3_BUCKET
    prefix = (prefix or cfg.S3_PREFIX).strip("/")
    base = f"{prefix}/{root.name}"
    s3 = s3_client if s3_client is not None else client()
    ## IfNoneMatch refuse de réserver un identifiant déjà utilisé dans ce bucket.
    s3.put_object(
        Bucket=bucket,
        Key=base + "/_collecte_reservee.json",
        Body=b'{"reserved":true}',
        ContentType="application/json",
        IfNoneMatch="*",
    )
    count = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(root)
        if any(part.startswith(".") or part == "__pycache__" for part in rel.parts):
            continue  ## Aucun .env ou fichier caché transmis.
        s3.upload_file(str(path), bucket, base + "/" + rel.as_posix())
        count += 1
    location = f"s3://{bucket}/{base}"
    print(
        f"{count} fichiers conservés dans {location}. Sources locales conservées : {root}"
    )
    return location

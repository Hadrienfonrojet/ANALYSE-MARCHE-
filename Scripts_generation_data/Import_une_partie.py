"""Importer les parties, au point de vue des joueurs du panel.

Ce fichier reprend les fonctions historiques d'import et contient leur déroulé.
La reconnaissance des ouvertures vient du champ opening renvoyé par Lichess.
Aucune liste manuelle d'ouvertures n'est chargée lors de l'import du module.

request_games et parse_game, dans Collecte_enrichie.py, gèrent respectivement
le transport HTTP et la conversion d'une réponse API en une ligne enrichie.
Les requêtes restent séquentielles pour ne pas multiplier les erreurs 429.
"""

import time
import warnings

import pandas as pd

import config_projet as cfg
from Scripts_generation_data.Collecte_enrichie import request_games, parse_game


## Partie 1 - Extraire les parties d'un joueur pour une cadence
# ------------------------------------------------------


def extract_games_user(username, format_partie, nb_parties, token=None, max_retries=4):
    """Retourner les parties valides comme DataFrame, sans écrire de fichier.

    parse_game vérifie que le joueur demandé figure bien parmi les deux joueurs.
    La couleur détermine comment traduire winner en Win, Loss ou Draw.
    Les Elo du joueur ET de l'adversaire sont conservés pour les analyses.
    Une erreur réseau persistante est signalée ; elle n'est pas masquée comme
    une absence de parties, qui aurait pu donner un panel incomplet silencieux.
    """
    username = str(username).strip().lower()
    if not username or nb_parties < 1:
        raise ValueError("Fournir un pseudo et un nombre de parties positif.")

    rows = []
    for game in request_games(username, format_partie, nb_parties, token, max_retries):
        row = parse_game(game, username, format_partie, username)
        if row is not None:
            rows.append(row)

    return pd.DataFrame(rows)


## Partie 2 - Assembler les joueurs et cadences du panel
# -----------------------------------------------


def import_games_enriched(users_df, token=None, n_per_format=60):
    """Collecter les cadences de cfg.FORMATS et conserver l'origine des joueurs.

    Entrée : DataFrame avec user_id ; seed_origin est facultatif.
    Sorties : games_<cadence>.parquet et games_enrichies_raw.parquet.
    Les doublons joueur/partie sont retirés. Deux joueurs peuvent cependant
    représenter la même partie : les deux points de vue ne sont pas indépendants.
    Les sauvegardes se font dans l'expérience courante, sans effacer les autres.
    """
    if n_per_format < 1:
        raise ValueError("Le nombre de parties doit être positif.")
    if "user_id" not in users_df:
        raise ValueError("La liste des joueurs doit contenir user_id.")

    users = users_df.dropna(subset=["user_id"]).copy()
    users["user_id"] = users["user_id"].astype(str).str.strip().str.lower()
    users = users[users["user_id"].ne("")].drop_duplicates("user_id")
    if users.empty:
        raise ValueError("Aucun joueur valide dans la liste.")

    all_frames = []

    for number, user in enumerate(users.to_dict("records"), 1):
        for cadence in cfg.FORMATS:
            frame = extract_games_user(user["user_id"], cadence, n_per_format, token)
            if not frame.empty:
                origin = user.get("seed_origin")
                frame["seed_origin"] = origin if pd.notna(origin) else user["user_id"]
                all_frames.append(frame)
            time.sleep(0.15)

        if number % 10 == 0:
            print("Joueurs traités :", number, "/", len(users))

    if not all_frames:
        raise RuntimeError(
            "Aucune partie récupérée : vérifier les pseudos et les filtres."
        )

    raw = pd.concat(
        all_frames, ignore_index=True
    )  ## Réunir les DataFrames joueur/cadence.
    raw = raw.drop_duplicates(["user_id", "game_id"])

    cfg.DATA_DIR.mkdir(parents=True, exist_ok=True)
    for cadence, frame in raw.groupby("format_partie"):
        frame.to_parquet(cfg.DATA_DIR / f"games_{cadence}.parquet", index=False)
    raw.to_parquet(cfg.DATA_DIR / "games_enrichies_raw.parquet", index=False)

    return raw


## Partie 3 - Import à partir d'une liste de joueurs déjà enregistrée
# ------------------------------------------------------------


def import_games_df(nb_parties_extraites, token=None, max_workers=1):
    """Lire la liste actuelle, ou la liste historique si elle est seule présente.

    max_workers reste accepté pour les anciens appels, mais le réseau reste
    séquentiel. Les sorties par cadence de l'ancien projet sont conservées.
    """
    if max_workers != 1:
        warnings.warn(
            "Collecte séquentielle : max_workers est conservé pour compatibilité.",
            stacklevel=2,
        )

    candidates = [
        cfg.DATA_DIR / "users_list_stratified.parquet",
        cfg.DATA_DIR / "users_list_global.parquet",
    ]
    source = next((path for path in candidates if path.is_file()), None)
    if source is None:
        raise FileNotFoundError(
            "Créer la liste des joueurs avant d’importer leurs parties."
        )

    users = pd.read_parquet(source)
    return import_games_enriched(users, token, nb_parties_extraites)




# Scripts_generation_data/Import_une_partie.py
import requests
import json
import time
import pandas as pd
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import random

# --- CONFIGURATION ---
# On analyse ces 4 cadences pour les joueurs trouvés
type_parties = ["bullet", "blitz", "rapid", "classical"]

DATA_DIR = os.path.join(os.path.dirname(__file__), "../Data")
os.makedirs(DATA_DIR, exist_ok=True)

# --- CHARGEMENT DES OUVERTURES ---
openings_file = os.path.join(DATA_DIR, "openings.parquet")
openings_dict = {}

if os.path.exists(openings_file):
    try:
        print("📚 Chargement des ouvertures...")
        df_openings = pd.read_parquet(openings_file)
        for _, row in df_openings.iterrows():
            moves_val = row["moves"]
            if hasattr(moves_val, "tolist"): moves_val = moves_val.tolist()
            if isinstance(moves_val, (list, tuple)):
                openings_dict[tuple(moves_val)] = (row["eco"], row["name"])
    except Exception:
        print("⚠️ Erreur lecture ouvertures.")

def identify_opening_fast(moves_list):
    if not moves_list or not openings_dict: return (None, None)
    limit = min(len(moves_list), 20)
    for length in range(limit, 0, -1):
        moves_slice = tuple(moves_list[:length])
        if moves_slice in openings_dict: return openings_dict[moves_slice]
    return (None, None)

def extract_games_user(username, format_partie, nb_parties, token, max_retries=3):
    time.sleep(1.0) # Pause anti-429
    url = f"https://lichess.org/api/games/user/{username}"
    params = {"max": nb_parties, "rated": "true", "perfType": format_partie, "opening": "true"}
    headers = {"Accept": "application/x-ndjson", "Authorization": f"Bearer {token}"}

    retries = 0
    while retries < max_retries:
        try:
            r = requests.get(url, params=params, headers=headers)
            if r.status_code == 200: break
            elif r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 3))
                print(f"⏳ 429 sur {username}. Pause {wait}s...")
                time.sleep(wait)
                retries += 1
            else: return pd.DataFrame()
        except:
            time.sleep(5)
            retries += 1

    if not r or r.status_code != 200: return pd.DataFrame()

    rows = []
    for line in r.iter_lines():
        if not line: continue
        try:
            game = json.loads(line)
            players = game.get("players", {})
            if "white" not in players or "black" not in players: continue
            
            white_id = players["white"].get("user", {}).get("id", "").lower()
            if white_id == username.lower(): user_color = "white"
            else: user_color = "black"
            
            my_data = players[user_color]
            winner = game.get("winner")
            result = "Win" if winner == user_color else ("Draw" if not winner else "Loss")
            
            moves = game.get("moves", "").split()
            eco, name = identify_opening_fast(moves)
            
            rows.append({
                "user_id": username,
                "game_id": game.get("id"),
                "format_partie": format_partie,
                "timestamp_ms": game.get("createdAt"),
                "result": result,
                "eco": eco,
                "opening_name": name,
                "rating": my_data.get("rating"),
                "rating_diff": my_data.get("ratingDiff"),
                "color": user_color
            })
        except: continue
    return pd.DataFrame(rows)

def import_games_df(nb_parties_extraites, token, max_workers=1):
    # 1. On charge la liste issue du Random Walk
    users_file = os.path.join(DATA_DIR, "users_list_global.parquet")
    if not os.path.exists(users_file):
        print("❌ users_list_global.parquet introuvable.")
        return pd.DataFrame()

    df_users = pd.read_parquet(users_file)
    users_list = df_users["user_id"].unique().tolist()
    print(f"ℹ️  Téléchargement pour {len(users_list)} joueurs (Random Walk)...")

    all_dfs = []

    # 2. On télécharge les parties (tous formats) pour ces joueurs
    for format_partie in type_parties:
        print(f"\n🎮 Format : {format_partie.upper()}")
        dfs_fmt = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_user = {executor.submit(extract_games_user, user, format_partie, nb_parties_extraites, token): user for user in users_list}
            
            count = 0
            for future in as_completed(future_to_user):
                res = future.result()
                if not res.empty: dfs_fmt.append(res)
                count += 1
                if count % 10 == 0: print(f"   ... {count}/{len(users_list)}", end="\r")

        if dfs_fmt:
            df_concat = pd.concat(dfs_fmt, ignore_index=True)
            output_file = os.path.join(DATA_DIR, f"games_{format_partie}.parquet")
            df_concat.to_parquet(output_file, index=False)
            print(f"\n✅ {len(df_concat)} parties sauvegardées.")
            all_dfs.append(df_concat)

    if all_dfs: return pd.concat(all_dfs, ignore_index=True)
    return pd.DataFrame()

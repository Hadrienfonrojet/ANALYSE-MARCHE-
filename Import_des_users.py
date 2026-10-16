import requests
import pandas as pd
import time
import os
import random
import json

# Répertoire des données
DATA_DIR = os.path.join(os.path.dirname(__file__), "../Data")
os.makedirs(DATA_DIR, exist_ok=True)

def get_recent_opponents(username, token, nb_games_to_check=10):
    """
    Récupère les derniers adversaires d'un joueur.
    """
    url = f"https://lichess.org/api/games/user/{username}"
    params = {"max": nb_games_to_check, "lite": "true"} 
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/x-ndjson"}

    opponents = []
    
    try:
        r = requests.get(url, params=params, headers=headers)
        
        if r.status_code == 429:
            print("⏳ 429 (Discovery) - Pause 3s...")
            time.sleep(3)
            return []
            
        if r.status_code != 200:
            return []

        for line in r.iter_lines():
            if not line: continue
            try:
                game = json.loads(line)
                players = game.get("players", {})
                
                for color in ["white", "black"]:
                    if color in players and "user" in players[color]:
                        p_id = players[color]["user"]["id"]
                        # On ne s'ajoute pas soi-même comme adversaire
                        if p_id.lower() != username.lower():
                            opponents.append(p_id)

            except Exception:
                continue

    except Exception as e:
        print(f"Erreur sur {username}: {e}")
        return []

    # SÉCURITÉ 1 : On nettoie les doublons au niveau de la requête API
    return list(set(opponents))

def discover_users_random_walk(seed_user, target_count, token, branching_factor=5):
    """
    Marche aléatoire accélérée avec garantie d'unicité.
    """
    print(f"--- Démarrage Random Walk (Graine : {seed_user}, Vitesse x{branching_factor}) ---")
    
    # 'collected_users' est un SET (Ensemble) : Il interdit physiquement les doublons
    collected_users = set()
    collected_users.add(seed_user.lower())
    
    final_list = [{"user_id": seed_user.lower()}]
    current_user = seed_user.lower()
    
    attempts = 0
    max_attempts = target_count * 3 

    while len(final_list) < target_count and attempts < max_attempts:
        attempts += 1
        
        # 1. On cherche les adversaires
        opponents = get_recent_opponents(current_user, token)
        
        # ### SÉCURITÉ ANTI-DOUBLON MAJEURE ###
        # On ne garde QUE ceux qui ne sont PAS dans 'collected_users'
        new_candidates = [opp for opp in opponents if opp.lower() not in collected_users]
        
        if new_candidates:
            # On en prend jusqu'à 'branching_factor' (ex: 5)
            nb_to_take = min(len(new_candidates), branching_factor)
            
            # random.sample garantit qu'on ne prend pas 2 fois le même dans le lot
            batch = random.sample(new_candidates, nb_to_take)
            
            # Ajout à la liste officielle
            for user in batch:
                user_clean = user.lower()
                
                # Double vérification (paranoïaque mais sûre)
                if user_clean not in collected_users:
                    collected_users.add(user_clean)
                    final_list.append({"user_id": user_clean})
            
            print(f"⚡ Ajout de {len(batch)} joueurs via {current_user} | Total : {len(final_list)}/{target_count}")

            # REBOND : On continue la marche depuis l'un des nouveaux trouvés
            current_user = random.choice(batch).lower()
            
            time.sleep(0.5)
        else:
            # Impasse : Tous les adversaires de ce joueur sont DÉJÀ dans notre liste
            print(f"   ⚠️ Impasse sur {current_user} (Adversaires déjà connus). Rebond aléatoire.")
            
            # On pioche quelqu'un d'autre dans la liste existante pour relancer la machine
            # (On ne l'ajoute pas, on s'en sert juste de tremplin)
            pool = list(collected_users - {current_user})
            if pool:
                current_user = random.choice(pool)
            else:
                break
            time.sleep(1)

    # Sauvegarde finale
    df_global = pd.DataFrame(final_list)
    
    # Si on a dépassé légèrement à cause du dernier batch, on coupe proprement
    if len(df_global) > target_count:
        df_global = df_global.iloc[:target_count]
        
    output_path = os.path.join(DATA_DIR, "users_list_global.parquet")
    df_global.to_parquet(output_path, index=False)
    
    print(f"\n🌍 TERMINÉ : {len(df_global)} joueurs uniques trouvés.")
    print(f"📁 Sauvegardé dans : {output_path}")
    
    return df_global
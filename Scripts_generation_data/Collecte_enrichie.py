"""Complète l'import existant par un panel multi-graines, avec variables parties/adversaires."""
import json, time, random
import pandas as pd
import requests
from config_projet import DATA_DIR, FORMATS

def request_games(username, fmt, n, token, retries=4):
    headers={'Accept':'application/x-ndjson'}
    if token: headers['Authorization']='Bearer '+token
    seen = set()
    for retry in range(retries):
        try:
            r=requests.get('https://lichess.org/api/games/user/'+username,
                params={'max':n,'rated':'true','perfType':fmt,'opening':'true','moves':'true','sort':'dateAsc','variant':'standard','finished':'true'},
                headers=headers,stream=True,timeout=(15,120))
            if r.status_code==429:
                r.close(); time.sleep(max(60,int(r.headers.get('Retry-After','60')))); continue
            r.raise_for_status()
            for line in r.iter_lines():
                if line:
                    game = json.loads(line)
                    if game.get('id') not in seen:
                        seen.add(game.get('id'))
                        yield game
            r.close(); return
        except requests.RequestException as exc:
            if retry == retries - 1:
                raise RuntimeError(f'Collecte Lichess échouée pour {username} ({fmt})') from exc
            time.sleep(2**retry)
    raise RuntimeError(f'Limite API persistante pour {username} ({fmt})')

def discover_stratified(seeds, token, target_per_seed=30, neighbors_per_user=10, seed=42):
    rng=random.Random(seed); records=[]; visited=set()
    for seed_user in seeds:
        queue=[(seed_user.lower(), 0)]; count=0
        while queue and count<target_per_seed:
            name, depth=queue.pop(0)
            if name in visited: continue
            visited.add(name); count+=1
            records.append({'user_id':name,'seed_origin':seed_user,'discovery_depth':depth})
            games=list(request_games(name,'blitz',neighbors_per_user,token))
            adversaries=[]
            for g in games:
                for col in ('white','black'):
                    ident=g.get('players',{}).get(col,{}).get('user',{}).get('id')
                    if ident and ident.lower()!=name: adversaries.append(ident.lower())
            rng.shuffle(adversaries)
            queue.extend([(a, depth + 1) for a in dict.fromkeys(adversaries) if a not in visited])
            time.sleep(.15)
    if not records: raise ValueError('Aucun joueur configuré')
    df=pd.DataFrame(records).drop_duplicates('user_id')
    df.to_parquet(DATA_DIR/'users_list_stratified.parquet',index=False)
    return df

def parse_game(g, user, fmt, origin):
    players=g.get('players',{})
    if not all(x in players for x in ('white','black')): return None
    wid=(players['white'].get('user') or {}).get('id','').lower()
    bid=(players['black'].get('user') or {}).get('id','').lower()
    if user not in (wid,bid): return None
    col='white' if user==wid else 'black'; opp='black' if col=='white' else 'white'
    winner=g.get('winner'); status=g.get('status','')
    if status in ('created','started','aborted','noStart','unknownFinish'): return None
    result='Draw' if not winner else 'Win' if winner==col else 'Loss'
    me=players[col]; other=players[opp]; opening=g.get('opening') or {}
    rating=me.get('rating'); opp_rating=other.get('rating')
    return {'game_id':g.get('id'),'user_id':user,'seed_origin':origin,'format_partie':fmt,
      'timestamp_ms':g.get('createdAt'),'last_move_ms':g.get('lastMoveAt'),
      'result':result,'win':int(result=='Win'),'score':.5 if result=='Draw' else int(result=='Win'),
      'is_draw':int(result=='Draw'),'color':col,'is_white':int(col=='white'),
      'rating':rating,'opponent_rating':opp_rating,
      'rating_diff_opponent':(rating-opp_rating) if isinstance(rating,(int,float)) and isinstance(opp_rating,(int,float)) else None,
      'rating_diff':me.get('ratingDiff'),'opponent_id':(other.get('user') or {}).get('id'),
      'eco':opening.get('eco'),'opening_name':opening.get('name'),
      'opening_ply':opening.get('ply'),'moves':g.get('moves',''),
      'status':status,'rated':g.get('rated'), 'variant':(g.get('variant') or ''),
      'speed':g.get('speed'), 'clock_initial':(g.get('clock') or {}).get('initial'),
      'clock_increment':(g.get('clock') or {}).get('increment')}

def collect_games(users, token, n_per_format=60):
    rows=[]
    for i,rec in enumerate(users.to_dict('records'),1):
        name=rec['user_id']; origin=rec['seed_origin']
        for fmt in FORMATS:
            for game in request_games(name,fmt,n_per_format,token):
                row=parse_game(game,name,fmt,origin)
                if row: rows.append(row)
            time.sleep(.15)
        if i%10==0: print('joueurs traités',i,'/',len(users))
    df=pd.DataFrame(rows)
    if df.empty: raise RuntimeError('Aucune partie récupérée : vérifier réseau et pseudos')
    df.drop_duplicates(['user_id','game_id'],inplace=True)
    df.to_parquet(DATA_DIR/'games_enrichies_raw.parquet',index=False)
    return df

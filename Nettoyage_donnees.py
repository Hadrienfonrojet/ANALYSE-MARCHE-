"""Nettoyage, identification famille, variables temporelles anti-fuite de données."""
import numpy as np
import pandas as pd
import config_projet as cfg

def prepare(raw, openings=None):
    if raw.empty: raise ValueError('Aucune partie à nettoyer')
    df=raw.copy()
    df['user_id']=df['user_id'].astype(str).str.lower()
    df=df.dropna(subset=['game_id','user_id','timestamp_ms']).drop_duplicates(['user_id','game_id'])
    df['timestamp']=pd.to_datetime(df['timestamp_ms'],unit='ms',utc=True,errors='coerce')
    df=df.dropna(subset=['timestamp']).sort_values(['user_id','timestamp','game_id']).reset_index(drop=True)
    for c in ['rating','opponent_rating','rating_diff_opponent']:
        df[c]=pd.to_numeric(df[c],errors='coerce')
    df=df[df['result'].isin(['Win','Loss','Draw']) & df['color'].isin(['white','black'])].copy()
    df['win']=(df['result']=='Win').astype(int)
    df['score']=df['result'].map({'Win':1.,'Draw':.5,'Loss':0.})
    df['is_draw']=(df['result']=='Draw').astype(int)
    df['is_white']=(df['color']=='white').astype(int)
    df['elo_diff']=df['rating']-df['opponent_rating']
    df['expected_score']=1/(1+np.power(10,-df['elo_diff']/400))
    df['eco']=df['eco'].fillna('UNKNOWN')
    df['opening_name']=df['opening_name'].fillna('Inconnue')
    if openings is not None and not openings.empty:
        mapping=openings[['eco','name','family']].drop_duplicates(['eco','name'])
        df=df.merge(mapping.rename(columns={'name':'opening_name','family':'family_reference'}),
            on=['eco','opening_name'],how='left',validate='many_to_one')
    if 'family_reference' not in df: df['family_reference']=np.nan
    df['opening_family']=df['family_reference'].fillna(df['opening_name'].str.split(':').str[0]).fillna('Inconnue')
    df['eco_group']=df['eco'].str[0]
    df['elo_band']=pd.cut(df['rating'],bins=[0,1000,1200,1400,1600,1800,2000,2200,2500,4000],labels=['0-1000','1000-1200','1200-1400','1400-1600','1600-1800','1800-2000','2000-2200','2200-2500','2500-4000'],include_lowest=True)
    # L'ouverture des noirs et des blancs dépend conjointement des deux joueurs.
    for keys in [['user_id','color'],['user_id','color','opening_family']]:
        label='color' if len(keys)==2 else 'opening'
        df['previous_'+label+'_time']=df.groupby(keys,observed=True)['timestamp'].shift(1)
    df['experience_opening_prior']=df.groupby(['user_id','color','opening_family'],observed=True).cumcount()
    df['experience_log']=np.log1p(df['experience_opening_prior'])
    from analyses.Tests_repetition import add_transitions
    df = add_transitions(df)
    df['gap_minutes']=df.groupby('user_id')['timestamp'].diff().dt.total_seconds()/60
    df['new_session']=(df['gap_minutes'].isna() | (df['gap_minutes']>30)).astype(int)
    df['session_num']=df.groupby('user_id')['new_session'].cumsum()
    df['session_id']=df['user_id']+'_'+df['session_num'].astype(str)
    df['game_in_session']=df.groupby('session_id').cumcount()+1
    df['game_index']=df.groupby('user_id').cumcount()+1
    df.to_parquet(cfg.DATA_DIR/'games_clean.parquet',index=False)
    df.groupby(['user_id','opening_family','color'],observed=True).agg(n=('win','size'),score_rate=('score','mean')).reset_index().to_parquet(cfg.DATA_DIR/'players_openings.parquet',index=False)
    return df

if __name__=='__main__':
    raw=pd.read_parquet(cfg.DATA_DIR/'games_enrichies_raw.parquet')
    p=cfg.DATA_DIR/'openings_complet.parquet'
    print('lignes nettoyées',len(prepare(raw,pd.read_parquet(p) if p.exists() else None)))

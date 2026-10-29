"""Complément non destructif: dictionnaire complet Lichess, sans remplacer les 50 entrées historiques."""
from pathlib import Path
import pandas as pd
import requests
from config_projet import DATA_DIR
URL = 'https://raw.githubusercontent.com/lichess-org/chess-openings/master/'
def build_openings():
    dfs=[]
    for letter in 'abcde':
        r=requests.get(URL+letter+'.tsv', timeout=45); r.raise_for_status()
        from io import StringIO
        frame=pd.read_csv(StringIO(r.text),sep='\t',dtype=str)
        frame['source_file']=letter+'.tsv'; dfs.append(frame)
    df=pd.concat(dfs,ignore_index=True).drop_duplicates(subset=['eco','name','pgn'])
    df['family']=df['name'].str.split(':').str[0]
    df['eco_group']=df['eco'].str[0]
    df.to_parquet(DATA_DIR/'openings_complet.parquet',index=False)
    print('Ouvertures source Lichess:',len(df)); return df
if __name__=='__main__': build_openings()

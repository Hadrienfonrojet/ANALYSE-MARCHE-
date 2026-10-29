"""Référentiel des ouvertures observées, fourni par l'API des parties Lichess."""
import pandas as pd
from config_projet import DATA_DIR

def build_openings(raw=None):
    if raw is None:
        raw = pd.read_parquet(DATA_DIR / 'games_enrichies_raw.parquet')
    reference = raw[['eco', 'opening_name']].dropna().drop_duplicates()
    reference = reference.rename(columns={'opening_name': 'name'})
    reference = reference[reference['name'].ne('')].copy()
    reference['family'] = reference['name'].str.split(':').str[0]
    reference['eco_group'] = reference['eco'].str[0]
    reference['source'] = 'lichess_api'
    reference = reference.sort_values(['eco', 'name']).reset_index(drop=True)
    reference.to_parquet(DATA_DIR / 'openings_complet.parquet', index=False)
    return reference

if __name__ == '__main__':
    print(build_openings())

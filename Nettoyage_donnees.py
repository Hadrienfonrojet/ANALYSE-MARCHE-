"""Nettoyer les parties et construire les variables utilisées dans les analyses.

Ce fichier n'efface aucune base. Il part d'une copie de la base brute et écrit
les sorties dans l'expérience courante. Lire les fonctions dans l'ordre :
identifiants, résultats et Elo, ouvertures, historique, puis sauvegarde.

La fonction publique prepare(raw, openings=None) conserve sa signature : le
master et les cellules du notebook existant peuvent continuer à l'appeler.
"""

import numpy as np
import pandas as pd

import config_projet as cfg
from analyses.Tests_repetition import add_transitions


# 1. Identifier une observation et établir l'ordre chronologique
# ---------------------------------------------------------------

def nettoyer_identifiants(raw):
    """Une observation est le point de vue d'un joueur dans une partie.

    On enlève les vrais identifiants absents AVANT de les convertir en texte.
    Puis on normalise les pseudos et on retire les doublons joueur/partie.
    Deux joueurs observés dans une même partie restent deux points de vue :
    ils ne sont pas deux parties indépendantes pour les tests statistiques.
    """
    required = {
        'game_id', 'user_id', 'timestamp_ms', 'result', 'color',
        'rating', 'opponent_rating', 'eco', 'opening_name', 'format_partie',
    }
    missing = required - set(raw.columns)
    if missing:
        raise ValueError('Colonnes requises absentes : ' + ', '.join(sorted(missing)))

    data = raw.dropna(subset=['game_id', 'user_id', 'timestamp_ms']).copy()
    data['user_id'] = data['user_id'].astype(str).str.strip().str.lower()
    data['game_id'] = data['game_id'].astype(str).str.strip()
    data = data[data['user_id'].ne('') & data['game_id'].ne('')]
    data = data.drop_duplicates(['user_id', 'game_id'])

    # Une valeur non numérique ou une date hors limites devient NaT, puis est exclue.
    numeric_time = pd.to_numeric(data['timestamp_ms'], errors='coerce')
    data['timestamp'] = pd.to_datetime(numeric_time, unit='ms', utc=True, errors='coerce')
    data = data.dropna(subset=['timestamp'])

    return data.sort_values(['user_id', 'timestamp', 'game_id']).reset_index(drop=True)


# 2. Résultats et Elo
# ---------------------

def ajouter_resultats_et_elo(data):
    """Calculer scores, couleurs et écarts de niveau sans inventer les Elo absents.

    score : victoire=1, nulle=0,5, défaite=0.
    win : indicateur 0/1 ; sa moyenne est le taux de victoire.
    expected_score : repère descriptif issu de l'écart Elo, pas une garantie.
    Les tranches Elo ont des étiquettes texte pour rester exportables en Parquet.
    """
    data = data[
        data['result'].isin(['Win', 'Loss', 'Draw'])
        & data['color'].isin(['white', 'black'])
    ].copy()

    for column in ['rating', 'opponent_rating']:
        data[column] = pd.to_numeric(data[column], errors='coerce')

    data['win'] = data['result'].eq('Win').astype(int)
    data['score'] = data['result'].map({'Win': 1., 'Draw': .5, 'Loss': 0.})
    data['is_draw'] = data['result'].eq('Draw').astype(int)
    data['is_white'] = data['color'].eq('white').astype(int)
    data['elo_diff'] = data['rating'] - data['opponent_rating']
    data['rating_diff_opponent'] = data['elo_diff']
    data['expected_score'] = 1 / (1 + np.power(10, -data['elo_diff'] / 400))

    data['elo_band'] = pd.cut(
        data['rating'],
        bins=[0, 1000, 1200, 1400, 1600, 1800, 2000, 2200, 2500, 4000],
        labels=['0-1000', '1000-1200', '1200-1400', '1400-1600', '1600-1800',
                '1800-2000', '2000-2200', '2200-2500', '2500-4000'],
        include_lowest=True,
    )

    return data


# 3. Rapprocher chaque partie du référentiel des ouvertures
# ----------------------------------------------------------

def associer_ouvertures(data, openings=None):
    """Conserver l'information API et regrouper les variantes par famille.

    Le couple code ECO/nom évite d'associer arbitrairement deux variantes.
    Une ouverture vide reste Inconnue. On ne classe pas automatiquement cette
    absence d'information comme une répétition ou comme un changement.
    """
    data = data.copy()
    for column, unknown in [('eco', 'UNKNOWN'), ('opening_name', 'Inconnue')]:
        data[column] = data[column].fillna('').astype(str).str.strip()
        data.loc[data[column].eq(''), column] = unknown

    # Si prepare reçoit déjà un panel préparé, ne pas conserver une ancienne jointure.
    data = data.drop(columns=['family_reference'], errors='ignore')

    if openings is not None and not openings.empty:
        required = {'eco', 'name', 'family'}
        if not required.issubset(openings.columns):
            raise ValueError('Le référentiel doit contenir eco, name et family.')

        mapping = openings[['eco', 'name', 'family']].dropna().copy()
        for column in ['eco', 'name', 'family']:
            mapping[column] = mapping[column].astype(str).str.strip()
        mapping = mapping.drop_duplicates()

        # Deux familles différentes pour le même couple signalent une incohérence.
        if mapping.duplicated(['eco', 'name']).any():
            raise ValueError('Plusieurs familles pour le même couple ECO/nom.')

        mapping = mapping.rename(columns={'name': 'opening_name', 'family': 'family_reference'})
        data = data.merge(mapping, on=['eco', 'opening_name'], how='left', validate='many_to_one')
    else:
        data['family_reference'] = np.nan

    fallback = data['opening_name'].str.split(':').str[0].str.strip()
    data['opening_family'] = data['family_reference'].fillna(fallback)
    data.loc[data['opening_family'].eq(''), 'opening_family'] = 'Inconnue'
    data['eco_group'] = data['eco'].str[0]

    return data


# 4. Construire uniquement des informations connues avant la partie
# ------------------------------------------------------------------

def construire_historiques(data):
    """Répétition, expérience observée et sessions sans utiliser le futur.

    add_transitions, dans analyses/Tests_repetition.py, compare les ouvertures
    toutes couleurs et à même couleur. shift(1) n'utilise que la partie précédente.
    L'expérience est le nombre de parties déjà observées dans la même famille
    avec la même couleur ; elle n'est pas l'expérience échiquéenne totale.
    Les sessions sont des groupes descriptifs séparés par plus de 30 minutes.
    """
    data = data.sort_values(['user_id', 'timestamp', 'game_id']).reset_index(drop=True)

    for keys, label in [
        (['user_id', 'color'], 'color'),
        (['user_id', 'color', 'opening_family'], 'opening'),
    ]:
        data['previous_' + label + '_time'] = data.groupby(keys, observed=True)['timestamp'].shift(1)

    data['experience_opening_prior'] = data.groupby(
        ['user_id', 'color', 'opening_family'], observed=True,
    ).cumcount().astype(float)
    data.loc[data['opening_family'].eq('Inconnue'), 'experience_opening_prior'] = np.nan
    data['experience_log'] = np.log1p(data['experience_opening_prior'])

    data = add_transitions(data)

    data['gap_minutes'] = data.groupby('user_id')['timestamp'].diff().dt.total_seconds() / 60
    data['new_session'] = (data['gap_minutes'].isna() | data['gap_minutes'].gt(30)).astype(int)
    data['session_num'] = data.groupby('user_id')['new_session'].cumsum()
    data['session_id'] = data['user_id'] + '_' + data['session_num'].astype(str)
    data['game_in_session'] = data.groupby('session_id').cumcount() + 1
    data['game_index'] = data.groupby('user_id').cumcount() + 1

    return data


# 5. Fonction utilisée par le master et le notebook
# --------------------------------------------------

def prepare(raw, openings=None, max_fullmoves=None):
    """Exécuter les étapes de préparation et enregistrer les deux tables utiles.

    La base brute d'entrée n'est pas modifiée. Les données invalides sont filtrées
    dans une copie ; aucun fichier existant d'une autre expérience n'est supprimé.
    """
    if raw.empty:
        raise ValueError('Aucune partie à nettoyer.')

    # Si un référentiel complet est fourni, les coups joués deviennent la source
    # de l'identification. Les étiquettes API sont conservées dans api_*.
    if openings is not None and 'position_key' in openings.columns:
        from Scripts_generation_data.Identification_ouvertures import identify_games
        raw = identify_games(raw, openings, max_fullmoves=max_fullmoves)
        raw.to_parquet(cfg.DATA_DIR / 'games_identifies.parquet', index=False)
        observed = raw.drop_duplicates('game_id').groupby(
            ['eco', 'opening_name', 'opening_identification_status'], dropna=False,
        ).size().reset_index(name='nombre_parties')
        observed.to_csv(cfg.DATA_DIR / 'openings_observees.csv', index=False)

    data = nettoyer_identifiants(raw)
    data = ajouter_resultats_et_elo(data)
    if data.empty:
        raise ValueError('Aucune partie valide après nettoyage.')

    data = associer_ouvertures(data, openings)
    data = construire_historiques(data)

    data.to_parquet(cfg.DATA_DIR / 'games_clean.parquet', index=False)
    summary = data.groupby(
        ['user_id', 'opening_family', 'color'], observed=True,
    ).agg(n=('win', 'size'), score_rate=('score', 'mean')).reset_index()
    summary.to_parquet(cfg.DATA_DIR / 'players_openings.parquet', index=False)

    return data


if __name__ == '__main__':
    raw = pd.read_parquet(cfg.DATA_DIR / 'games_enrichies_raw.parquet')
    reference = cfg.DATA_DIR / 'openings_complet.parquet'
    openings = pd.read_parquet(reference) if reference.exists() else None
    print('Lignes nettoyées :', len(prepare(raw, openings)))

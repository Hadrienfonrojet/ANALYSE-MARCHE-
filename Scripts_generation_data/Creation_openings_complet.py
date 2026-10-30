"""Créer le fichier des ouvertures observées à partir des réponses de l'API Lichess.

Rôle de ce fichier
-----------------
Lors de la collecte, l'API des parties renvoie un champ opening avec notamment
un code ECO et un nom. Collecte_enrichie.py place ces informations dans les
colonnes eco et opening_name de games_enrichies_raw.parquet.

Ce module transforme ces informations en une table de référence :
    eco, name, family, eco_group, source.

Il ne télécharge pas un dictionnaire externe et ne contient pas une liste
manuelle d'ouvertures. Son nom historique "complet" signifie ici qu'il reprend
les couples observés dans toute la collecte, pas toutes les ouvertures connues.

La fonction est appelée explicitement dans Master_file.py, après la collecte
et avant le nettoyage. Pour comprendre les termes, lire :
    docs/Introduction_aux_ouvertures.md
"""
import pandas as pd
import config_projet as cfg


def extraire_ouvertures(raw):
    """Garder une ligne par couple ECO/nom, sans inventer les valeurs absentes.

    Exemple de nom : "Sicilian Defense: ...".
    Une famille est le texte situé avant les deux-points, ici "Sicilian Defense".
    C'est une règle de regroupement du projet, et non une nouvelle classification
    indépendante de Lichess. Les variantes d'une même famille restent distinctes
    par leur nom complet dans le référentiel.
    """
    required = {'eco', 'opening_name'}
    missing = required - set(raw.columns)
    if missing:
        raise ValueError('Colonnes nécessaires aux ouvertures absentes : ' + ', '.join(sorted(missing)))
    reference = raw[['eco', 'opening_name']].dropna().copy()
    reference['eco'] = reference['eco'].astype(str).str.strip()
    reference['opening_name'] = reference['opening_name'].astype(str).str.strip()
    reference = reference[reference['eco'].ne('') & reference['opening_name'].ne('')]
    reference = reference.drop_duplicates(['eco', 'opening_name'])
    reference = reference.rename(columns={'opening_name': 'name'})
    reference['family'] = reference['name'].str.split(':').str[0].str.strip()
    reference['eco_group'] = reference['eco'].str[0]
    reference['source'] = 'lichess_api'
    return reference.sort_values(['eco', 'name']).reset_index(drop=True)


def sauvegarder_ouvertures(reference):
    """Écrire le référentiel dans le dossier de données de l'expérience courante.

    Parquet conserve les types pour Python. CSV permet aussi de lire la table
    facilement dans un tableur. Les deux fichiers représentent la même table.
    Relancer cette étape actualise ces sorties dans le run courant ; pour une
    autre collecte, créer une nouvelle expérience avec cfg.create_run().
    """
    cfg.DATA_DIR.mkdir(parents=True, exist_ok=True)
    reference.to_parquet(cfg.DATA_DIR / 'openings_complet.parquet', index=False)
    reference.to_csv(cfg.DATA_DIR / 'openings_complet.csv', index=False)


def build_openings(raw=None):
    """Extraire, sauvegarder et retourner le référentiel des ouvertures observées.

    Entrée explicite : DataFrame brut produit par collect_games.
    Sans entrée : lire games_enrichies_raw.parquet dans cfg.DATA_DIR.
    Sorties : openings_complet.parquet et openings_complet.csv.
    Une table vide indique qu'aucune ouverture n'a été reconnue dans la collecte.
    """
    if raw is None:
        source = cfg.DATA_DIR / 'games_enrichies_raw.parquet'
        if not source.is_file():
            raise FileNotFoundError('Collecter des parties ou fournir raw avant de construire le référentiel : ' + str(source))
        raw = pd.read_parquet(source)
    reference = extraire_ouvertures(raw)
    sauvegarder_ouvertures(reference)
    return reference


if __name__ == '__main__':
    print(build_openings())

"""Comprendre et lancer toutes les étapes du projet Lichess.

Ordre de lecture conseillé
-------------------------
1. docs/Introduction_aux_ouvertures.md : que représente une ouverture ?
2. Ce fichier : comment les étapes s'enchaînent et quels fichiers elles produisent.
3. Scripts_generation_data/Creation_openings_complet.py : référentiel des ouvertures.
4. Analyse_data.ipynb : hypothèses, calculs et interprétation des tests.

Exemple depuis la racine du dépôt :
    python Master_file.py --users-per-seed 1 --games-per-format 5

Le programme ne supprime aucune ancienne collecte. Chaque lancement crée un
nouveau dossier Collectes/<identifiant>/ avec ses données et ses résultats.
Les fonctions ci-dessous font réellement le travail d'orchestration ; elles
peuvent aussi être appelées séparément dans Python pour comprendre chaque étape.
"""
import argparse
import json
from pathlib import Path

import pandas as pd
import config_projet as cfg
from Scripts_generation_data.Collecte_enrichie import discover_stratified, collect_games
from Scripts_generation_data.Creation_openings_complet import build_openings
from Nettoyage_donnees import prepare
from Analyse_ouvertures import analyze


def verifier_parametres(users_per_seed, games_per_format, skip_collect, raw_file):
    """Vérifier les entrées avant de créer un dossier ou de lancer des requêtes.

    --skip-collect réutilise un fichier brut existant. Il ne relance pas l'API.
    Sans cette option, les pseudos viennent de config_projet.py et du .env privé.
    """
    if users_per_seed < 1 or games_per_format < 1:
        raise ValueError('Les nombres de joueurs et de parties doivent être positifs.')
    if skip_collect:
        if raw_file is None:
            raise ValueError('--skip-collect exige --raw-file chemin/vers/games_enrichies_raw.parquet')
        source = Path(raw_file).expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        return source
    if raw_file is not None:
        raise ValueError('Utiliser --skip-collect avec --raw-file pour réanalyser une base.')
    if not cfg.SEED_USERS or any(s.startswith('pseudo_') for s in cfg.SEED_USERS):
        raise ValueError('Renseigner de vrais pseudos dans LICHESS_SEEDS.')
    return None


def creer_experience(users_per_seed, games_per_format, source=None):
    """Créer un dossier neuf et enregistrer les paramètres non secrets.

    experience.json indique la taille de collecte demandée et l'origine des
    données. Les anciens dossiers restent présents. Aucun jeton n'y est écrit.
    """
    run_dir = cfg.create_run()
    manifest = run_dir / 'experience.json'
    parameters = json.loads(manifest.read_text(encoding='utf-8'))
    parameters.update(users_per_seed=users_per_seed, games_per_format=games_per_format,
                      mode='reanalyse' if source is not None else 'collecte',
                      source_file=str(source) if source is not None else None)
    manifest.write_text(json.dumps(parameters, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Dossier de cette expérience :', run_dir)
    return run_dir


def obtenir_parties(users_per_seed, games_per_format, source=None):
    """Collecter les parties via l'API, ou copier une ancienne base dans ce run.

    discover_stratified découvre les comptes à partir de leurs adversaires.
    collect_games demande les parties et leur champ opening à l'API Lichess.
    Sorties : users_list_stratified.parquet et games_enrichies_raw.parquet.
    La réanalyse ne modifie pas le fichier source.
    """
    if source is not None:
        print('1. Lecture de la base existante :', source)
        raw = pd.read_parquet(source)
        raw.to_parquet(cfg.DATA_DIR / 'games_enrichies_raw.parquet', index=False)
    else:
        print('1. Découverte des joueurs et collecte des parties Lichess')
        token = cfg.get_lichess_token()
        users = discover_stratified(cfg.SEED_USERS, token, users_per_seed)
        raw = collect_games(users, token, games_per_format)
    if raw.empty:
        raise ValueError('Aucune partie disponible ; impossible de construire les analyses.')
    print('Observations brutes :', len(raw))
    return raw


def creer_referentiel_ouvertures(raw):
    """Extraire les ouvertures reconnues par Lichess dans les parties collectées.

    Le fichier source de cette étape est :
    Scripts_generation_data/Creation_openings_complet.py.
    Sortie : Data/openings_complet.parquet dans le dossier de cette expérience.
    Ce référentiel contient les ouvertures observées, pas toutes les ouvertures
    possibles. Il remplace l'ancienne liste manuelle de 50 ouvertures.
    """
    print('2. Construction du référentiel des ouvertures observées')
    openings = build_openings(raw)
    print('Couples ECO et nom distincts :', len(openings))
    print('Fichier des ouvertures :', cfg.DATA_DIR / 'openings_complet.parquet')
    return openings


def nettoyer_et_construire_variables(raw, openings):
    """Préparer les variables utiles aux analyses, sans supprimer de fichiers.

    prepare nettoie les doublons joueur/partie, calcule le score, les tranches
    Elo et les historiques de répétition avec ou sans distinction de couleur.
    Sorties : Data/games_clean.parquet et Data/players_openings.parquet.
    """
    print('3. Nettoyage et construction des variables de répétition')
    clean = prepare(raw, openings)
    print('Observations analysables :', len(clean))
    return clean


def lancer_analyses(clean):
    """Produire les descriptifs, les χ², les tableaux détaillés et les graphiques.

    Le détail pédagogique des tests se trouve dans Analyse_data.ipynb.
    Les fonctions du χ² et des répétitions sont dans analyses/Tests_repetition.py.
    Sorties : Resultats/ et Resultats/repetition/ de cette expérience.
    Les analyses sont corrélationnelles ; les valeurs p restent exploratoires
    car des parties d'un même joueur ne sont pas indépendantes.
    """
    print('4. Analyses descriptives et tests statistiques')
    tests = analyze(clean)
    print('Tableaux et figures :', cfg.RESULTS_DIR)
    print('Tests de répétition :', cfg.RESULTS_DIR / 'repetition/tests_repetition_chi2.csv')
    return tests


def run_pipeline(users_per_seed=cfg.USERS_PER_SEED, games_per_format=cfg.GAMES_PER_FORMAT,
                 skip_collect=False, upload=False, raw_file=None):
    """Exécuter les étapes dans l'ordre et renvoyer les données et les tests.

    L'envoi SSP Cloud intervient uniquement si upload=True. Les identifiants
    sont lus dans l'environnement privé ; boto3 est installé par requirements.txt.
    """
    source = verifier_parametres(users_per_seed, games_per_format, skip_collect, raw_file)
    creer_experience(users_per_seed, games_per_format, source)
    raw = obtenir_parties(users_per_seed, games_per_format, source)
    openings = creer_referentiel_ouvertures(raw)
    clean = nettoyer_et_construire_variables(raw, openings)
    tests = lancer_analyses(clean)
    if upload:
        print('5. Envoi de cette expérience vers SSP Cloud')
        from Stockage_SSPCloud import upload_outputs
        upload_outputs()
    print('Expérience terminée. Anciennes collectes conservées.')
    return clean, tests


def main(argv=None):
    """Lire les options puis appeler le déroulé détaillé ci-dessus."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--users-per-seed', type=int, default=cfg.USERS_PER_SEED,
                        help='Nombre maximum de joueurs découverts par graine')
    parser.add_argument('--games-per-format', type=int, default=cfg.GAMES_PER_FORMAT,
                        help='Nombre maximum de parties par joueur et cadence')
    parser.add_argument('--skip-collect', action='store_true', help='Réutiliser une base brute existante')
    parser.add_argument('--raw-file', help='Chemin de la base brute à réanalyser')
    parser.add_argument('--upload', action='store_true', help='Envoyer les sorties vers SSP Cloud après analyse')
    return run_pipeline(**vars(parser.parse_args(argv)))


if __name__ == '__main__':
    main()

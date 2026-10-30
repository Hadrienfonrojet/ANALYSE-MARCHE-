# Analyse des ouvertures Lichess

[▶ Exécuter le notebook dans Colab](https://colab.research.google.com/github/Hadrienfonrojet/ANALYSE-MARCHE-/blob/main/Analyse_data.ipynb)

GitHub affiche le notebook ; utiliser Colab pour exécuter ses cellules. Les analyses sont dans les sections 6 à 9 : descriptif, χ²/V de Cramér, corrélations et graphiques. La première cellule installe toutes les dépendances, dont `boto3`.

Les ouvertures proviennent exclusivement du champ `opening` renvoyé par l'API des parties Lichess (`opening=true`). `Scripts_generation_data/Creation_openings_complet.py` est le seul constructeur du référentiel : il extrait les couples ECO/nom observés dans les parties collectées. Ce référentiel n'est pas un dictionnaire exhaustif.

## Installation

```sh
python -m pip install -r requirements.txt
cp .env.example .env
```

Configurer un ou plusieurs vrais pseudos séparés par des virgules dans `LICHESS_SEEDS`. Cinq graines sont recommandées pour le projet ENSAE ; une suffit pour un essai. Le jeton Lichess est optionnel pour les parties publiques. Les secrets SSP Cloud restent dans l'environnement ou le `.env` local.

## Exécution

Depuis la racine du projet :

```sh
python -m Pipeline_ouvertures --users-per-seed 1 --games-per-format 5
python -m Pipeline_ouvertures --skip-collect --raw-file Collectes/IDENTIFIANT/Data/games_enrichies_raw.parquet
python -m Pipeline_ouvertures --skip-collect --raw-file Collectes/IDENTIFIANT/Data/games_enrichies_raw.parquet --upload
```

`python Master_file.py` accepte les mêmes options. Importer les modules ne déclenche aucune collecte. Chaque étape est également une fonction réutilisable : `discover_stratified`, `collect_games`, `build_openings`, `prepare`, `analyze`, `upload_outputs` et `run_pipeline`.

Chaque lancement crée `Collectes/<horodatage_identifiant>/` avec `Data/` et `Resultats/`, sans effacer les expériences précédentes, même lors d’une réanalyse. Les anciens dossiers racine sont conservés. Le pipeline écrit dans ce nouveau dossier `Data/games_enrichies_raw.parquet`, `Data/openings_complet.parquet`, `Data/games_clean.parquet`, `Data/players_openings.parquet`, puis les tableaux et figures dans `Resultats/`. L'option `--skip-collect` exige un fichier brut existant et reconstruit le référentiel pour éviter un cache périmé. Les anciens constructeurs manuels ont été supprimés.

L'envoi SSP Cloud est uniquement explicite (`--upload`), vers `s3://hadrien2703/diffusion/projet_ouvertures/<identifiant_experience>/`. Il ne supprime pas d'objets et ne demande aucune ACL publique ; les clés existantes de même nom peuvent être remplacées.

## Interprétation

Les analyses décrivent des associations, jamais une causalité. Examiner les effectifs, le V de Cramér, les valeurs p corrigées et la validité des tests chi². Les parties d'un même joueur et les deux points de vue d'une même partie ne sont pas indépendants. Le panel découvert par adversaires n'est pas représentatif de tous les utilisateurs Lichess. Les régressions historiques restent des analyses complémentaires.

Le notebook `Analyse_data.ipynb` utilise les mêmes fonctions que la ligne de commande. Le PDF fourni dans l'archive est un document historique ; ce README décrit le fonctionnement actuel.

## Configuration commune

`config_projet.py` centralise les chemins, pseudos, cadences et tailles par défaut (`USERS_PER_SEED`, `GAMES_PER_FORMAT`). Le fichier `.env` privé peut les renseigner ; les options de commande et la cellule paramètres du notebook permettent de les ajuster pour une expérience. Le seul nom du jeton est `LICHESS_TOKEN` (remplacer l'ancien `jeton_api` dans votre `.env`). Aucun secret n'est inscrit dans les fichiers suivis. La chaîne exécute toujours `prepare()` avant l'analyse et avant l'envoi optionnel SSP Cloud.

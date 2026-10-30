# Configuration et collecte

Le mode d’emploi actuel est dans le [README principal](../README.md). Le [guide détaillé](Guide_analyse_Lichess.docx) décrit les variables, tests, hypothèses et fonctions.

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


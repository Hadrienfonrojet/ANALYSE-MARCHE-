# Analyse des ouvertures Lichess

[▶ Exécuter le notebook dans Colab](https://colab.research.google.com/github/Hadrienfonrojet/ANALYSE-MARCHE-/blob/main/Analyse_data.ipynb)

GitHub affiche le notebook ; utiliser Colab pour exécuter ses cellules. Le notebook comporte 60 cellules avec les fonctions essentielles visibles, les χ² détaillés et les analyses de répétition par couleur. Les sections 5 à 7 montrent le code du χ², les tests et leurs tableaux observés et attendus. La première cellule installe toutes les dépendances, dont `boto3`.

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

Le notebook `Analyse_data.ipynb` utilise les mêmes fonctions que la ligne de commande. Le guide actuel est dans `docs/Guide_analyse_Lichess.docx`. L'ancien PDF est conservé dans `docs/archives/`.

## Configuration commune

`config_projet.py` centralise les chemins, pseudos, cadences et tailles par défaut (`USERS_PER_SEED`, `GAMES_PER_FORMAT`). Le fichier `.env` privé peut les renseigner ; les options de commande et la cellule paramètres du notebook permettent de les ajuster pour une expérience. Le seul nom du jeton est `LICHESS_TOKEN` (remplacer l'ancien `jeton_api` dans votre `.env`). Aucun secret n'est inscrit dans les fichiers suivis. La chaîne exécute toujours `prepare()` avant l'analyse et avant l'envoi optionnel SSP Cloud.

## Retrouver les analyses et les tests

- `Analyse_data.ipynb` : notebook principal pour Colab, avec les explications à conserver ou à retirer.
- `analyses/Tests_repetition.py` : code de référence des transitions, du χ² de Pearson, du V de Cramér, de Fisher 2×2, de Holm et du bootstrap descriptif par joueur.
- `analyses/Analyse_ouvertures.py` : descriptifs et analyses générales ; le fichier de même nom à la racine reste compatible avec les anciens imports.
- `docs/` : guide et configuration ; `docs/archives/` : ancienne documentation.
- `tests/` : vérification des calculs, des définitions temporelles et du notebook hors ligne.

La répétition est comparée toutes couleurs confondues, à la précédente partie de même couleur, puis sur les parties observées consécutives de même couleur ou de couleurs différentes. Le programme teste également la répétition de la couleur elle-même. Chaque définition comporte la relation résultat précédent–répétition et répétition–résultat courant, avec stratifications par couleur, cadence et Elo.

Les exports se trouvent dans `Resultats/repetition/` : `tests_repetition_chi2.csv`, `taux_repetition.csv`, `bootstrap_joueurs.csv`, tableaux observés/attendus/résidus et leur index. `valid` ne valide que les effectifs attendus ; l'indépendance des parties n'est pas garantie. Les valeurs p restent exploratoires. Holm corrige la famille éligible des tests de répétition ; les tests généraux restent exportés séparément.

```sh
python -m unittest discover -s tests -v
```

Les données des tests sont simulées et ne constituent pas des résultats sur Lichess. Les tests réseau et l'accès SSP Cloud ne sont pas validés par ces tests hors ligne.

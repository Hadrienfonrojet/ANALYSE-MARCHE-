# Analyse des ouvertures Lichess

[▶ Exécuter le notebook dans Colab](https://colab.research.google.com/github/Hadrienfonrojet/ANALYSE-MARCHE-/blob/main/Analyse_data.ipynb)

GitHub affiche le notebook ; utiliser Colab pour exécuter ses cellules. Le notebook comporte 60 cellules avec les fonctions essentielles visibles, les χ² détaillés et les analyses de répétition par couleur. Les sections 5 à 7 montrent le code du χ², les tests et leurs tableaux observés et attendus. La première cellule installe toutes les dépendances, dont `boto3`.

Le grand référentiel officiel des ouvertures est rétabli : les cinq tables Lichess `a.tsv` à `e.tsv` sont réunies dans [References/openings_complet.csv](References/openings_complet.csv) et `.parquet` (**3865 lignes** pour la version livrée). Les sources et leur révision sont conservées dans `References/`.

Les ouvertures des parties sont identifiées **à partir des coups joués** : `python-chess` reconstruit les positions dans les 5 ou 10 premiers coups complets. La variante officielle la plus profonde atteinte est retenue ; la profondeur et les ambiguïtés sont enregistrées. Les noms API restent séparés dans `api_eco` et `api_opening_name`.

Lire [la méthode complète](docs/Introduction_aux_ouvertures.md) et [Identification_ouvertures.py](Scripts_generation_data/Identification_ouvertures.py).

## Retrouver le déroulé du projet

1. [Introduction aux ouvertures](docs/Introduction_aux_ouvertures.md) : notions, origine des informations, nom des fichiers et lien avec les répétitions.
2. [Master_file.py](Master_file.py) : déroulé complet, commenté étape par étape, avec les fonctions de validation, collecte, ouvertures, nettoyage et analyse.
3. [Création du référentiel des ouvertures](Scripts_generation_data/Creation_openings_complet.py) : téléchargement des cinq TSV officiels et sauvegarde du grand référentiel.
4. [Notebook d'analyse](Analyse_data.ipynb) : code des tests et interprétation.

Le script des ouvertures est présent sur GitHub. La grande table est incluse dans `References/` et copiée dans `Collectes/<identifiant>/Data/` à chaque exécution. La table des seules ouvertures rencontrées est distincte : `openings_observees.csv`.

## Installation

```sh
python -m pip install -r requirements.txt
cp .env.example .env
```

Configurer un ou plusieurs vrais pseudos séparés par des virgules dans `LICHESS_SEEDS`. Cinq graines sont recommandées pour le projet ENSAE ; une suffit pour un essai. Le jeton Lichess est optionnel pour les parties publiques. Les secrets SSP Cloud restent dans l'environnement ou le `.env` local.

## Exécution

Depuis la racine du projet :

```sh
python -m Pipeline_ouvertures --users-per-seed 1 --games-per-format 5 --opening-moves 10
python -m Pipeline_ouvertures --skip-collect --raw-file Collectes/IDENTIFIANT/Data/games_enrichies_raw.parquet
python -m Pipeline_ouvertures --skip-collect --raw-file Collectes/IDENTIFIANT/Data/games_enrichies_raw.parquet --upload
```

`python Master_file.py` accepte les mêmes options. Importer les modules ne déclenche aucune collecte. Chaque étape est également une fonction réutilisable : `discover_stratified`, `collect_games`, `build_openings`, `prepare`, `analyze`, `upload_outputs` et `run_pipeline`.

Chaque lancement crée `Collectes/<horodatage_identifiant>/` avec `Data/` et `Resultats/`, sans effacer les expériences précédentes, même lors d’une réanalyse. Les anciens dossiers racine sont conservés. Le pipeline écrit dans ce nouveau dossier `Data/games_enrichies_raw.parquet`, `Data/openings_complet.parquet`, `Data/games_clean.parquet`, `Data/players_openings.parquet`, puis les tableaux et figures dans `Resultats/`. L'option `--skip-collect` exige un fichier brut existant et charge le référentiel officiel figé, puis refait l’identification à partir des coups. Les anciens constructeurs manuels ont été supprimés.

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

## Lire les fichiers historiques d’import et de nettoyage

- [Import_des_users.py](Scripts_generation_data/Import_des_users.py) contient le parcours des adversaires, l’origine des joueurs, la profondeur de découverte et les fonctions historiques `discover_users_random_walk` et `discover_users_five_seeds`.
- [Import_une_partie.py](Scripts_generation_data/Import_une_partie.py) contient l’extraction par joueur, l’assemblage par cadence et la lecture des listes de comptes actuelles ou historiques.
- [Collecte_enrichie.py](Scripts_generation_data/Collecte_enrichie.py) contient les fonctions HTTP et le parsing de la réponse API ; ses anciens points d’entrée restent disponibles pour le notebook.
- [Nettoyage_donnees.py](Nettoyage_donnees.py) présente séparément les identifiants, les scores et Elo, la jointure des ouvertures, les historiques et les sauvegardes.

Les erreurs réseau persistantes sont signalées, les réponses sont fermées même après échec, les pseudos sont normalisés avant dédoublonnage et les identifiants absents sont retirés avant conversion en texte. Les ouvertures inconnues ne deviennent pas de fausses répétitions. Le détail des corrections est dans [Corrections des imports et du nettoyage](docs/Corrections_imports_et_nettoyage.md).

## Identification des ouvertures à cinq ou dix coups

Un coup complet = un coup blanc et un coup noir. `--opening-moves 5` inspecte jusqu'à 10 demi-coups et `--opening-moves 10` jusqu'à 20. Le notebook possède la variable `OPENING_MOVES`. La première étape construit le référentiel complet ; `prepare` utilise ensuite les coups `moves` pour identifier les parties avant de calculer les répétitions.

La méthode exige au moins cinq coups complets dans la partie par défaut. Une famille connue par une ligne plus courte peut être retenue, mais la profondeur exacte reste visible. Les coups après la fenêtre ne contribuent pas au nom. Les positions équivalentes permettent certaines transpositions ; les ambiguïtés de noms sont signalées. Sans coups disponibles ou en cas de coups invalides, aucune étiquette API n'est utilisée comme remplacement silencieux.

`Data/games_identifies.parquet` conserve l'identification locale et API. `Data/openings_observees.csv` recense les ouvertures rencontrées, tandis que `References/openings_complet.*` conserve toutes les lignes officielles. Pour changer de version, modifier `OPENINGS_REFERENCE_REV` puis reconstruire le cache avec `build_openings(refresh=True)`.

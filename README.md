# Ouvertures et victoires successives — projet original complété

> Après une victoire, gagner la partie suivante est-il plus fréquent lorsqu’on répète l’ouverture plutôt que lorsqu’on en change ?

Ce dépôt repart du dossier **Projet-info-2A-main**. Il conserve ses importeurs et son notebook détaillé, puis ajoute une partie VI sur les ouvertures. Les anciens blocs remplacés sont entourés de lignes `##` et entièrement commentés : ils restent lisibles, sans s’exécuter une deuxième fois.

[Ouvrir le notebook dans Colab](https://colab.research.google.com/github/Hadrienfonrojet/ANALYSE-MARCHE-/blob/main/Analyse_data.ipynb)

[L’ancien projet GitHub et son historique sont conservés dans un dépôt distinct](https://github.com/Hadrienfonrojet/ANALYSE-MARCHE-ARCHIVE-2026-11-03). L’archive est privée : il faut être connecté avec le compte autorisé. Une branche `archive/projet-avant-retour-original-2026-11-03` conserve aussi cet état.

## Lire et comprendre

1. [ANALYSE_DU_PROJET.md](ANALYSE_DU_PROJET.md) : ce qui change, les questions, les limites et le rôle des fichiers.
2. [Analyse_data.ipynb](Analyse_data.ipynb) : sections I–V initiales conservées, puis partie VI sur la répétition d’ouverture.
3. [Analyse_repetition_ouverture.py](Analyse_repetition_ouverture.py) : fonctions commentées pour préparer les transitions, décrire, tester et ajuster.
4. [Scripts_generation_data/Creation_Df_openings.py](Scripts_generation_data/Creation_Df_openings.py) : ancien référentiel désactivé, puis référentiel officiel et reconnaissance par position.

Le notebook contient **77 cellules**. Les commentaires historiques de résultats sont signalés et repliés : ce sont des textes de l’ancien rapport, pas des conclusions recalculées sur tes nouvelles données. Les sections II–V restent une comparaison Hot Hand ; la partie VI répond à la nouvelle question.

## Installation

```bash
python -m pip install -r requirements.txt
cp .env.example .env
```

`config_projet.py` et `.env.example` sont conservés de la version GitHub précédente. Le vrai `.env` reste privé, ignoré par Git. Ne jamais y recopier des secrets dans un fichier suivi. `boto3` est déjà dans requirements.txt ; le pipeline n’installe plus de bibliothèque automatiquement.

Paramètres de stockage conservés :

```text
S3_BUCKET=hadrien2703
S3_PREFIX=diffusion/projet_ouvertures
```

Les identifiants AWS restent dans l’environnement ou ton `.env` privé. Le nom habituel du token est `LICHESS_TOKEN` ; le Master accepte aussi l’ancien `jeton_api`.

## Collecter les parties de cinq comptes choisis

```bash
python Master_file.py --users pseudo_1 pseudo_2 pseudo_3 pseudo_4 pseudo_5 --upload
```

Remplacer les cinq exemples par tes vrais comptes ; aucun compte supplémentaire n’est découvert dans ce mode. Les importeurs contiennent ce même exemple dans un bloc entre guillemets, sans changement de leurs fonctions.

Sans `--users`, le Master utilise les graines `LICHESS_SEEDS` et la découverte d’adversaires originale. `USERS_PER_SEED` et `GAMES_PER_FORMAT` sont lus dans la configuration ; ce dernier paramètre est un maximum de parties **par joueur et par cadence**. Les fonctions originales de collecte ne sont pas réécrites : leurs limites réseau, d’échantillonnage et de continuité restent décrites dans ANALYSE_DU_PROJET.md.

L’importeur original ne garde pas les coups et l’Elo adverse : le Master complète donc les parties par IDs, par lots de 300 via l’API officielle. Cela ajoute une étape de téléchargement explicite, puis sauvegarde la base enrichie. L’ouverture API est gardée séparément ; la reconnaissance locale utilise réellement la fenêtre de coups choisie.

Chaque exécution crée :

```text
Collectes/<identifiant_unique>/
    experience.json
    Data/
        openings.parquet
        users_list_global.parquet
        games_<cadence>.parquet
        dfs_games_brut.parquet
        dfs_games_enrichi.parquet
        dfs_games.parquet
        games_clean.parquet
    Resultats/
        tests_repetition.csv
        taux_<cadre>.csv
        observe_<cadre>.csv
        attendu_<cadre>.csv
        transitions_<cadre>.parquet
        bootstrap_joueurs.csv
        regression_diagnostic.json
        regression_coefficients.csv
        statistiques_descriptives.csv
        descriptifs_ouvertures_couleur.csv
        qualite.json
        *.png
```

Les fichiers enrichis/users/cadences n’existent que si l’étape correspondante est exécutée. Tous les fichiers locaux restent conservés. Avec `--upload`, cette collecte est copiée sous `s3://hadrien2703/diffusion/projet_ouvertures/<identifiant_unique>/`, sans effacement et sans ACL publique. Un marqueur conditionnel refuse de réutiliser un identifiant déjà réservé. Si un envoi échoue, les données locales restent disponibles ; créer une nouvelle collecte pour un nouvel envoi.

## Réutiliser une base sans refaire la collecte

```bash
python Master_file.py --raw-file chemin/vers/dfs_games_enrichi.parquet
```

Pour compléter un ancien parquet depuis les IDs, avec un accès API explicite :

```bash
python Master_file.py --raw-file chemin/vers/ancien.parquet --enrich-api --upload
```

Sans coups, la reconnaissance locale du Master est indiquée inconnue ; sans Elo adverse, la régression peut être non estimable. Le code ne fabrique aucune de ces informations. Modifier `OPENING_MAX_FULLMOVES` dans ton `.env` privé pour choisir 5 ou 10 coups ; le minimum de disponibilité est 5 coups complets par défaut.

## Utiliser le notebook

**DEMO=True par défaut** : les données sont simulées, pour apprendre et vérifier le code sans S3 ni token. Elles ne permettent aucune conclusion réelle sur Lichess.

Pour tes données, dans I.2 :

```python
DEMO = False
LOCAL_FILE = "Collectes/TON_IDENTIFIANT/Data/dfs_games.parquet"
# ou, sans fichier local :
LOCAL_FILE = None
S3_RUN_ID = "TON_IDENTIFIANT"
```

Les variables AWS privées doivent être disponibles dans l’environnement Colab ou un `.env` local jamais publié. Sur Colab, la cellule d’installation récupère le dépôt ; redémarrer l’environnement pour charger une version plus récente plutôt que garder un ancien clone en mémoire.

En VI, `OPENING_MOVES=5` ou `10` choisit la fenêtre. Chaque exécution crée un nouveau dossier de résultats. L’envoi S3 du notebook est désactivé par défaut et demande `UPLOAD_S3=True`.

## Tests

```bash
python -m unittest discover -s tests -v
```

Tests hors réseau : référentiel, fenêtre 5/10, nulles, dernières parties, ouvertures inconnues, distinction même couleur, tableau χ² connu, Fisher, bootstrap, modèle groupé sur données simulées, protection des sauvegardes, envoi S3 simulé et Master sans collecte. Le notebook complet est également exécuté en DEMO lors de la vérification livrée.

Une collecte réelle et les permissions SSP Cloud ne sont pas validées par ces tests simulés. Les importeurs originaux conservés peuvent encore rencontrer leurs erreurs réseau connues : voir le document d’analyse.

## Sources

[Référentiel officiel CC0](https://github.com/lichess-org/chess-openings) · [Export par IDs](https://github.com/lichess-org/api/blob/master/doc/specs/tags/games/api-games-export-_ids.yaml) · [Consignes API](https://lichess.org/page/api-tips).

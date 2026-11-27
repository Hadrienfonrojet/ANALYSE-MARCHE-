# Le rôle des ouvertures aux échecs, inspiré du *Jeu de la dame*

[![Ouvrir dans Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Hadrienfonrojet/ANALYSE-MARCHE-/blob/main/QueensGambit.ipynb)

**Question de départ :** répéter une ouverture dépend-il de l’issue de la partie précédente ?

**Problématique :** comment les taux de victoire, de défaite et de nulle varient-ils selon l’ouverture, la couleur, la période et la répétition d’une même stratégie ?

Tout le projet se lit dans **`QueensGambit.ipynb`** : collecte, nettoyage, statistiques descriptives, tests du χ² avec correction de Holm et régressions (modèles linéaires de probabilité avec effet fixe joueur, logit).

## Données

* **13 727 parties classées** de **30 comptes Lichess**, du 25 novembre 2025 au 24 novembre 2026.
* Les comptes sont découverts par marche aléatoire à partir de trois graines (`macaquezizi`, `T34USSR`, `lucascrotti`), avec au plus 300 parties par compte et par cadence.
* La base brute est publiée dans `donnees/parties_1an.parquet` : le notebook la relit sans réinterroger Lichess.
* L’ouverture est identifiée à partir des coups et analysée au niveau de la **famille** (Sicilienne, Française…).

## Résultat principal

On répète sa famille d’ouverture dans 11,7 % des enchaînements après une victoire et dans 11,9 % après une nulle ou une défaite (χ², p = 0,65). Dans notre échantillon, les résultats ne suffisent pas à établir une association entre le fait de répéter une famille d’ouverture après une victoire et le résultat de la partie suivante. Les résultats dépendent surtout de l’écart d’Elo et, plus faiblement, de la couleur.

## Fichiers

Le [guide du code](#guide-du-code-et-des-paramètres) présente les fichiers et leurs fonctions par rôle.

## Prérequis

* Python 3.12
* Git pour cloner le dépôt
* Jupyter et `nbconvert` pour exécuter le notebook en ligne de commande, ou Colab dans le navigateur

## Installation

```bash
git clone https://github.com/Hadrienfonrojet/ANALYSE-MARCHE-.git
cd ANALYSE-MARCHE-
python -m pip install -r requirements.txt
```

## Utilisation

```bash
jupyter nbconvert --to notebook --execute --inplace QueensGambit.ipynb
```

Pour refaire une collecte, créer un fichier `.env` (jamais publié) avec son jeton Lichess, puis :

```bash
# .env : LICHESS_TOKEN=...  LICHESS_SEEDS=macaquezizi,T34USSR,lucascrotti
#        USERS_PER_SEED=10   GAMES_PER_FORMAT=300
python Master_file.py --collect --discover --since 2025-11-25 --until 2026-11-25 --debut 2026-05-01 --fin 2026-11-01 --upload
```

## Limites

L’échantillon est propre aux 30 comptes suivis et à leurs adversaires ; le plafond de 300 parties tronque l’historique des comptes les plus actifs ; les résultats sont des associations, car chaque joueur choisit lui-même son ouverture et sa cadence.

## Guide du code et des paramètres

Pour une nouvelle collecte, le Master appelle la découverte des comptes, puis l’import Lichess. Les parties passent ensuite par l’identification des ouvertures et le nettoyage. Le notebook peut partir directement de la base publiée, puis réutiliser les modules de nettoyage et d’analyse.

### Où modifier les réglages

* **Les comptes de départ**
  * **Où intervenir** — `--users` en ligne de commande ou `LICHESS_SEEDS` dans `.env`
  * **Qui utilise le réglage** — `Master_file.preparer_utilisateurs()`. Sans `--discover`, on collecte les comptes indiqués. Avec cette option, ils servent de départ à la marche aléatoire.

* **La taille de la collecte**
  * **Où intervenir** — `USERS_PER_SEED` (30 par défaut) et `GAMES_PER_FORMAT` (60 par défaut) dans `.env`
  * **Qui utilise le réglage** — `Master_file.py` transmet le premier à la découverte et le second à l’import. Le plafond de parties s’applique par compte et par cadence. L’exemple ci-dessus le fixe à 300 pour la collecte publiée.

* **Les cadences ou le tirage**
  * **Où intervenir** — `FORMATS` et `RANDOM_SEED` dans `config.py`
  * **Qui utilise le réglage** — `import_parties.import_games_df()` parcourt les cadences. Le Master transmet la graine à la marche aléatoire. Une même graine fixe les tirages pour un ensemble de candidats donné.

* **Les dates téléchargées**
  * **Où intervenir** — `--since` et `--until` dans la commande de collecte
  * **Qui utilise le réglage** — `Master_file.main()` convertit les dates UTC en millisecondes pour l’API. La borne de fin est exclue.

* **La période du sous-échantillon exporté**
  * **Où intervenir** — `DEBUT` et `FIN` en tête du notebook ou `--debut` et `--fin` en ligne de commande
  * **Qui utilise le réglage** — `analyse.filtrer_periode()` sélectionne les parties déjà disponibles, début inclus et fin exclue en UTC.

* **Le fichier analysé**
  * **Où intervenir** — `SOURCE`, `LOCAL_FILE` et `S3_RUN_ID` dans le notebook, ou `--raw-file` dans le Master
  * **Qui utilise le réglage** — Le notebook charge le fichier local ou la collecte S3 désignée. Le Master lit le CSV ou le Parquet donné.

* **La profondeur d’identification**
  * **Où intervenir** — `OPENING_MIN_FULLMOVES` et `OPENING_MAX_FULLMOVES` dans `.env` (5 et 10 par défaut)
  * **Qui utilise le réglage** — `import_ouvertures.identify_games()` applique ces bornes pour classer les parties.

* **La granularité des ouvertures**
  * **Où intervenir** — `NIVEAU_OUVERTURE=famille` ou `variante` dans `.env`
  * **Qui utilise le réglage** — `nettoyage.creer_variables()` choisit le niveau du libellé d’ouverture utilisé dans les analyses.

* **L’ouverture affichée et le seuil des tableaux**
  * **Où intervenir** — `OUVERTURE` et `MIN_PARTIES` en tête du notebook
  * **Qui utilise le réglage** — Les cellules descriptives s’en servent pour choisir l’ouverture détaillée et filtrer l’affichage selon le nombre d’observations.

* **Les trois régressions par résultat**
  * **Où intervenir** — `RUN_REGRESSIONS=true` ou `false` dans `.env`
  * **Qui utilise le réglage** — `Master_file.main()` transmet ce réglage à `analyse.analyser()`. Le notebook lit aussi ce réglage pour ces trois modèles. Ses régressions complémentaires ont leurs propres cellules.

* **L’accès à Lichess et la destination S3**
  * **Où intervenir** — `LICHESS_TOKEN` dans `.env`, puis `S3_BUCKET` et `S3_PREFIX` pour le stockage
  * **Qui utilise le réglage** — `config.get_lichess_token()` fournit le jeton à la collecte. `Stockage_SSPCloud.py` lit la destination lors d’un envoi avec `--upload`.

### [`config.py`](config.py) — Configuration et dossiers d’exécution

#### Jeton Lichess

* **`get_lichess_token()`**  
  Lit `LICHESS_TOKEN` ou l’ancien nom `jeton_api`. Le Master l’appelle lors d’une collecte API.

#### Dossiers d’exécution

* **`create_run()`**  
  Crée un dossier unique dans `Collectes/`, initialise `Data/` et `Resultats/`, puis écrit les réglages dans `experience.json`. Appelée à l’initialisation d’une exécution.

### [`import_utilisateurs.py`](import_utilisateurs.py) — Découverte des comptes

#### Lecture des adversaires

* **`get_recent_opponents(username, token=None, nb_games_to_check=10)`**  
  Récupère les adversaires distincts des dernières parties de `username` via `telecharger_parties()`. La marche aléatoire l’appelle à chaque étape.

#### Exploration du réseau

* **`discover_users_random_walk(seed_user, target_count, token=None, branching_factor=5, random_seed=73)`**  
  Explore le réseau depuis `seed_user`. `target_count` fixe le nombre visé, `branching_factor` limite le nombre de nouveaux comptes pris à chaque étape et `random_seed` fixe le tirage. Appelée par le Master avec `--discover`.

### [`import_parties.py`](import_parties.py) — Requêtes Lichess et table brute

#### Requête HTTP et cache

* **`telecharger_parties(username, token=None, params=None, session=None, max_retries=3)`**  
  Envoie une requête HTTP GET et décode le flux NDJSON en dictionnaires Python. `params` porte les filtres, `session` permet de fournir un client HTTP et `max_retries` fixe le nombre maximal de tentatives. Appelée par la découverte des adversaires et la collecte.

* **`lire_ou_telecharger(username, cadence, params, token=None, max_retries=3)`**  
  Réutilise une réponse locale si ses paramètres et son empreinte concordent, ou la télécharge et la conserve. Appelée par `extract_games_user()`.

#### Conversion et assemblage

* **`partie_vers_ligne(game, username, cadence)`**  
  Transforme un objet JSON `game` en observation du point de vue de `username`, avec notamment sa couleur, son adversaire et son résultat. Appelée pendant l’extraction d’un compte.

* **`extract_games_user(username, format_partie, nb_parties, token=None, max_retries=3, since=None, until=None)`**  
  Collecte un compte pour une cadence donnée. `nb_parties` plafonne l’export et `since`/`until` sont les bornes API en millisecondes. Appelée par `import_games_df()`.

* **`import_games_df(nb_parties_extraites, token=None, max_workers=1, since=None, until=None)`**  
  Parcourt les comptes sélectionnés et les cadences de `config.FORMATS`, puis concatène les tables. Le plafond s’applique à chaque couple compte–cadence. Le code exige `max_workers=1`. Appelée par le Master.

### [`import_ouvertures.py`](import_ouvertures.py) — Référentiel et identification

#### Clés de position et référentiel

* **`position_key(board)`**  
  Construit une clé à partir des pièces, du trait, des droits de roque et de la prise en passant légale. L’indexation et la reconnaissance utilisent la même clé.

* **`download_sources(source_dir=None)`**  
  Récupère les cinq TSV de la révision figée et les place dans `source_dir` ou le cache configuré. Appelée par `creer_openings()`.

* **`read_reference(source_dir)`**  
  Lit les cinq fichiers du dossier et assemble la table officielle des ouvertures. Appelée par `creer_openings()`.

#### Indexation et reconnaissance

* **`build_position_index(reference, max_fullmoves=10)`**  
  Indexe les positions des variantes officielles jusqu’à la profondeur choisie. Appelée par `identify_games()`.

* **`identify_opening(moves, index, max_fullmoves=10, min_fullmoves=5)`**  
  Rejoue les coups et retient la variante officielle la plus précise reconnue dans la fenêtre de profondeur. Appelée pour chaque partie par `identify_games()`.

* **`identify_games(raw, reference, max_fullmoves=None, min_fullmoves=None)`**  
  Ajoute les informations d’ouverture à la base brute `raw`. Les valeurs `None` utilisent la configuration. Appelée par `Master_file.identifier_parties()`.

#### Export du référentiel

* **`creer_openings(data_dir=None, source_dir=None)`**  
  Prépare et exporte `openings.parquet`. `source_dir` cible les TSV et `data_dir` la destination. Appelée par le Master et le notebook.

### [`nettoyage.py`](nettoyage.py) — Table d’analyse et chronologie

#### Normalisation

* **`convertir_dates(valeurs, millisecondes=False)`**  
  Convertit les dates ISO ou numériques en UTC. `millisecondes=True` indique que les timestamps numériques sont exprimés dans cette unité. Intervient pendant la préparation des dates.

* **`normaliser_identifiants(df)`**  
  Uniformise les identifiants sur la table de travail et compte les identifiants reconstruits. Appelée par `preparer_parties()`.

#### Sélection et variables

* **`selectionner_parties(df, bilan)`**  
  Sélectionne les lignes exploitables, complète le bilan et conserve les ruptures nécessaires à la chronologie. Appelée par `preparer_parties()`.

* **`creer_variables(df)`**  
  Construit les variables d’analyse comme les indicateurs de résultat, le score et l’écart Elo. Applique `NIVEAU_OUVERTURE`. Appelée par `preparer_parties()`.

#### Nettoyage complet et sauvegarde

* **`preparer_parties(frame)`**  
  Enchaîne les opérations et renvoie la table nettoyée et son bilan sans modifier la table source. Utilisée dans le notebook et l’analyse.

* **`clean_games(frame)`**  
  Renvoie uniquement la table nettoyée. Utilisée lorsque le bilan détaillé n’est pas nécessaire.

* **`sauvegarder_nettoyage(frame, destination)`**  
  Nettoie puis écrit un nouveau Parquet à `destination`. Le Master l’appelle pour conserver la base prête à analyser.

### [`Analyse_repetition_ouverture.py`](Analyse_repetition_ouverture.py) — Transitions et tests

#### Construction des transitions

* **`creer_transitions(frame, meme_couleur=False)`**  
  Associe chaque partie à la prochaine partie observée du même compte. Avec `meme_couleur=True`, cherche la prochaine partie de même couleur. Sert aux tests et aux régressions.

* **`preparer_cadres(frame)`**  
  Construit les trois cadres de comparaison à partir de `creer_transitions()` : immédiat, immédiat de même couleur et prochain de même couleur. Utilisée dans les tests du module `analyse.py`.

#### Tests et incertitude

* **`tester_table(frame, x="repeat_opening", y="win_next")`**  
  Croise les colonnes `x` et `y`, calcule les effectifs attendus et renvoie les résultats des tests avec les tableaux observé et attendu. Utilisée dans `analyse.tests_repetition()`.

* **`taux_apres_victoire(transitions)`**  
  Garde les transitions après victoire avec ouverture renseignée des deux côtés, puis compare les taux lorsqu’on répète ou change. Utilisée avant les tests sur la victoire suivante.

#### Lancement de l’analyse

* **`analyser(frame, output_dir, run_regression=True)`**  
  Délègue l’analyse à `analyse.analyser()`. `output_dir` fixe les exports et `run_regression` active les modèles.

### [`analyse.py`](analyse.py) — Statistiques, modèles et exports

#### Statistiques descriptives

* **`statistiques_ouvertures(parties)`**  
  Calcule les effectifs, taux et scores par ouverture connue, avec une lecture par partie et par joueur. Utilisée dans le notebook et le parcours descriptif.

* **`filtrer_periode(parties, debut, fin)`**  
  Extrait la fenêtre UTC demandée, début inclus et fin exclue. Appelée par `statistiques_temporelles()`.

* **`statistiques_temporelles(parties, debut, fin)`**  
  Renvoie les observations de la fenêtre et leurs taux mensuels pour les exports.

* **`series_resultats(parties)`**  
  Calcule les suites consécutives de victoires, défaites ou nulles avec la même ouverture, puis leurs maxima. Utilisée sur l’ensemble des observations et sur la fenêtre.

#### Préparation et estimation des modèles

* **`preparer_regressions(parties)`**  
  Construit les transitions immédiates et exprime l’écart Elo de la partie suivante par tranche de 100 points. Appelée par `regressions_lineaires()`.

* **`regressions_lineaires(parties)`**  
  Estime trois modèles sur la victoire, la défaite et la nulle de la partie suivante. Renvoie les diagnostics et les coefficients. Appelée par le parcours d’analyse.

#### Export des tableaux

* **`exporter_tableaux(output, parties, bilan, overview, intervalle, monthly, runs, maxima, window_maxima)`**  
  Écrit dans `output` la base, le bilan, les résultats par ouverture, la fenêtre et ses taux mensuels, les séries et leurs maxima. Appelée en fin d’analyse.

#### Comparaison des cadres

* **`tests_repetition(parties, output)`**  
  Compare les trois cadres de transition, applique la correction de Holm et écrit les résultats dans `output`. Renvoie aussi les tableaux de taux.

#### Graphiques et traçabilité

* **`tracer_resultats(overview, monthly, maxima, output)`**  
  Trace les résultats par ouverture et les maxima des séries dans `output`. Le graphique mensuel est généré uniquement si une table mensuelle non vide est fournie.

* **`ecrire_manifeste(frame, output, debut, fin)`**  
  Enregistre les dates, les versions et l’empreinte des données dans le dossier de résultats. Appelée en fin d’exécution.

* **`version(package)`**  
  Fonction locale à `ecrire_manifeste()`. Lit la version installée du paquet ou renvoie `absent`.

#### Lancement de l’analyse

* **`analyser(frame, output_dir, debut="2024-02-01", fin="2024-03-01", run_regression=True)`**  
  Enchaîne nettoyage, descriptifs, tests, figures et exports. Appelée par le Master. Passe explicitement `debut` et `fin` pour sélectionner une période de la collecte étudiée.

* **`main(argv=None)`**  
  Point d’entrée autonome de `analyse.py`. Lit la base indiquée avec `--input`, la période et le dossier de résultats avant d’appeler `analyser()`.

### [`Master_file.py`](Master_file.py) — Orchestration

#### Sélection des comptes

* **`preparer_utilisateurs(users=None, token=None, discover=False)`**  
  Écrit la liste des comptes fournis ou configurés. Si `discover=True`, l’étend via la marche aléatoire. Appelée au lancement d’une collecte API.

#### Identification des ouvertures

* **`identifier_parties(raw, reference)`**  
  Classe les ouvertures à partir des coups de `raw` et du référentiel, ou conserve le libellé fourni en signalant que sa profondeur n’a pas été vérifiée. Appelée par le Master et le notebook.

#### Exécution de la chaîne

* **`main(argv=None)`**  
  Point d’entrée de la chaîne. Lance une collecte avec `--collect` ou relit une base avec `--raw-file`, puis identifie, nettoie et analyse. Les bornes et l’option `--upload` se règlent dans la commande.

### [`Stockage_SSPCloud.py`](Stockage_SSPCloud.py) — Stockage S3

#### Connexion et copie vers S3

* **`client()`**  
  Construit le client S3 utilisé pour lire une collecte depuis le notebook ou envoyer ses fichiers.

* **`upload_folder_to_s3(local_folder, bucket=None, prefix=None, s3_client=None)`**  
  Copie le dossier d’une collecte sous son identifiant. `bucket` et `prefix` remplacent la destination configurée et `s3_client` permet de fournir un client déjà initialisé. Appelée par le Master avec `--upload`.

### [`QueensGambit.ipynb`](QueensGambit.ipynb) — Lecture des données et analyse interactive

Les cellules appellent les modules du projet et définissent deux fonctions locales pour les analyses détaillées.

#### Taux descriptifs et test d’indépendance

* **`taux(df, par, cible="win_suiv")`**  
  Regroupe les observations selon `par` et affiche les effectifs, le taux de la variable binaire `cible` et son intervalle approximatif. Utilisée dans les comparaisons descriptives.

* **`chi2(df, x, y="win_suiv")`**  
  Construit un tableau croisé entre `x` et `y` et renvoie le χ², la valeur p, les degrés de liberté et le V de Cramér. Utilisée dans les analyses détaillées et leur bilan.

# Projet Lichess et répétition des ouvertures

[Ouvrir le notebook dans Colab](https://colab.research.google.com/github/Hadrienfonrojet/ANALYSE-MARCHE-/blob/main/Analyse_data.ipynb)

Le projet est organisé pour comprendre et reproduire chaque calcul. Les scripts comportent des sections `## Partie ...`, des lignes espacées et des commentaires distinguant une colonne, une liste et un DataFrame.

## Ordre de lecture

1. [Guide pédagogique PDF](docs/Guide_pedagogique_analyse.pdf) : notions, rôle des fichiers, hypothèses et interprétation.
2. [Notebook Analyse_data.ipynb](Analyse_data.ipynb) : code et résultats cellule par cellule.
3. [Nettoyage_donnees.py](Nettoyage_donnees.py) et [Tests_repetition.py](analyses/Tests_repetition.py) : colonnes d'historique et tests.
4. [Analyse_ouvertures.py](analyses/Analyse_ouvertures.py) : les cinq parties du parcours d'analyse.
5. [Regression_multiple.py](analyses/Regression_multiple.py) : un modèle explicite et son test F.
6. [Master_file.py](Master_file.py) : enchaînement complet, collecte et sorties.

## Plan de l'analyse

**Partie 1** : créer les DataFrames utiles et les colonnes de passé. `prev_opening_same_color` est une colonne contenant, à chaque ligne, l'ouverture de la précédente partie observée de ce joueur avec la même couleur. Ce n'est pas une liste de ses parties.

**Partie 2** : fonction du χ² avec tableau observé, attentes, formule, degrés de liberté et V de Cramér.

**Partie 3** : dix applications annoncées : résultat précédent × répétition et répétition × résultat courant sous quatre définitions, puis deux questions sur la répétition de la couleur. Holm corrige les tests dont les attentes sont suffisantes. Les stratifications et contrôles supplémentaires restent facultatifs.

**Partie 4** : quatre tests exacts de Fisher sur des tables 2×2, puis une régression multiple du score. Fisher exact n'est pas le test F de Fisher-Snedecor : le premier porte sur des effectifs, le second sur les coefficients du modèle. Le F classique est pédagogique ; le F de Wald avec covariance groupée par joueur est approximatif et nécessite assez de groupes.

**Partie 5** : statistiques descriptives (`mean`, `std`, `median`, `min`, `max`), tableaux par couleur/cadence/famille et graphiques simples. Les descriptifs sont présentés à la fin du parcours, mais doivent aussi être consultés avant l'interprétation des tests.

## Référentiel complet des ouvertures

Le [grand répertoire](References/openings_complet.csv) réunit **3865 lignes** des cinq tables officielles `a.tsv` à `e.tsv`. Les sources et leur version sont dans `References/`. [Creation_openings_complet.py](Scripts_generation_data/Creation_openings_complet.py) construit la table et [Identification_ouvertures.py](Scripts_generation_data/Identification_ouvertures.py) rejoue les positions des cinq ou dix premiers coups complets. Les étiquettes API sont conservées séparément.

Une référence courte peut identifier seulement une famille générale. Les variantes longues ne sont pas attribuées avant leur position finale. Profondeur de reconnaissance, transpositions et ambiguïtés sont expliquées dans [Introduction aux ouvertures](docs/Introduction_aux_ouvertures.md).

## Installation et lancement

```sh
python -m pip install -r requirements.txt
cp .env.example .env
python Master_file.py --users-per-seed 1 --games-per-format 20 --opening-moves 10
```

Renseigner les pseudos dans `LICHESS_SEEDS`. Le jeton facultatif est `LICHESS_TOKEN`. Les bibliothèques, dont `boto3` et `python-chess`, sont installées par requirements.txt ; aucun module métier ne lance pip à l'import.

Pour réanalyser une base sans relancer la collecte :

```sh
python Master_file.py --skip-collect --raw-file chemin/vers/games_enrichies_raw.parquet --opening-moves 5
```

Chaque lancement crée une nouvelle expérience dans `Collectes/<identifiant>/`. Aucune ancienne base n'est effacée. La première cellule Colab crée un nouveau clone du dépôt. Redémarrer le noyau lors d'un changement de version pour ne pas garder d'anciens modules en mémoire.

## Paramétrage

`config_projet.py` regroupe chemins, pseudos, cadences, taille de collecte, référentiel, fenêtre de coups et paramètres S3. Le `.env` privé peut remplacer les valeurs par défaut. `RUN_REGRESSIONS=true` active le modèle multiple ; dans le notebook la variable du même nom permet de le désactiver. Les paramètres non secrets sont enregistrés avec l'expérience.

L'envoi SSP Cloud reste explicite avec `--upload`, sous `s3://hadrien2703/diffusion/projet_ouvertures/<identifiant>/`. Il ne supprime pas d'objets et ne demande pas d'ACL publique. Les vrais secrets ne doivent jamais être publiés.

## Lire les sorties

- `Data/games_enrichies_raw.parquet` : base brute conservée.
- `Data/openings_complet.*` : référentiel officiel complet de cette expérience.
- `Data/games_identifies.parquet` et `openings_observees.csv` : reconnaissance locale et étiquettes API.
- `Data/games_clean.parquet` : base préparée avec répétitions.
- `Resultats/tests_chi2.csv` et `repetition/` : χ², Holm, observés/attendus/résidus et taux.
- `Resultats/fisher/tests_fisher_exact.csv` : tests exacts 2×2 et correction de Holm séparée.
- `Resultats/regression_multiple_resume.csv` et `_coefficients.csv` : modèle, statut, coefficients, R² et tests F. Un modèle non estimable affiche une raison ; les valeurs p groupées restent manquantes s'il y a trop peu de joueurs.
- `Resultats/statistiques_descriptives.csv`, `description_*.csv` et PNG : résumés et graphiques.

Les anciens ensembles de nombreuses régressions logistiques sont remplacés dans le parcours principal par un seul modèle linéaire du score, lisible et commenté.

## Limites statistiques

Les valeurs p supposent un modèle d'échantillonnage et des hypothèses qui ne sont pas garanties par une collecte d'adversaires. Un joueur contribue plusieurs parties et des adversaires peuvent être communs. `valid` ne vérifie que les effectifs attendus du χ². Les valeurs p sont exploratoires, même après Holm ; cette correction ne rend pas les observations indépendantes.

Le modèle du score est linéaire malgré une variable discrète bornée. Son F classique ne bénéficie pas ici d'une justification exacte ; le test de Wald groupé est une approximation. Les résultats sont des associations conditionnelles, jamais des preuves causales.

## Vérifier le logiciel

```sh
python -m unittest discover -s tests -v
```

Les tests utilisent des données simulées, des tableaux connus et des requêtes simulées. Ils vérifient l'identification, le nettoyage, le χ², Fisher exact, la régression, le F et les cellules du notebook. Ils ne valident pas les autorisations réseau ou SSP Cloud réelles.

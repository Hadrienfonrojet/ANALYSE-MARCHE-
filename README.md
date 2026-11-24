# Jeu de la dame · Statistiques des ouvertures

**Comment les taux de victoire, de défaite et de nulle varient-ils selon l’ouverture, le temps et les séries observées ?**

[![Ouvrir dans Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Hadrienfonrojet/ANALYSE-MARCHE-/blob/main/Analyse_data.ipynb)

L’approfondissement du projet porte sur les statistiques descriptives et la construction rigoureuse des variables. Trois exercices étudient les résultats par ouverture, une nouvelle base dans une fenêtre temporelle et les séries maximales de chaque résultat. Trois régressions linéaires de probabilité complètent cette exploration, pour la victoire, la défaite et la nulle à la suivante.

## Ce que tu peux reproduire

La démonstration utilise **3 600 lignes fictives pour 40 comptes**, du 1er janvier au 30 mars 2024. Les préfixes de coups sont légaux et proviennent du référentiel officiel. Les résultats sont simulés, avec un coefficient générateur nul de répétition. La graine vaut 73.

Les deux notebooks utilisent cette même base figée. Les sorties enregistrées sont disponibles dès l’ouverture. Les empreintes du CSV et des cinq tables officielles sont dans `data_demo/parties_demo.json`. Les versions directes sont fixées dans `requirements.txt` et toutes les versions de l’environnement validé sont dans `requirements-lock.txt`. L’environnement de référence est Python **3.12**, testé avec Python 3.12.14 sur macOS.

## Installation et commandes centrales

Depuis la racine du dépôt, avec Python 3.12 installé :

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m Scripts_generation_data.Simulation_reproductible --verify
python Master_file.py --demo --debut 2024-01-15 --fin 2024-03-01
python executer_notebook.py
python -m unittest discover -s tests -v
```

Sous Windows, l’activation s’effectue avec `.venv\Scripts\activate`. Le script `executer_notebook.py` utilise le Python courant pour son noyau Jupyter et enregistre les sorties dans le notebook. Pour l’ouvrir et modifier les cellules, le bouton Colab ci-dessus donne accès à l’éditeur.

Pour lancer uniquement les trois exercices sur la démonstration :

```bash
python analyse_statisitques.py --demo --debut 2024-01-15 --fin 2024-03-01
```

Pour reconstruire une nouvelle copie du CSV fictif :

```bash
python -m Scripts_generation_data.Simulation_reproductible --output /tmp/parties_demo.csv
```

Cette commande refuse d’écraser une copie existante. La vérification avec `--verify` reconstruit les données en mémoire et compare leurs octets et les empreintes des sources.

## Sources de données

| Table | Source | Récupération et rôle |
|---|---|---|
| Parties réelles | API Lichess | Export NDJSON des comptes sélectionnés, avec résultats, dates, couleurs, cadences, classements, adversaires et coups. |
| Ouvertures | Dépôt officiel `lichess-org/chess-openings` | Cinq TSV officiels figés, `a.tsv` à `e.tsv`, version `712a58be746c143f4ab935b68acc50f4bac813eb`. Ils donnent noms, ECO et positions à reconstruire. |
| Démonstration fournie | Simulation du projet | Base reproductible pour vérifier toute la chaîne sans accès réseau après installation. |

Les parties et le référentiel sont deux jeux de données distincts du même producteur Lichess. La simulation sert à la reproductibilité de la démonstration. Le rendu empirique demanderait une collecte réelle. Le référentiel officiel est diffusé sous CC0.

[Référentiel officiel](https://github.com/lichess-org/chess-openings) · [API officielle](https://lichess.org/api) · [Consignes API](https://lichess.org/page/api-tips)

## Collecter des parties réelles

Créer un `.env` privé depuis `.env.example` et définir les paramètres souhaités. Le jeton Lichess est facultatif selon l’accès. Les identifiants AWS restent privés.

```bash
python Master_file.py --collect --users compte1 compte2 compte3 compte4 compte5 \
  --since 2024-01-01 --until 2024-04-01 --debut 2024-01-15 --fin 2024-03-01
```

Remplacer les exemples par les comptes choisis. Sans `--users`, les comptes sont lus dans `LICHESS_SEEDS`. `--discover` active explicitement une exploration d’adversaires avec une graine fixée. `GAMES_PER_FORMAT` est un plafond **par compte et par cadence**. Un plafond peut créer des trous dans la chronologie. Pour une couverture complète de la fenêtre, vérifier le plafond et comparer les volumes collectés.

La collecte est séquentielle. Elle emploie un timeout, enregistre les réponses brutes NDJSON et attend au moins 60 secondes après un HTTP 429. Une erreur est propagée et les fichiers déjà écrits restent disponibles. Les listes et les historiques Lichess peuvent évoluer. Pour reproduire une estimation, réutiliser les fichiers conservés et leurs empreintes, plutôt que lancer une nouvelle requête réseau.

## Réanalyser un fichier et conserver les résultats

```bash
python Master_file.py --raw-file chemin/vers/parties.parquet --debut 2024-01-15 --fin 2024-03-01
```

Le fichier peut être CSV ou Parquet. Les champs indispensables sont `user_id`, `result`, `opening_name` ou les `moves` permettant de l’obtenir, et une date ISO ou un timestamp. Les champs `rating`, `opponent_rating`, `color` et `format_partie` sont nécessaires aux modèles ajustés. Une étiquette fournie sans coups est conservée avec un statut de profondeur non vérifiée.

Chaque lancement crée `Collectes/<identifiant>/Data` et `Collectes/<identifiant>/Resultats`. Le brut, la base identifiée, le nettoyage, le sous-échantillon temporel, les tableaux et figures sont conservés. Le manifeste indique la source, la version Python, les bibliothèques, les bornes et l’empreinte d’entrée.

`--upload` copie la nouvelle collecte vers `s3://hadrien2703/diffusion/projet_ouvertures/<identifiant>/`. Aucun objet existant n’est supprimé. Une réservation conditionnelle empêche une réutilisation du même identifiant. Les fichiers cachés et le `.env` sont exclus.

## Les trois exercices dans `analyse_statisitques.py`

1. **Toute la base**. Effectifs, joueurs, taux de victoire/défaite/nulle, score moyen, écart-type et taux moyen par joueur pour chaque ouverture. Une nulle vaut 0 dans chacun des indicateurs victoire et défaite, 1 dans l’indicateur nulle et 0,5 dans le score.
2. **Fenêtre temporelle**. Copie `[début, fin[` en UTC, export `nouveau_jeu_intervalle.parquet`, statistiques mensuelles et étude d’une ouverture. Il s’agit d’un sous-échantillon, pas d’une collecte indépendante.
3. **Séries**. Longueurs et maxima par joueur, ouverture et résultat dans la chronologie complète observée. Un changement de résultat ou d’ouverture interrompt une série. Les nulles interrompent victoires et défaites et possèdent leurs propres séries. Les dates ex aequo constituent une rupture. Les séries dans une fenêtre sont tronquées à ses bornes.

## Lire les modèles et les tests

Les trois modèles OLS expliquent les indicateurs du résultat suivant avec répétition, victoire courante, écart Elo pour 100 points, couleur, cadence et famille d’ouverture de la suivante. Ils utilisent le même échantillon complet et des erreurs-types groupées par compte. Un coefficient de 0,02 représente **2 points de probabilité**. Les modèles peuvent produire des prédictions hors [0, 1], comptées dans le diagnostic.

Les trois cibles somment à 1. Les équations sont complémentaires et leurs coefficients de répétition ne constituent pas trois preuves indépendantes. Les trois tests centraux de répétition sont corrigés par Holm. Les modèles trop petits, constants ou colinéaires sont signalés. Avec moins de 20 comptes, les coefficients restent affichés si estimables mais les incertitudes groupées sont masquées.

Le χ² et Fisher sont des comparaisons exploratoires sur les transitions après victoire. Holm corrige les trois cadres annoncés. Le regroupement par joueur ne règle pas toutes les dépendances entre adversaires. Le choix d’ouverture, l’incomplétude des historiques et la taille des groupes limitent une interprétation causale.

## Modifier les notebooks

Dans Colab, **Fichier → Enregistrer une copie dans Drive** crée une version personnelle éditable. Double-cliquer sur le texte permet de modifier les cellules Markdown. **Exécution → Tout exécuter** lance les calculs. Après une installation de dépendances, redémarrer la session si Colab le demande. Pour publier la copie, utiliser **Fichier → Enregistrer une copie dans GitHub**.

Les variables `SOURCE`, `LOCAL_FILE`, `S3_RUN_ID`, `DEBUT`, `FIN` et `OUVERTURE` sont regroupées au début. Avec `SOURCE="s3"`, le notebook lit le Parquet de la collecte indiquée via boto3. Les cellules de texte contiennent les questions, les choix méthodologiques et des espaces d’interprétation.

## Pour le rendu écrit et oral

L’approfondissement porte sur l’exploration descriptive. Sélectionner un tableau des taux, un graphique temporel, une table des séries maximales et les trois coefficients centraux. Les résultats de démonstration sont dans `resultats_demo/` et les trois guides sont dans `docs/`.

- [Notebook principal](Analyse_data.ipynb)
- [Notebook de rendu](notebooks/Rendu_Lichess.ipynb)
- [Résumé de l’étude](RENDU.md)
- [Méthode et fonctions](ANALYSE_DU_PROJET.md)
- [Vérifications](VERIFICATIONS.md)

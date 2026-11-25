# Le rôle des ouvertures aux échecs, inspiré du *Jeu de la dame*

[![Ouvrir dans Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Hadrienfonrojet/ANALYSE-MARCHE-/blob/main/QueensGambit.ipynb)

**Question de départ :** répéter une ouverture dépend-il de l’issue de la partie précédente ?

**Problématique :** comment les taux de victoire, de défaite et de nulle varient-ils selon l’ouverture, la couleur, la période et la répétition d’une même stratégie ?

Tout le projet se lit dans **`QueensGambit.ipynb`** : collecte, nettoyage, statistiques descriptives, tests (χ², Fisher, bootstrap par joueur, correction de Holm) et régressions (modèles linéaires de probabilité avec effet fixe joueur, logit).

## Données

- **13 727 parties classées** de **30 comptes Lichess**, du 25 novembre 2025 au 24 novembre 2026.
- Les comptes sont découverts par marche aléatoire à partir de trois graines (`macaquezizi`, `T34USSR`, `lucascrotti`), avec au plus 300 parties par compte et par cadence.
- La base brute est publiée dans `donnees/parties_1an.parquet` : le notebook la relit sans réinterroger Lichess.
- L’ouverture est identifiée à partir des coups et analysée au niveau de la **famille** (Sicilienne, Française…).

## Résultat principal

On répète sa famille d’ouverture dans 11,7 % des enchaînements après une victoire et dans 11,9 % après une nulle ou une défaite (χ², p = 0,65). Répéter ne change pas non plus les chances de gagner la partie suivante. Les résultats dépendent surtout de l’écart d’Elo et, plus faiblement, de la couleur.

## Fichiers

| Fichier | Rôle |
|---|---|
| `QueensGambit.ipynb` | Le notebook d’analyse complet, avec ses sorties |
| `config.py` | Paramètres publics et lecture du fichier privé `.env` |
| `import_utilisateurs.py` | Découverte des comptes (marche aléatoire entre adversaires) |
| `import_parties.py` | Téléchargement des parties via l’API Lichess (NDJSON) |
| `import_ouvertures.py` | Référentiel officiel des ouvertures et identification par les coups |
| `nettoyage.py` | Nettoyage, contrôle des résultats et des ruptures d’historique |
| `analyse.py` | Statistiques par ouverture, fenêtre de temps, séries, régressions |
| `Analyse_repetition_ouverture.py` | Enchaînements de parties, χ², Fisher, bootstrap par joueur |
| `Master_file.py` | Enchaîne collecte, identification, nettoyage et analyse |
| `Stockage_SSPCloud.py` | Copie de la collecte sur le stockage S3 du SSP Cloud |

## Reproduire l’analyse

```bash
pip install -r requirements.txt
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

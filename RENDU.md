# Jeu de la dame · Résultats, temps et séries par ouverture

**Problématique** · Comment les taux de victoire, défaite et nulle varient-ils selon l’ouverture et la période ? Quelles séries observe-t-on avec une même ouverture ?

Le projet approfondit l’exploration descriptive et la construction des variables. Les trois modèles de probabilité linéaire donnent une lecture ajustée courte. Les résultats présentés dans le dépôt portent sur **3 600 observations fictives et 40 comptes**, construites à graine 73 à partir de préfixes de coups du référentiel officiel.

## Les trois exercices à présenter

| Exercice | Question | Résultat à lire |
|---|---|---|
| Ouvertures | Quel est le taux de chaque résultat avec cette ouverture ? | Effectifs et proportions, nulles incluses. |
| Temps | Les taux évoluent-ils dans une période annoncée ? | Sous-échantillon du 15 janvier au 1er mars 2024, fin exclue, et taux mensuels. |
| Séries | Quelle est la plus longue série de chaque résultat avec la même ouverture ? | Maximum par ouverture, calculé sur les séquences individuelles adjacentes. |

Une nulle est un résultat distinct, qui interrompt les séries de victoire et de défaite. Le maximum d’une série dépend du volume et de la continuité des observations.

## Trois modèles complémentaires

Une régression explique la victoire suivante, une autre la défaite et une troisième la nulle, avec les mêmes observations et contrôles. Les coefficients sont en points de probabilité. Les erreurs-types sont groupées par joueur et les trois tests centraux de répétition sont corrigés par Holm. Les comptes partagés, la sélection des ouvertures et les trous de collecte limitent une interprétation causale.

## Documents et accès

- [Notebook complet, éditable dans Colab](https://colab.research.google.com/github/Hadrienfonrojet/ANALYSE-MARCHE-/blob/main/Analyse_data.ipynb)
- [Notebook de rendu avec la même base et les mêmes calculs](notebooks/Rendu_Lichess.ipynb)
- [Trois exercices et modèles](analyse_statisitques.py)
- [Commandes reproductibles](README.md)
- [Sources et nettoyage, trois pages](docs/01_Reproductibilite_et_nettoyage.pdf)
- [Statistiques descriptives, trois pages](docs/02_Statistiques_descriptives.pdf)
- [Positionnement et lecture des modèles](docs/03_Positionnement_du_projet.pdf)

Pour l’oral, sélectionner le tableau des taux, le graphique temporel, les maxima et les coefficients de répétition. Annoncer d’abord le caractère simulé des données et les effectifs.

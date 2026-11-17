# Les ouvertures répétées sur Lichess

**Projet Python pour la data science · Hadrien Fonrojet**

Après une victoire, est-ce qu’un joueur gagne plus souvent sa partie suivante lorsqu’il répète la même ouverture ? Le projet compare les taux de victoire après répétition et changement, puis ajuste la comparaison sur la couleur, la cadence et l’écart Elo.

- [Notebook de rendu avec les résultats enregistrés](notebooks/Rendu_Lichess.ipynb)
- [Exécuter le notebook dans Colab](https://colab.research.google.com/github/Hadrienfonrojet/ANALYSE-MARCHE-/blob/main/notebooks/Rendu_Lichess.ipynb)
- [Notebook de travail et repères de lecture](Analyse_data.ipynb)
- [Configuration et collecte](README.md)

## Parcours de lecture

1. **Construire la base.** Simuler des parties puis identifier leurs ouvertures à partir des positions dans les dix premiers coups complets. Contrôler les champs manquants et les doublons.
2. **Décrire les données.** Comparer les effectifs, les scores et les taux par cadence ou par type de transition.
3. **Tester l’association.** Lire les effectifs observés et attendus, le χ² et le test exact de Fisher. Compléter par un bootstrap par joueur et une régression logistique ajustée.
4. **Discuter les limites.** Examiner le choix des ouvertures, la dépendance entre les parties d’un même joueur et la différence entre une partie immédiatement suivante et la prochaine partie de la même couleur.

## Résultats de démonstration

La simulation compte **1 200 parties et 40 joueurs fictifs**. Dans le cadre principal, on conserve 544 transitions après victoire. Le taux de victoire suivante est de 45,6 % après répétition (155/340) et 47,5 % après changement (97/204). L’écart est de −2,0 points environ, avec un intervalle bootstrap à 95 % d’environ [−9,3 ; +5,3] points. Le test du χ² donne 0,197 pour 1 degré de liberté, avec une valeur p de 0,657. Le rapport des cotes ajusté de la répétition vaut environ 0,90.

Ces valeurs décrivent la simulation. Le mécanisme simulé dépend du classement et de la couleur, et attribue un coefficient nul à la répétition. Une estimation empirique demande une collecte réelle documentée.

## Reproduire

Dans Colab, ouvrir le notebook puis choisir **Exécution → Tout exécuter**. En local, depuis la racine du dépôt :

```bash
python -m pip install -r requirements.txt
jupyter notebook notebooks/Rendu_Lichess.ipynb
```

La graine de la simulation vaut 73. Le notebook s’appuie sur les cinq tables d’ouvertures déjà présentes dans `References/`.

[Structure du rendu inspirée du projet sur les Jeux olympiques](https://github.com/oldblindmole/Projet_Python_Data_Science_JO/blob/main/main.ipynb)

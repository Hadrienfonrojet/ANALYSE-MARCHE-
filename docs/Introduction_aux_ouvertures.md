# Comprendre les ouvertures utilisées dans le projet

## Ce que désigne une ouverture

Une ouverture correspond au début d'une partie d'échecs : les premiers coups organisent le développement des pièces et la position. Elle n'est pas choisie par un joueur seul ; les réponses de l'adversaire participent à la position obtenue. Une même famille comprend plusieurs variantes.

Dans ce projet, on ne cherche pas à reconstruire une théorie des ouvertures. On utilise la reconnaissance fournie par Lichess pour étudier les associations entre familles jouées, répétition et résultats.

## Où est le fichier des ouvertures

Le **script qui construit la table** est [Scripts_generation_data/Creation_openings_complet.py](../Scripts_generation_data/Creation_openings_complet.py).

Le **fichier de données produit après collecte** est `Collectes/<identifiant>/Data/openings_complet.parquet`. Une copie lisible dans un tableur est aussi produite : `openings_complet.csv`. Ces données ne sont pas stockées dans GitHub par défaut ; elles n'existent qu'après l'exécution d'une collecte ou d'une réanalyse. C'est pourquoi voir le script sur GitHub ne signifie pas qu'une table de données y est déjà présente.

Le **master qui appelle cette création** est [Master_file.py](../Master_file.py), dans `creer_referentiel_ouvertures(raw)`. Il appelle réellement `build_openings(raw)` après avoir obtenu les parties.

## Comment la table est créée

1. `collect_games()` interroge l'API des parties Lichess avec `opening=true`.
2. `parse_game()` extrait `opening.eco` et `opening.name` vers `eco` et `opening_name`.
3. `extraire_ouvertures()` retire les informations absentes et les doublons ECO/nom.
4. Le nom complet est conservé. La famille correspond à la partie du nom située avant les deux-points.
5. `sauvegarder_ouvertures()` écrit le Parquet et le CSV dans cette expérience.

Le nom historique `Creation_openings_complet.py` est conservé pour retrouver le fichier. Il produit un référentiel **des ouvertures observées dans la collecte**, pas un dictionnaire exhaustif de toutes les ouvertures possibles. L'ancienne liste manuelle de 50 ouvertures n'est plus utilisée.

## Les colonnes à comprendre

| Colonne | Signification |
|---|---|
| `eco` | Code de classement renvoyé par Lichess |
| `name` | Nom complet de l'ouverture reconnue, variante comprise |
| `family` | Texte avant les deux-points dans le nom complet |
| `eco_group` | Première lettre du code ECO, regroupement plus large |
| `source` | `lichess_api`, origine des informations |

Par exemple, un nom commençant par `Sicilian Defense:` est regroupé dans la famille `Sicilian Defense`. Les différents noms complets restent présents dans le référentiel. Un code ECO seul n'identifie pas nécessairement une variante unique : on conserve le couple code/nom.

## Comment les ouvertures deviennent des variables d'analyse

`prepare(raw, openings)` rapproche chaque partie du référentiel et produit `opening_family`. Les parties sont ensuite triées par joueur et par date.

- `repeat_all` compare la famille à celle de la partie observée précédente, quelle que soit la couleur.
- `repeat_same_color` compare à la précédente partie observée avec la même couleur.
- `same_color_consecutive` décrit la répétition de la couleur elle-même, pas celle de l'ouverture.

Exemple : blanc A, noir B, blanc A. La troisième partie répète la famille A avec les blancs, mais pas la famille B de la partie immédiatement précédente.

Les premières observations et les transitions avec une ouverture inconnue restent manquantes. Une information absente n'est ni une répétition ni un changement. Les historiques portent sur les parties collectées, pas nécessairement sur toutes les parties réellement jouées.

## Ce que l'analyse peut dire

Les χ² examinent l'association entre résultat précédent et répétition, puis entre répétition et résultat courant. Les comparaisons par couleur, cadence et Elo aident à décrire le contexte. Elles ne prouvent pas qu'une ouverture ou sa répétition cause une victoire.

Pour suivre les calculs et leurs justifications, ouvrir [Analyse_data.ipynb](../Analyse_data.ipynb), sections 3 à 16. Le code des tests y est visible, et sa version de référence est dans [analyses/Tests_repetition.py](../analyses/Tests_repetition.py).

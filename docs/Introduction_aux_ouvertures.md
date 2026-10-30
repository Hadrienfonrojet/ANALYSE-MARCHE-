# Le référentiel complet des ouvertures et leur identification

## Le gros répertoire demandé

Le projet conserve les cinq fichiers officiels **a.tsv, b.tsv, c.tsv, d.tsv et e.tsv** du dépôt [lichess-org/chess-openings](https://github.com/lichess-org/chess-openings). Chaque ligne contient un code ECO, un nom et une suite de coups PGN. Les cinq tables sont réunies, même si leurs ouvertures ne sont jamais rencontrées dans la collecte.

Les fichiers visibles dans GitHub sont :

- [References/openings_complet.csv](../References/openings_complet.csv) : la grande table, lisible dans un tableur ;
- [References/openings_complet.parquet](../References/openings_complet.parquet) : la même table pour Python ;
- [References/lichess_openings/](../References/lichess_openings/) : les cinq sources dans un dossier identifié par la révision officielle ;
- [References/sources_reference.json](../References/sources_reference.json) : version, date et empreintes des sources.

Le référentiel réuni contient **3865 lignes** pour la version livrée. Il est complet au sens des cinq tables officielles de cette version, pas au sens de toutes les ouvertures théoriquement possibles.

## Le fichier qui construit la table

[Creation_openings_complet.py](../Scripts_generation_data/Creation_openings_complet.py) effectue les étapes suivantes :

1. télécharger les cinq TSV de la révision configurée si les sources ne sont pas déjà présentes ;
2. réunir les lignes et retirer les doublons exacts ECO/nom/PGN ;
3. rejouer chaque suite PGN avec `python-chess` ;
4. enregistrer sa position finale, son nombre de demi-coups et la suite UCI ;
5. écrire la grande table dans `References/` et la copier dans `Data/` de l'expérience.

La table contient notamment `eco`, `name`, `pgn`, `uci`, `reference_ply`, `position_key` et `family`. La famille est le texte avant les deux-points dans le nom.

## Identifier une partie à partir des coups joués

[Identification_ouvertures.py](../Scripts_generation_data/Identification_ouvertures.py) reconstruit les positions d'une partie standard depuis sa suite de coups SAN (`moves`, demandée à l'API Lichess).

**Un coup complet correspond au coup des blancs puis au coup des noirs.** Ainsi, 5 coups complets correspondent à 10 demi-coups et 10 coups complets à 20 demi-coups.

Le programme inspecte les positions atteintes dans cette fenêtre, cherche celles présentes dans le référentiel et retient la variante officielle la plus profonde effectivement atteinte. Il n'attribue pas le nom d'une variante longue à son simple début. Une référence courte peut néanmoins identifier une famille générale : la profondeur exacte figure dans les sorties.

Les positions sont comparées avec les pièces, le trait, les droits de roque et l'en passant légal. Les compteurs de coups sont ignorés. Cette comparaison reconnaît certaines transpositions, lorsque des ordres de coups différents aboutissent à une même position.

Plusieurs noms officiels peuvent correspondre à une position. Le programme garde tous les candidats et signale `plusieurs_noms`. Le nom affiché est choisi de manière reproductible par profondeur de référence, puis code ECO et nom ; ce choix n'est pas une certitude sur la préférence théorique d'un joueur.

## Choisir cinq ou dix coups

Dans le terminal :

```sh
python Master_file.py --opening-moves 5
python Master_file.py --opening-moves 10
```

Dans le notebook, modifier `OPENING_MOVES = 5` ou `10` avant `prepare`.

La configuration par défaut exige au moins 5 coups complets disponibles. Une partie plus courte, des coups absents ou invalides, une variante non standard ou une absence de correspondance restent explicitement signalés ; ils ne sont pas remplacés silencieusement par le nom API. Les coups situés après la fenêtre ne sont pas utilisés.

## Séparer le nom API du résultat local

- `api_eco` et `api_opening_name` conservent les étiquettes reçues dans l'API des parties.
- `eco` et `opening_name` contiennent l'identification calculée à partir des coups et du référentiel complet.
- `opening_match_ply` indique le demi-coup de la partie où la position retenue a été rencontrée.
- `opening_reference_ply` indique la profondeur de la ligne officielle reconnue.
- `opening_plies_examined` indique le nombre de demi-coups effectivement inspectés.
- `opening_identification_status` et `opening_candidates` explicitent les échecs et les noms possibles.

Le nom API peut différer : il peut utiliser une autre convention ou davantage de coups. Le programme ne le considère pas comme une vérité cachée remplaçant la méthode limitée à 5 ou 10 coups.

## Où sont les sorties de l'expérience

`Data/openings_complet.*` contient le grand référentiel. **`Data/openings_observees.csv`** est une table séparée des ouvertures effectivement identifiées et du nombre de parties distinctes. `Data/games_identifies.parquet` conserve les étiquettes API et locales ; `Data/games_clean.parquet` contient les variables nettoyées pour l'analyse. `Resultats/bilan_identification_ouvertures.csv` résume les statuts du master.

Une ancienne base sans `moves` peut être lue mais ne peut pas être réidentifiée localement. Il faut recollecter les coups. Les associations statistiques restent exploratoires : le choix d'ouverture dépend des deux joueurs et les parties d'un même joueur ne sont pas indépendantes.

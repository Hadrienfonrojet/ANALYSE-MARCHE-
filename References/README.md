# Référentiel complet officiel Lichess

Les cinq fichiers `a.tsv` à `e.tsv` du dépôt [lichess-org/chess-openings](https://github.com/lichess-org/chess-openings) sont conservés sous `lichess_openings/712a58be746c143f4ab935b68acc50f4bac813eb/`. Le jeu source est publié sous CC0-1.0.

La table réunie `openings_complet.csv` et sa version Parquet contiennent 3865 lignes : 823 dans a.tsv, 781 dans b.tsv, 1250 dans c.tsv, 644 dans d.tsv et 367 dans e.tsv. Les positions, suites UCI, profondeurs et familles sont calculées par le script du projet à partir des PGN officiels.

`sources_reference.json` conserve la révision, la date de construction et les empreintes SHA-256. Changer OPENINGS_REFERENCE_REV puis appeler build_openings(refresh=True) pour adopter une autre version.

Cette table contient toutes les lignes de cette version du référentiel, et pas seulement les ouvertures rencontrées dans la collecte. L’identification des parties est expliquée dans [Introduction aux ouvertures](../docs/Introduction_aux_ouvertures.md).

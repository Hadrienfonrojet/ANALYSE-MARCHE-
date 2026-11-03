# Vérifications de la livraison — 3 novembre 2026

- 17 tests du complément passent : référentiel officiel 3865 entrées ; classification 5/10 coups ; nulles et dernières parties ; ouvertures inconnues ; historique même couleur distinct ; χ² sur tableau connu ; Fisher ; bootstrap par compte ; régression groupée sur données fictives ; cas de cinq comptes ; fichiers conservés ; requêtes API et S3 simulées ; Master sur base locale sans collecte.
- 1 test supplémentaire exécute les 28 cellules de code du notebook de 77 cellules, en mode DEMO, avec GET/POST réseau interdits. Il passe.
- Les fonctions d’Import_des_users.py et Import_une_partie.py ont été comparées par leur syntaxe à celles du dossier Projet-info-2A-main : identiques. Seul le bloc d’exemple entre guillemets est ajouté.
- config_projet.py et .env.example sont conservés à l’identique de l’état GitHub avant cette livraison.
- La syntaxe des scripts est vérifiée ; les sorties de notebook sont retirées ; aucun vrai .env n’est livré ; les motifs de tokens et clés reconnus ont été recherchés.
- L’ancien dépôt est conservé dans ANALYSE-MARCHE-ARCHIVE-2026-11-03. Le commit a73cf1a24963ef49ec33ffe9dbbf781ffcf4a3df, état exact avant modification, est conservé dans son historique. Une correction ultérieure retire le token en clair de la version courante de son script de diagnostic ; le ZIP d’archive retire également ce token. Le token reste dans l’historique Git conservé et doit être révoqué s’il est actif.

Aucune collecte réelle, lecture de tes données S3 ou écriture réelle sur S3 n’est effectuée pour ces vérifications. Les résultats de démonstration ne constituent pas une analyse empirique de tes parties. Les limites réseau des importeurs conservés sont documentées dans ANALYSE_DU_PROJET.md.

# Vérifications du projet

Version du 24 novembre 2026. Le dépôt conserve les calculs de sa démonstration, avec un découpage plus lisible et des protections supplémentaires pour les historiques réels.

## Exécution complète

- Python 3.12.14, dépendances fixées dans `requirements-lock.txt`.
- Notebook principal : 45 cellules, dont 19 cellules de code exécutées dans l’ordre, sans sortie d’erreur.
- `notebooks/Rendu_Lichess.ipynb` est une copie identique du notebook exécuté.
- 33 tests automatisés réussis : `python -m unittest discover -s tests -v`.
- Les fonctions d’import sont testées avec réponses simulées et erreurs contrôlées. Aucune nouvelle collecte réelle ni écriture S3 n’est nécessaire à ces vérifications.

## Conservation des résultats

Les tableaux des ouvertures, des périodes, des maxima, des tests et des trois modèles ont été comparés à la version GitHub précédente. Les huit CSV communs, hors bilan enrichi, sont identiques à une tolérance numérique de 10^-12. Les modèles conservent 3 560 transitions et 40 comptes. Le bilan gagne des compteurs de ruptures et de chronologies incertaines.

La simulation fournie reste inchangée : 3 600 lignes, 40 comptes, graine 73 et effet générateur propre de répétition nul. Ses empreintes et celles des cinq sources officielles restent vérifiées.

## Cas limites couverts

Les tests contrôlent : taux avec nulles, fenêtres UTC semi-ouvertes, séries interrompues par une nulle ou un changement d’ouverture, ouvertures inconnues, dates ex aequo, ruptures après un rejet, comptes avec date inconnue, nettoyage répété sans perte des ruptures, conservation des timeout avec résultat exploitable, groupes de test absents, alignement des observations de régression avec Elo manquant, erreurs API, pause après HTTP 429, cache après échec, changement de paramètres et modification du contenu brut. La conservation locale et l’absence de suppression S3 sont contrôlées avec un client simulé.

## Limites

Les tests ne prouvent pas la représentativité des comptes ni la complétude des historiques. Les valeurs p du χ² et de Fisher restent exploratoires avec plusieurs transitions par joueur. Le groupement des erreurs-types et le bootstrap par compte ne règlent pas toutes les dépendances entre adversaires. Les résultats de démonstration ne constituent pas des conclusions empiriques sur Lichess.

# Vérifications de la livraison

## Environnement de référence

Python 3.12.14, environnement virtuel isolé créé depuis zéro, installation réussie des dépendances directes puis gel de l’ensemble des versions dans requirements-lock.txt. `python -m pip check` ne trouve aucune dépendance cassée. Le fichier `.python-version` indique Python 3.12.

## Base et sources

Le CSV de démonstration contient 3 600 lignes fictives pour 40 comptes. La commande `python -m Scripts_generation_data.Simulation_reproductible --verify` reconstruit les données à graine 73 et compare les octets du CSV et les empreintes des cinq sources. Elle réussit. Le référentiel figé conserve 3 865 entrées.

## Exécution normale

`python Master_file.py --demo --debut 2024-01-15 --fin 2024-03-01` termine et exporte les trois exercices, les trois modèles linéaires et les graphiques. Le sous-échantillon temporel comporte 1 840 lignes. Les données brutes, identifiées et nettoyées sont conservées dans des fichiers distincts.

Le notebook principal est exécuté entièrement dans un vrai noyau Jupyter avec le Python de l’environnement courant. Les 10 cellules de code terminent et les sorties sont enregistrées. Le notebook de rendu contient les mêmes cellules, réglages et résultats. Toutes les cellules sont éditables et les zones d’interprétation sont des cellules Markdown.

## Tests automatisés

22 tests passent. Ils couvrent les proportions avec nulles, les valeurs manquantes, le bilan de nettoyage, les formats de date, les bornes temporelles, les périodes vides, les séries interrompues par nulles/ouvertures inconnues/changements/dates ex aequo, la distinction des joueurs, le χ² connu, la profondeur d’identification, les trois modèles sur le même échantillon, les erreurs API et reprises après 429, la préservation S3 simulée, les bases sans coups, les exports et les empreintes des fichiers. Les sorties des deux notebooks sont validées.

## Documents

Les trois PDF comportent respectivement 3, 3 et 2 pages. Toutes les pages ont été rendues et contrôlées visuellement. Leurs chiffres viennent de la même exécution de démonstration que les tableaux publiés. Les noms d’ouvertures y sont abrégés pour la lecture et les CSV conservent les variantes complètes.

## Portée de cette vérification

Les résultats livrés sont simulés. La collecte API réelle et les permissions du compte SSP Cloud ne sont pas testées par des appels réels dans cette livraison. Les tests de ces chemins utilisent des réponses et clients simulés. La collecte combine deux tables distinctes du même producteur Lichess. Un véritable rendu empirique demande un échantillon réel documenté.

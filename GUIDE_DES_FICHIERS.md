# Guide de lecture du projet Jeu de la dame

## Objectif et ordre conseillé

Nous étudions les résultats associés aux ouvertures : leurs taux de victoire, de défaite et de nul, leur évolution dans une période et leurs séries maximales. Nous décrivons ensuite si répéter une ouverture après une victoire est associé à une autre victoire. Le projet reste une étude observationnelle. Le notebook rassemble la présentation, les calculs et les espaces d’interprétation.

Lire d’abord `Analyse_data.ipynb`, puis `analyse.py`, `Analyse_repetition_ouverture.py` et `nettoyage.py`. Les fichiers d’import servent à expliquer la constitution des données.

## 1. Configuration et conservation

`config.py` contient les paramètres. `get_lichess_token()` lit le jeton privé au moment de l’utilisation. `create_run()` crée un dossier unique `Collectes/<identifiant>/Data` et `Resultats`, et écrit les paramètres publics de l’expérience. Un simple import ne crée aucun dossier.

Le bucket est `hadrien2703`, le préfixe est `diffusion/projet_ouvertures`. Les clés restent dans l’environnement ou un `.env` privé. `Stockage_SSPCloud.client()` prépare boto3 ; `upload_folder_to_s3()` réserve une nouvelle destination, copie les fichiers et conserve les sources locales. Il ne supprime aucun objet. Les fichiers cachés ne sont pas envoyés.

## 2. Importer les utilisateurs et les parties

Dans `import_utilisateurs.py`, `get_recent_opponents()` extrait les comptes adverses depuis le JSON retourné par l’API. Il n’y a pas de scraping HTML. `discover_users_random_walk()` tire des adversaires avec une graine et des listes triées, puis explore le réseau. Le réseau peut changer ; la liste sélectionnée est donc conservée. Les joueurs ne constituent pas un échantillon représentatif de Lichess.

Dans `import_parties.py`, `telecharger_parties()` traite une requête à la fois, attend après une limitation et signale les échecs. `lire_ou_telecharger()` conserve le brut et un manifeste : une reprise exige les mêmes paramètres et la même empreinte. Une requête réussie sans partie se distingue d’un échec. `partie_vers_ligne()` transforme une partie en une ligne du point de vue d’un compte. `extract_games_user()` collecte un compte et une cadence. `import_games_df()` réunit les comptes et les cadences.

Le Master crée toujours une nouvelle collecte. Pour reprendre une requête déjà effectuée, les fonctions d’import peuvent réutiliser leur dossier existant. Une modification du plafond, de la période ou des paramètres exige un nouveau dossier. Un plafond trop petit et des cadences omises peuvent laisser des trous impossibles à détecter uniquement avec les lignes collectées.

## 3. Identifier les ouvertures

`import_ouvertures.py` télécharge ou relit `a.tsv` à `e.tsv` d’une révision officielle figée. `download_sources()` récupère les sources ; `read_reference()` construit la grande table. `position_key()` décrit une position comparable. `build_position_index()` prépare la recherche. `identify_opening()` rejoue les coups et retient la position officielle la plus précise atteinte dans la limite choisie. `identify_games()` applique ce travail à toute la base. `creer_openings()` conserve la table et sa provenance.

Cinq coups complets au minimum doivent être disponibles ; dix coups sont examinés au maximum par défaut. Un coup complet comprend un coup blanc et un coup noir. Une famille peut être connue plus tôt ; la profondeur exacte est enregistrée. Les positions équivalentes permettent certaines transpositions. Les noms de référence partageant une position restent documentés. Un nom complet et une famille ne sont pas le même niveau de regroupement.

## 4. Nettoyer sans déformer la chronologie

Dans `nettoyage.py`, `convertir_dates()` accepte dates ISO, secondes et millisecondes en UTC. `normaliser_identifiants()` harmonise comptes, identifiants et résultats. `selectionner_parties()` écarte les lignes invalides et les doublons compte/partie. `creer_variables()` ajoute les indicateurs `win`, `loss`, `draw`, le score, la famille et l’écart Elo.

`preparer_parties()` renvoie la table et le bilan ; `clean_games()` renvoie seulement la table. `sauvegarder_nettoyage()` refuse d’écraser un fichier existant. Les ouvertures inconnues restent dans l’historique. Les Elo manquants restent manquants : ils n’empêchent pas les descriptifs, mais les modèles utilisant ces valeurs les excluent.

Un rejet daté crée une rupture : victoire → ligne rejetée → victoire ne devient pas une série de deux victoires. Une date inconnue empêche de placer la ligne ; par prudence, ce compte est exclu des analyses de succession et de séries. Ses parties valides restent décrites. Les dates ex aequo sont ambiguës. Les parties timeout terminées avec résultat exploitable restent conservées. Ces protections ne reconstituent pas des matchs qui n’ont jamais été collectés.

## 5. Les trois exercices descriptifs

Dans `analyse.py`, `statistiques_ouvertures()` fournit effectifs, joueurs, proportions de chaque résultat, score moyen et écart-type. `win.mean()` est un taux de victoire. Le score moyen inclut un demi-point pour une nulle : il n’est pas ce taux. Les taux moyens par joueur donnent un poids égal aux comptes au sein d’une ouverture.

`filtrer_periode()` crée une copie entre début inclus et fin exclue. `statistiques_temporelles()` calcule ensuite les résultats mensuels. Il s’agit d’un sous-échantillon temporel, pas d’une nouvelle collecte indépendante. `series_resultats()` mesure les séries de même résultat avec la même ouverture, dans la chronologie complète du joueur avant sélection. Un nul interrompt une série de victoires ou de défaites. Le maximum dépend de la taille et des bornes de l’historique.

## 6. Répétition, χ² et Fisher

Dans `Analyse_repetition_ouverture.py`, `creer_transitions()` ajoute les colonnes de la partie suivante. `preparer_cadres()` distingue la suivante immédiate, les transitions immédiates de même couleur et la prochaine de même couleur. `taux_apres_victoire()` sélectionne ensuite les transitions dont la partie courante est gagnée.

`tester_table()` construit le tableau répétition/changement × victoire suivante/autre résultat. L’effectif attendu d’une case vaut le total de sa ligne multiplié par celui de sa colonne, divisé par l’effectif total. Le χ² additionne (observé − attendu)² / attendu. Le tableau 2×2 possède un degré de liberté. La fonction affiche les attendus, la valeur p et le V de Cramér. Si une modalité manque, le test est signalé non estimable.

Fisher exact bilatéral complète ce tableau, notamment pour de petits effectifs. Il ne corrige pas la dépendance entre parties d’un joueur et ne constitue pas une analyse multivariable. `tests_repetition()` applique la même comparaison aux trois cadres et corrige leur multiplicité par Holm. Les valeurs p restent exploratoires.

`bootstrap_joueurs()` rééchantillonne des comptes entiers pour estimer l’incertitude de l’écart de taux. Il garde ensemble les transitions d’un même compte. Des adversaires partagés et les choix d’ouverture restent des limites. L’inférence est masquée sous vingt comptes : ce seuil est un garde-fou, pas une garantie.

## 7. Trois régressions lisibles

`preparer_regressions()` réutilise les transitions immédiates. `regressions_lineaires()` forme un même échantillon complet pour les trois cibles : victoire, défaite et nulle suivantes. Les contrôles sont la victoire courante, l’écart Elo suivant pour 100 points, la couleur, la cadence et la famille suivantes, avec la répétition comme variable centrale.

Ces modèles portent sur toutes les transitions exploitables, pas uniquement celles après victoire. Un coefficient de 0,02 représente une association ajustée de deux points de probabilité. Les trois cibles somment à un : les modèles sont complémentaires. Les erreurs-types sont groupées par compte et les trois tests de répétition corrigés par Holm. Les modèles trop petits ou colinéaires sont signalés. Les prédictions hors [0, 1] sont comptées.

Le notebook interprète le signe, la taille et l’incertitude des coefficients. Les ajustements ne suffisent pas à établir une causalité.

## 8. Exécuter, exporter et rédiger

`exporter_tableaux()` conserve les trois exercices. `tracer_resultats()` produit les trois figures. `ecrire_manifeste()` documente versions, bornes et empreinte. `analyser()` rassemble ces tâches dans un parcours court ; le notebook les utilise étape par étape pour montrer les calculs. `Master_file.main()` enchaîne toute la chaîne depuis une source choisie.

`donnees_demo.py` reconstruit une simulation figée de 3 600 lignes et 40 comptes, avec graine 73 et sans avantage propre de répétition. Elle sert à vérifier la chaîne ; ses résultats ne prouvent rien sur les joueurs réels. `executer_notebook.py` lance toutes les cellules avec le Python courant. Les deux notebooks sont identiques, éditables et contiennent leurs sorties. Dans Colab : Fichier → Enregistrer une copie dans Drive.

Commandes centrales :

```bash
python -m pip install -r requirements-lock.txt
python donnees_demo.py --verify
python Master_file.py --demo --debut 2024-01-15 --fin 2024-03-01
python executer_notebook.py
python -m unittest discover -s tests -v
```

Les anciens noms (`config_projet.py`, `Nettoyage_donnees.py`, `analyse_statisitques.py` et les scripts de génération) sont des passerelles de compatibilité. Le code à comprendre et à modifier est dans les fichiers principaux indiqués ici.

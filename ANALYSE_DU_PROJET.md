# Comprendre le complément au projet original

## Le point de départ reste ton projet

Les scripts de découverte des utilisateurs et d’import des parties reprennent ceux de Projet-info-2A-main. Leurs fonctions sont conservées ; seul un exemple de cinq comptes est ajouté entre guillemets. Le Master leur fournit un nouveau dossier Data et une liste de comptes, pour éviter d’écraser une ancienne collecte. Aucun nouveau découpage en de nombreux modules d’analyse n’est ajouté : l’extension est dans Analyse_repetition_ouverture.py.

Le notebook initial de 65 cellules reste la base. Ses sections Hot Hand sont conservées pour la comparaison ; les anciens blocs remplacés restent visibles et désactivés entre des lignes de hashtags. Les anciens commentaires contenant des résultats sont explicitement historiques : ils ne doivent pas être lus comme des résultats de la nouvelle analyse. Le nettoyage partagé corrige l’ordre timestamp/déduplication et garde les nulles.

## Les fichiers et leur rôle

| Fichier | Rôle et changement |
|---|---|
| config_projet.py | Configuration GitHub conservée, création de dossiers uniques, paramètres S3 Hadrien. |
| .env.example | Modèle GitHub conservé ; un vrai .env privé est lu mais jamais publié ni envoyé. |
| Master_file.py | Ancien Master en commentaires, puis un seul pipeline actif sans suppression. Sélection directe des comptes ou découverte originale, complément API, identification, nettoyage, analyse et envoi facultatif. |
| Scripts_generation_data/Creation_Df_openings.py | Ancienne liste manuelle commentée intégralement ; cinq tables Lichess officielles réunies. La sortie openings.parquet reste compatible avec l’import d’origine. Reconnaissance locale par positions sur 5/10 coups. |
| Scripts_generation_data/Import_des_users.py | Fonctions originales conservées. Un exemple entre guillemets montre la sélection de cinq comptes depuis le Master. |
| Scripts_generation_data/Import_une_partie.py | Fonctions originales conservées, même exemple commenté. Le dictionnaire et le chemin de sortie sont fournis par le Master. |
| Scripts_generation_data/Inspect_keys_API.py | Script de diagnostic ; token remplacé par lecture environnementale et opening=true. Ne pas l’importer comme une bibliothèque : il garde son exécution directe d’origine. |
| Nettoyage_donnees.py | Crée une copie propre, retire les doublons/statuts non analysables et conserve les nulles dans la chronologie ; sauvegarde séparée. |
| Stockage_SSPCloud.py | Envoi sous un identifiant unique ; aucune suppression locale ou S3 et aucun .env transmis. |
| Analyse_repetition_ouverture.py | Construction des transitions, taux, χ²/Fisher, bootstrap par compte, logistique ajustée et descriptifs. |
| Analyse_data.ipynb | Rapport initial conservé et complété par VI ; démonstration fictive ou vraies données locales/S3. |
| tests/test_complement.py | Vérifications reproductibles sur petits jeux fictifs et services simulés. |
| References/lichess_openings/... | Cinq TSV officiels figés, sans données personnelles de parties. |

Le doublon Creation_Df_openings.py à la racine n’est pas réintroduit : le script canonique garde son nom d’origine dans Scripts_generation_data, là où le Master l’appelle. Les anciens modules et guides GitHub restent dans le dépôt d’archive, pour ne pas mélanger deux parcours d’analyse dans le dépôt actif.

## 1. Référentiel et identification

Les cinq fichiers officiels a.tsv, b.tsv, c.tsv, d.tsv, e.tsv donnent ECO, nom et PGN. On rejoue les coups avec python-chess pour obtenir listes SAN compatibles et positions. Le référentiel figé livré contient 3865 entrées. Un code ECO peut correspondre à plusieurs variantes : comparer ECO seul ne suffit pas à comparer des ouvertures fines.

Un coup complet correspond à deux demi-coups. La fenêtre de 5 ou 10 coups correspond à 10 ou 20 demi-coups. Le nom retourné est la référence la plus précise atteinte dans cette fenêtre, avec la profondeur réellement reconnue. Une référence très courte donne parfois seulement une famille. Le minimum de cinq coups disponibles n’implique pas que le nom reconnu nécessite lui-même cinq coups. Les variantes nécessitant davantage de coups ne sont pas attribuées trop tôt. Les positions permettent de reconnaître certaines transpositions ; les ambiguïtés de noms sont enregistrées.

L’importeur original garde sa comparaison de préfixes pour la première collecte. Puis le Master récupère les coups par IDs et applique la reconnaissance par position : cette deuxième étape est celle utilisée dans dfs_games.parquet. Les étiquettes API restent dans api_eco et api_opening_name. Cette séparation évite de confondre une classification API de profondeur non imposée et la classification locale limitée aux premiers coups.

## 2. Quelle ligne étudie-t-on ?

Une ligne de parties représente le point de vue d’un compte sur un match. Deux comptes collectés peuvent donc représenter les deux côtés du même match. Distinguer nombre de lignes et nombre de parties uniques.

Une ligne de transitions relie une partie du compte à sa suivante observée. Les colonnes *_next contiennent les informations de cette suivante, après tri chronologique. Exemples : opening_name_next est UNE valeur par ligne ; le DataFrame apres_victoire est un ensemble de lignes dont result vaut Win.

Win → Draw → Win n’est pas une suite de deux victoires : la nulle reste dans l’historique et interrompt la suite. Une ouverture inconnue ne vaut ni répétition ni changement. On construit les décalages avant de sélectionner les ouvertures connues. La dernière partie n’a pas de transition et n’est pas artificiellement ajoutée au groupe « changer ». Les dates identiques sont triées par ID pour être reproductibles ; les transitions de délai nul sont exclues faute d’ordre temporel certain.

Trois cadres sont calculés :

1. Immédiat observé : la prochaine ligne du même compte.
2. Immédiat même couleur : sous-ensemble du précédent dont les couleurs sont identiques.
3. Prochaine même couleur : la prochaine ligne de cette couleur, possiblement après des matchs intermédiaires. Ce cadre ne mesure pas une victoire immédiatement successive.

Les N dernières parties par cadence ne garantissent pas un historique complet toutes cadences : « observée » reste essentiel. Les fenêtres d’analyse historiques de sessions reposent aussi sur les dates de début, pas une mesure exacte des pauses entre fin et début.

## 3. Décrire puis tester la question principale

Parmi les transitions qui commencent par une victoire et dont les deux ouvertures sont connues, comparer les groupes changer/répéter. Pour chacun, afficher nombre de transitions, comptes, victoires suivantes et taux de victoire suivante. Une nulle suivante vaut non-victoire. Le taux est une moyenne du booléen win_next.

H0 : répétition et victoire suivante sont indépendantes dans ce tableau. Le χ² de Pearson compare les effectifs observés aux attendus. Le code retourne statistique, ddl, p, minimum des attendus, garde-fou d’effectifs et V de Cramér. Pour un 2×2, Fisher exact ajoute odds ratio et p bilatérale. Fisher n’est pas un modèle à plusieurs variables.

Les trois cadres sont définis avant les résultats. La correction de Holm est appliquée séparément aux trois p du χ² et aux trois p de Fisher calculables. Cela ne rend pas les observations indépendantes : ces tests groupés restent exploratoires. Le seuil d’effectifs attendus ne vérifie que les effectifs, pas les autres hypothèses.

Le bootstrap rééchantillonne les comptes entiers. Il fournit un intervalle percentile de l’écart de taux répéter − changer lorsque suffisamment de comptes contribuent. Le choix de 20 comptes est un garde-fou pédagogique, pas une garantie. Les matchs avec adversaires partagés et les deux côtés d’une même partie ne sont pas rendus indépendants par ce regroupement.

## 4. Régression ajustée et portée de son résultat

La régression principale utilise les transitions immédiates après victoire :

victoire suivante ~ répétition + écart Elo de la suivante / 100 + couleur suivante + cadence suivante.

Le modèle logistique convient à cette cible binaire et prolonge la logistique du notebook original. Les erreurs-types sont regroupées par compte. Les effectifs, les classes, le rang de la matrice, la convergence et les incertitudes sont contrôlés. Un modèle non estimable affiche sa raison plutôt que des coefficients trompeurs. La variation ratingDiff après le match ne remplace jamais l’écart Elo avant la partie.

Un coefficient de répétition positif représente une association ajustée aux contrôles du modèle. Son exponentielle est un odds ratio, pas un écart de probabilité en pourcentage. Ce modèle étudie la répétition ; il ne classe pas les ouvertures par effet causal. Les descriptifs famille/couleur sont fournis, mais l’ajout de nombreuses familles à la régression demanderait plus de données et un regroupement des catégories rares.

Avec cinq comptes choisis, les statistiques descriptives fonctionnent, mais le bootstrap et la régression groupée sont volontairement limités. On ne doit pas promettre une inférence fiable en comptant simplement davantage de lignes issues de ces cinq comptes.

## 5. Les descriptifs à lire

statistiques_descriptives.csv : n, mean, median, std, min, max pour classement, classement adverse, écart Elo et score. std utilise l’écart-type d’échantillon de pandas. Le score 1/0,5/0 garde les nulles ; son espérance diffère du taux de victoire.

Les graphiques restent simples : histogramme du classement, barres Win/Draw/Loss et taux de victoire après répétition/changement. Les tables par ouverture et couleur indiquent les effectifs avant tout classement interprétatif. Une moyenne sur un petit groupe est fragile.

## 6. Ce qui reste volontairement inchangé ou limité

Les importeurs d’origine sont conservés à ta demande. Ils gardent leurs limitations : absence de timeout sur certaines requêtes, reprise 429 trop courte, variable r non initialisée si toutes les tentatives lèvent une exception, erreurs de lignes masquées et exploration d’un réseau non uniforme. Le nouveau complément API respecte une requête à la fois, timeout et pause 429 ; il ne corrige pas rétroactivement les requêtes de l’importeur. Pour une future étape, quelques corrections localisées suffiraient, sous réserve de ton accord pour modifier ces fichiers.

Le notebook conserve les analyses Hot Hand comme contexte ; leurs tests et modèles historiques nominaux restent exploratoires et leurs anciens commentaires numériques ne sont pas recalculés automatiquement. La partie VI est le parcours principal pour la nouvelle question. Le contrôle des sessions et le test de permutation historiques ne prouvent pas, à eux seuls, un rôle causal de l’ouverture.

## 7. Conservation et vérification

Le Master crée un nouvel identifiant par collecte. Les données brutes sont écrites avant le complément API ; un échec laisse donc la base disponible. Les sorties nettoyées sont distinctes. L’envoi S3 est explicite et n’efface aucun objet. Une réservation conditionnelle empêche de réutiliser le même identifiant distant. Les vrais .env ne sont ni dans Git, ni dans les fichiers envoyés.

Les tests simulent API et S3 : ils vérifient le logiciel, pas les droits réels. Le notebook est vérifié sur l’exemple DEMO annoncé. Aucune nouvelle conclusion empirique n’est affirmée sur tes données réelles lors de cette livraison.

## Sources officielles

- https://github.com/lichess-org/chess-openings
- https://github.com/lichess-org/api/blob/master/doc/specs/tags/games/api-games-export-_ids.yaml
- https://lichess.org/page/api-tips

## Token dans l’ancien état GitHub

Le contrôle de l’archive a trouvé un token en clair dans son script de diagnostic. Il est retiré de la version courante du dépôt d’archive et du ZIP, comme du nouveau projet. L’historique antérieur est conservé à ta demande et contient encore cette valeur ; la révoquer si elle est active. Aucun token n’a été testé ou utilisé pendant cette livraison.

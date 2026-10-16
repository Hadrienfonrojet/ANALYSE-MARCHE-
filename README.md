# Hot Hand dans les parties d’échecs en ligne  
*Projet de data science – Python*

## 1) Pitch & contexte

Le phénomène de **Hot Hand** désigne l’idée selon laquelle une série récente de succès
augmente la probabilité de succès futurs. Bien que longtemps débattu en psychologie et
en économie comportementale, il a été largement étudié dans des contextes sportifs
(basket-ball, baseball, tennis), mais beaucoup plus rarement dans des jeux **purement
stratégiques** comme les échecs.

Les échecs en ligne constituent pourtant un terrain d’étude particulièrement pertinent :
- le résultat de chaque partie est clairement défini (victoire/défaite/nulle),
- les joueurs disputent souvent plusieurs parties consécutives,
- de nombreuses variables observables sont disponibles (niveau Elo, cadence, ouverture).

Ce projet exploite des données issues de la plateforme **Lichess** afin d’évaluer
empiriquement l’existence et la nature d’un effet *Hot Hand* dans les parties d’échecs en
ligne.  
L’objectif n’est pas d’établir une causalité psychologique stricte, mais de déterminer
si les performances récentes sont associées à une probabilité accrue de succès à court
terme, et sous quelles conditions.

---

## 2) Problématique

> **Une victoire récente augmente-t-elle la probabilité de gagner la partie suivante
dans les échecs en ligne ?**

Plus précisément, le projet cherche à répondre aux questions suivantes :
- Existe-t-il une dépendance statistique entre résultats consécutifs ?
- Cette dépendance est-elle locale dans le temps (intra-session) ?
- Les résultats récents exercent-ils un effet cumulatif (mémoire > 1 match) ?
- Ces effets persistent-ils après contrôle du niveau du joueur et de facteurs
  structurels ?
- Les séries observées sont-elles compatibles avec un simple modèle aléatoire ?

---

## 3) Comment utiliser ce projet

### 3.1 Installer les packages

```bash
pip install numpy pandas matplotlib seaborn scipy statsmodels s3fs
```
## 3.2 Variables d’environnement

Deux configurations sont possibles selon l’usage.

### a) Exécuter uniquement le notebook d’analyse (recommandé)

Les données nécessaires à l’analyse sont déjà stockées sur un espace S3.
Créer un fichier `.env` avec :

```env
AWS_S3_ENDPOINT=minio.lab.sspcloud.fr
```
Aucune clé API Lichess n’est requise dans ce cas.

### b) Regénérer les données depuis l'API Lichess (optionnel)
Il faut ajouter dans le `.env` 
```env
jeton_api=VOTRE_TOKEN_LICHESS
AWS_S3_ENDPOINT=minio.lab.sspcloud.fr
```
Il faut dans ce cas générer une clé d'API Lichess, possible directement sur le site officiel avec un compte gratuit.

## 3.3 Quels fichiers exécuter ?

- `Masterfile`
Script permettant d’interroger l’API Lichess et de constituer les jeux de données (optionnel).

- `Analyse_data.ipynb`
Notebook principal contenant l’ensemble des analyses statistiques et graphiques.
Il peut être exécuté cellule par cellule et se lit également comme un rapport.

## 4) Données utilisées 

Les données proviennent de parties jouées sur **Lichess**, incluant notamment :

- résultats des parties (victoire/défaite),
- cadence de jeu (*bullet*, *blitz*, *rapid*, *classical*),
- niveau Elo des joueurs,
- horodatage des parties,
- ouvertures jouées.

Le jeu de données utilisé dans le notebook couvre **un large spectre de niveaux Elo**. 
Il a été généré en exécutant le **Masterfile** avec comme paramètres trista35 comme pseudo source, 500 joueurs et 150 parties par joueur. 


## 5) Notions d'échecs utiles 
Pour comprendre pleinement le projet, il est utile de connaître :

- **Elo** : système de classement mesurant la force relative d’un joueur ;
- **Cadences** :
  - *bullet* : parties très rapides,
  - *blitz* : parties rapides,
  - *rapid* : parties intermédiaires,
  - *classical* : parties longues ;
- **Ouverture** : séquence initiale standardisée de coups ;
- **Session de jeu** : suite de parties jouées sans longue interruption  
  (ici : pause ≤ 30 minutes).

Aucune connaissance avancée en théorie des échecs n’est requise.

## 6) Méthodologie et analyses

Le projet repose sur plusieurs niveaux d’analyse :

- tests d’indépendance entre résultats consécutifs (χ²),
- analyses conditionnelles par format et par niveau,
- filtrage temporel et définition de sessions de jeu,
- modèles markoviens (ordre 1 vs ordre 2),
- régressions logistiques avec contrôles (niveau, couleur),
- simulations par permutation (*null model*).

L’approche est volontairement progressive, allant du descriptif vers des tests plus
structurels.

---

## 7) Limitations

- L’analyse est **observationnelle** : elle ne permet pas d’identifier une causalité
  psychologique stricte.
- L’Elo de l’adversaire n’est pas toujours disponible, ce qui empêche de calculer un
  score attendu exact à chaque partie.
- Les parties nulles sont exclues pour simplifier l’analyse, ce qui peut légèrement
  modifier certaines dynamiques de séries.
- La définition d’une session repose sur un seuil (30 minutes) : même si les résultats
  sont généralement robustes à des variations raisonnables, ce choix reste conventionnel.

---

## 8) Pistes d’amélioration

Plusieurs extensions seraient naturelles :

- intégrer systématiquement l’Elo de l’adversaire et le score attendu,
- inclure la qualité des coups via un moteur (*Stockfish*),
- distinguer parties amicales et tournois,
- modéliser explicitement la durée des séries (modèles de survie),
- tester la robustesse sur d’autres périodes, échantillons ou plateformes.


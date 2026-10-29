# Étude ENSAE / Lichess : choix, répétition et efficacité des ouvertures

## Problématique
Dans quelle mesure le choix et la répétition des ouvertures sont-ils associés à la performance des joueurs en ligne, **après contrôle de l'écart Elo, de la couleur et de la cadence** ? Deux mécanismes : performance conditionnelle de l'ouverture et décision de la rejouer après le résultat précédent.

## Projet historique : jamais écrasé
`Master_file.py`, `Creation_Df_openings.py`, `Creation_Df_openings(1).py`, `Import_des_users.py`, `Import_une_partie.py`, `Analyse_data.ipynb` (65 cellules originales), `README.md` et `requirements.txt` sont conservés. Nouveaux modules complémentaires : `Pipeline_ouvertures.py`, `Collecte_enrichie.py`, `Creation_openings_complet.py`, `Nettoyage_donnees.py`, `Analyse_ouvertures.py`, `Stockage_SSPCloud.py`, `config_projet.py`. La dernière section du notebook comporte les nouveaux résultats.

## Exécution (depuis la racine du dossier)
```bash
python3 -m pip install -r requirements.txt
cp .env.example .env
# Modifier .env pour y insérer les CINQ vrais pseudos, et les secrets nécessaires.
python3 -m Scripts_generation_data.Creation_openings_complet
python3 Pipeline_ouvertures.py --users-per-seed 30 --games-per-format 60 --upload
jupyter notebook Analyse_data.ipynb
```
Si les données sont déjà présentes : `python3 Pipeline_ouvertures.py --skip-collect`. Pour téléverser après coup : `python3 Stockage_SSPCloud.py`.

La documentation et le code utilisateur disponibles ne permettent d'identifier avec certitude que `yuuki-asuna` parmi les cinq comptes souhaités. Remplacer `PSEUDO_2` à `PSEUDO_5` dans `.env`. Choisir volontairement cinq points de départ couvrant plusieurs niveaux Elo ; **vérifier ensuite dans les données** que chaque tranche est réellement représentée. La marche par adversaires n'assure pas un échantillon aléatoire ni une couverture uniforme.

## Données et classement
Le dictionnaire complet officiel des ouvertures est issu des cinq fichiers TSV du dépôt `lichess-org/chess-openings` : `eco`, `name`, `pgn`, `family`, `eco_group`. L'ancienne liste manuelle reste intacte. Pour chaque couple (utilisateur, partie) le programme collecte ID, horodatage, couleur, statut, victoire/nulle/défaite, Elo des deux joueurs, écart Elo, cadence, code ECO et famille d'ouverture, historique de répétition **à couleur identique**. Quand Lichess ne fournit pas d'ouverture, le champ reste « Inconnue » et n'est pas inventé à partir des premiers coups.

**Unités statistiques :** `game_id` = partie unique ; (`user_id`, `game_id`) = observation du point de vue d'un joueur. Une partie peut apparaître deux fois si ses deux protagonistes figurent dans la collecte. Les régressions regroupent les erreurs-types par `user_id`, mais une dépendance résiduelle par `game_id` peut subsister. Pour tester les effets des Blancs et des Noirs, une famille d'ouverture décrit une position créée conjointement et pas une décision unilatérale. Les doublons du même point de vue sont éliminés. Les jeux sont datés et classés **avant** calcul de l'expérience et des variables décalées (aucune fuite des résultats futurs).

## Approche statistique
1. Descriptifs : nombre de joueurs, Elo, fréquence et taux de victoire/nulle par ouverture/cadence/couleur/segment Elo.
2. χ² d'indépendance : `result × opening_group`, `result × color`, `result × format_partie`, `result × elo_band`, `result × seed_origin`, par couleur, cadence et Elo ; puis `résultat précédent × répétition` et `répétition × résultat actuel`. Calcul de V de Cramér, contrôle des effectifs théoriques et FDR Benjamini–Hochberg.
3. Régressions logistiques de **victoire** : M0 couleur ; M1 ajoute différence Elo ; M2 cadence ; M3 ouvertures ; M4 logarithme de l'expérience de cette ouverture ; M5 interaction expérience × couleur. Même échantillon sur les six modèles, AIC/BIC/LR/pseudo-R², coefficients, OR, IC 95 %, erreurs-types cluster joueur.
4. Régressions de **répétition** : R0 victoire/nulle précédente ; R1 ajoute différence Elo ; R2 couleur et cadence ; R3 expérience antérieure.
5. Régressions de **performance en cas de répétition** : P0 répétition ; P1 couleur ; P2 Elo ; P3 cadence ; P4 famille et expérience.
6. Analyses de sensibilité : restriction aux parties décisives, score attendu Elo (formule logistique standard) comparé au score effectivement réalisé, courbe d'expérience et distributions par segments Elo.

### Interpréter le χ²
- H0 : indépendance des modalités ; faible p ajustée = incompatibilité avec H0 dans l'échantillon, **pas une causalité**.
- `valid=False` ou `expected_lt5 > 0` signale des cellules trop rares ; regrouper des catégories ou appliquer d'autres méthodes avant de conclure.
- V de Cramér reflète la force de l'association et ne doit pas être confondu avec la significativité.
- Multiplicité : `p_fdr_bh` contrôle le taux attendu de fausses découvertes parmi les rejets, sous les conditions usuelles de la procédure.

### Interpréter la régression
Un odds ratio (OR) supérieur à 1 indique des **odds** plus élevées à covariables constantes, pas une hausse directe des probabilités du même pourcentage. En présence d'interactions, les effets ne sont pas constants. La comparaison des modèles ne démontre pas l'effet causal d'une ouverture : niveau non observé, adversaires, préparation, choix et sélection restent des confusions possibles. Pour une causalité, prévoir un protocole séparé (assignation ou quasi-expérience crédible).

## SSP Cloud : pourquoi et comment
Le SSP Cloud fournit un espace de stockage persistant de type objet **MinIO compatible S3**, distinct de la mémoire volatile des sessions d'exécution. On peut y partager ou recharger des Parquet sans retélécharger des milliers de parties et faciliter la reproductibilité du notebook. Le script utilise Boto3 avec les variables d'environnement SSP Cloud ou le fichier `.env` local et stocke sous `s3://<S3_BUCKET>/<S3_PREFIX>/Data/` et `.../Resultats/`. Par défaut le bucket historique **hadrien2703**, préfixe isolé **diffusion/projet_ouvertures** ; ces paramètres restent modifiables et nécessitent des droits d'écriture effectifs. L'upload n'efface **aucun** objet historique et ne demande **pas** d'accès public automatique. Éviter de publier les identifiants, secrets et données privées.

Dans un notebook SSP Cloud, les identifiants MinIO sont souvent préconfigurés dans l'environnement. Pour récupérer le fichier nettoyé :
```python
from Stockage_SSPCloud import download_file
chemin = download_file('games_clean.parquet')
import pandas as pd
df = pd.read_parquet(chemin)
```
Depuis un poste local, renseigner `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, et éventuellement `AWS_SESSION_TOKEN` et `AWS_S3_ENDPOINT`. **Ne jamais pousser `.env` dans Git.** Si le bucket n'appartient pas à l'utilisateur ou si les droits expirent, les opérations échouent sans que le programme crée un bucket à son insu.

## Fichiers de sortie
`Data/users_list_stratified.parquet` ; `Data/openings_complet.parquet` ; `Data/games_enrichies_raw.parquet` ; `Data/games_clean.parquet` ; `Data/players_openings.parquet` ; `Resultats/tests_chi2.csv` ; `Resultats/description_*.csv` ; `Resultats/modeles_*_comparaison.csv` et `*_coefficients.csv` ; `Resultats/surperformance_elo.csv`, `experience_progression.csv`, `experience_score.png`, `qualite_donnees.csv`, `LECTURE_RESULTATS.md`.

## Source méthodologique
Documentation API : https://lichess-org.github.io/api/ ; dictionnaire : https://github.com/lichess-org/chess-openings ; stockage : https://docs.sspcloud.fr/content/storage.html . Les résultats quantitatifs ne sont pas fournis avant l'exécution d'une collecte réelle. Le notebook original Hot Hand, ainsi que ses commentaires sur une autre base, reste un document historique distinct.

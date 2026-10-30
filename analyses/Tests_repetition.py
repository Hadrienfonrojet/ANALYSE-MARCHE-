"""Associations exploratoires et définitions temporelles de la répétition.

Les valeurs p du chi2 supposent des observations indépendantes. Cette hypothèse
n'est pas garantie dans un panel de parties ; les résultats sont exploratoires.
"""

from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, fisher_exact
from statsmodels.stats.multitest import multipletests


def add_transitions(frame):
    """Créer des COLONNES d'historique dans un DataFrame trié.

    Une ligne reste une observation joueur/partie. groupby ne fabrique pas
    une base distincte par joueur : il délimite les groupes pour shift(1).
    Une ouverture inconnue ne vaut ni répétition ni changement.
    """
    d = frame.sort_values(["user_id", "timestamp", "game_id"]).copy()
    ## On crée un nouveau DataFrame d, sans modifier le DataFrame fourni.
    d["known_opening"] = d["opening_family"].notna() & ~d["opening_family"].isin(
        ["Inconnue", "", "UNKNOWN"]
    )
    ## La colonne ci-dessus indique si l'ouverture actuelle est connue.

    ## Partie 1A - Lire la partie précédente du même joueur, toute couleur
    by_user = d.groupby("user_id", observed=True)
    d["prev_game_all"] = by_user["game_id"].shift(1)
    d["prev_opening_all"] = by_user["opening_family"].shift(1)
    ## On crée UNE COLONNE : à chaque ligne, la famille de la précédente
    ## partie observée de ce joueur. Ce n'est pas une liste de ses parties.
    d["prev_result_all"] = by_user["result"].shift(1)
    valid_all = d["known_opening"] & by_user["known_opening"].shift(1).eq(True)
    d["repeat_all"] = np.where(
        valid_all, d["opening_family"].eq(d["prev_opening_all"]).astype(float), np.nan
    )
    ## 1 = même famille ; 0 = changement ; NaN = comparaison impossible.

    ## Partie 1B - Lire la précédente partie de même couleur du même joueur
    by_user_color = d.groupby(["user_id", "color"], observed=True)
    d["prev_game_same_color"] = by_user_color["game_id"].shift(1)
    d["prev_opening_same_color"] = by_user_color["opening_family"].shift(1)
    ## On crée UNE COLONNE contenant l'ouverture de la précédente partie
    ## du même joueur AVEC LA MÊME COULEUR. Des parties de l'autre couleur
    ## peuvent s'intercaler. La première partie de chaque groupe vaut NaN.
    d["prev_result_same_color"] = by_user_color["result"].shift(1)
    valid_color = d["known_opening"] & by_user_color["known_opening"].shift(1).eq(True)
    d["repeat_same_color"] = np.where(
        valid_color,
        d["opening_family"].eq(d["prev_opening_same_color"]).astype(float),
        np.nan,
    )

    ## Partie 1C - La couleur elle-même est-elle répétée ?
    d["prev_color"] = by_user["color"].shift(1)
    d["same_color_consecutive"] = np.where(
        d["prev_color"].notna(), d["color"].eq(d["prev_color"]).astype(float), np.nan
    )
    ## Cela ne signifie pas que l'ouverture a été répétée.
    return d


def chi2_details(frame, a, b, label, min_expected=5):
    """Fonction du chi carré : calculer puis expliquer chaque résultat.

    H0 : les variables a et b sont indépendantes. H1 : elles sont associées.
    On compte les observations, puis on compare aux attentes sous H0 :
        Eij = total_ligne_i * total_colonne_j / n
        chi2 = somme((Oij - Eij)**2 / Eij)
        ddl = (nombre_lignes - 1) * (nombre_colonnes - 1)
    La statistique suit approximativement une loi du chi carré sous H0,
    avec les hypothèses du test et des effectifs suffisants.
    La valeur p n'est PAS la probabilité que H0 soit vraie.
    """
    complete = frame[[a, b]].dropna()  ## Nouveau DataFrame des deux colonnes connues.
    observed = pd.crosstab(complete[a], complete[b])  ## Tableau d'EFFECTIFS entiers.
    observed = observed.loc[observed.sum(axis=1).gt(0), observed.sum(axis=0).gt(0)]
    n = int(observed.to_numpy().sum())
    result = dict(
        test=label,
        n=n,
        chi2=np.nan,
        ddl=np.nan,
        p=np.nan,
        cramer_v=np.nan,
        expected_lt5=np.nan,
        min_expected=np.nan,
        valid=False,
        independence_assumed=True,
        interpretation="exploratoire",
        fisher_p=np.nan,
        status="tableau insuffisant",
    )
    expected = pd.DataFrame(index=observed.index, columns=observed.columns, dtype=float)
    residuals = expected.copy()
    if min(observed.shape, default=0) < 2:
        return result, observed, expected, residuals

    ## Partie 2A - Le calcul de Pearson, sans correction de Yates
    stat, p, ddl, exp = chi2_contingency(observed, correction=False)
    expected = pd.DataFrame(exp, index=observed.index, columns=observed.columns)
    residuals = (observed - expected) / np.sqrt(expected)
    ## Les résidus décrivent les cases qui s'écartent des attentes, sans test par case.

    ## Partie 2B - Taille de l'association et diagnostic des petits effectifs
    v = np.sqrt(stat / (n * min(observed.shape[0] - 1, observed.shape[1] - 1)))
    enough = bool((exp >= min_expected).all())
    result.update(
        chi2=float(stat),
        p=float(p),
        ddl=int(ddl),
        cramer_v=float(v),
        expected_lt5=int((exp < min_expected).sum()),
        min_expected=float(exp.min()),
        valid=enough,
        status="effectifs suffisants" if enough else "effectifs faibles",
    )
    ## valid valide seulement les effectifs attendus, PAS l'indépendance des parties.
    if observed.shape == (2, 2):
        result["fisher_p"] = float(
            fisher_exact(observed.to_numpy(), alternative="two-sided")[1]
        )
    return result, observed, expected, residuals


## Partie 3 - Corriger puis appliquer les tests du chi carré


def correct_multiple_tests(results):
    """Holm contrôle le risque familial sans exiger des tests indépendants.

    Cela ne répare pas les valeurs p invalides dues aux observations dépendantes.
    """
    out = results.copy()
    out["p_holm"] = np.nan
    usable = out["p"].notna() & out["valid"].fillna(False)
    if usable.any():
        out.loc[usable, "p_holm"] = multipletests(out.loc[usable, "p"], method="holm")[
            1
        ]
    return out


def repetition_scenarios(frame):
    """Définir les populations avant de lancer les tests."""
    d = add_transitions(frame)
    return {
        "toutes_couleurs": (d, "repeat_all", "prev_result_all", "prev_game_all"),
        "precedente_meme_couleur": (
            d,
            "repeat_same_color",
            "prev_result_same_color",
            "prev_game_same_color",
        ),
        "consecutives_meme_couleur": (
            d[d["same_color_consecutive"].eq(1)],
            "repeat_all",
            "prev_result_all",
            "prev_game_all",
        ),
        "consecutives_couleur_changee": (
            d[d["same_color_consecutive"].eq(0)],
            "repeat_all",
            "prev_result_all",
            "prev_game_all",
        ),
    }


## Compléments facultatifs - Vérifier la sensibilité des résultats


def independent_transition_sample(frame, previous_game):
    """Sensibilité : au plus une transition par joueur et aucun ID de partie partagé.

    Ce filtrage ne supprime pas les adversaires communs ou les autres dépendances.
    """
    used_games, used_users, chosen = set(), set(), []
    ordered = frame.dropna(subset=[previous_game]).sort_values(
        ["timestamp", "game_id", "user_id"]
    )
    for idx, row in ordered.iterrows():
        games = {str(row["game_id"]), str(row[previous_game])}
        if row["user_id"] not in used_users and not games & used_games:
            chosen.append(idx)
            used_games.update(games)
            used_users.add(row["user_id"])
    return frame.loc[chosen].copy()


def player_bootstrap(frame, repeat_column, n_boot=1000, seed=42):
    """IC descriptif du contraste de score, pondération égale des joueurs éligibles.

    Rééchantillonnage des joueurs ayant répétition ET changement ; ni causalité,
    ni correction complète de la dépendance entre adversaires communs.
    """
    valid = frame.dropna(subset=[repeat_column, "score"])
    means = (
        valid.groupby(["user_id", repeat_column], observed=True)["score"]
        .mean()
        .unstack()
    )
    if 0.0 not in means or 1.0 not in means:
        return dict(players=0, difference=np.nan, ci_low=np.nan, ci_high=np.nan)
    delta = (means[1.0] - means[0.0]).dropna().to_numpy()
    if len(delta) < 2:
        return dict(
            players=len(delta),
            difference=float(delta.mean()) if len(delta) else np.nan,
            ci_low=np.nan,
            ci_high=np.nan,
        )
    rng = np.random.default_rng(seed)
    draws = np.array(
        [rng.choice(delta, size=len(delta), replace=True).mean() for _ in range(n_boot)]
    )
    return dict(
        players=len(delta),
        difference=float(delta.mean()),
        ci_low=float(np.quantile(draws, 0.025)),
        ci_high=float(np.quantile(draws, 0.975)),
    )


## Partie 3 - Applications concrètes et sorties lisibles


def run_repetition_tests(
    frame, output_dir=None, stratify=True, include_sensitivity=True
):
    """Partie 3 : appliquer le chi carré aux questions annoncées.

    1. Résultat précédent × répétition : rejoue-t-on plus après certains résultats ?
    2. Répétition × résultat courant : les résultats diffèrent-ils selon répétition ?
    Quatre définitions séparent les couleurs. Deux questions finales portent
    sur la répétition de couleur elle-même. Les compléments restent activables
    avec stratify et include_sensitivity ; le parcours principal les désactive.
    """
    records, tables, rates, boot = [], {}, [], []
    scenarios = repetition_scenarios(frame)

    def run(part, a, b, name):
        record, observed, expected, residuals = chi2_details(part, a, b, name)
        records.append(record)
        tables[name] = (observed, expected, residuals)

    for name, (part, repeat, previous, previous_game) in scenarios.items():
        eligible = part.dropna(subset=[repeat, previous, "result"])
        run(eligible, previous, repeat, name + "__resultat_precedent_repetition")
        run(eligible, repeat, "result", name + "__repetition_resultat_courant")
        rates.append(
            dict(
                scenario=name,
                transitions=len(eligible),
                players=eligible["user_id"].nunique(),
                repeat_rate=float(eligible[repeat].mean()) if len(eligible) else np.nan,
            )
        )
        boot.append(dict(scenario=name, **player_bootstrap(eligible, repeat)))
        if include_sensitivity:
            sensitivity = independent_transition_sample(eligible, previous_game)
            run(sensitivity, repeat, "result", name + "__sensibilite_une_transition")
        for dim in (["color", "format_partie", "elo_band"] if stratify else []):
            for value, subset in eligible.groupby(dim, observed=True):
                run(subset, repeat, "result", name + "__" + dim + "_" + str(value))
    d = add_transitions(frame)
    run(d, "same_color_consecutive", "result", "couleur_repetee__resultat_courant")
    run(d, "same_color_consecutive", "repeat_all", "couleur_repetee__ouverture_repetee")
    results = correct_multiple_tests(pd.DataFrame(records))
    rates, boot = pd.DataFrame(rates), pd.DataFrame(boot)
    if output_dir is not None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        results.to_csv(out / "tests_repetition_chi2.csv", index=False)
        rates.to_csv(out / "taux_repetition.csv", index=False)
        boot.to_csv(out / "bootstrap_joueurs.csv", index=False)
        for i, (name, values) in enumerate(tables.items()):
            for kind, tab in zip(["observes", "attendus", "residus"], values):
                tab.to_csv(out / f"table_{i:03d}_{kind}.csv")
        pd.DataFrame({"table_id": range(len(tables)), "test": list(tables)}).to_csv(
            out / "index_tables.csv", index=False
        )
    return results, tables, rates, boot


## Partie 4 - Test exact de Fisher, distinct du test F de régression


def fisher_details(frame, a, b, label):
    """Comparer deux variables à deux catégories dans une table 2 × 2.

    H0 : odds ratio de population égal à 1 dans un modèle à marges fixées.
    Le calcul exact repose sur une loi hypergéométrique. Il est utile quand
    les effectifs du chi carré sont petits ; il ne corrige pas la dépendance
    entre parties. Ce test ne traite pas plusieurs covariables de régression.
    """
    table = pd.crosstab(frame[a], frame[b])
    table = table.loc[table.sum(axis=1).gt(0), table.sum(axis=0).gt(0)]
    result = dict(
        test=label,
        n=int(table.to_numpy().sum()),
        odds_ratio=np.nan,
        p=np.nan,
        p_holm=np.nan,
        statut="tableau non 2x2",
    )
    if table.shape != (2, 2):
        return result, table
    odds, p_value = fisher_exact(table.to_numpy(), alternative="two-sided")
    result.update(odds_ratio=float(odds), p=float(p_value), statut="exploratoire")
    return result, table


def run_fisher_tests(frame, output_dir=None):
    """Appliquer Fisher en annonçant le regroupement victoire / non-victoire.

    Les défaites et les nulles sont regroupées dans non-victoire : ce n'est
    pas la même question que le chi carré à trois catégories de résultats.
    Les catégories sont triées : 0=changement/non-victoire, 1=répétition/victoire.
    Pour répétition × victoire, OR compare les odds de victoire en répétition
    à celles en changement. La correction de Holm porte sur ces quatre tests.
    """
    data = add_transitions(frame)
    data["win"] = data["result"].eq("Win").astype(int)
    records, tables = [], {}
    for suffix in ["all", "same_color"]:
        repeat = "repeat_" + suffix
        previous = "prev_result_" + suffix
        part = data.dropna(subset=[repeat, previous]).copy()
        part["previous_win"] = part[previous].eq("Win").astype(int)
        for a, b, question in [
            (repeat, "win", suffix + "__repetition_victoire"),
            ("previous_win", repeat, suffix + "__victoire_precedente_repetition"),
        ]:
            record, table = fisher_details(part, a, b, question)
            records.append(record)
            tables[question] = table
    results = pd.DataFrame(records)
    usable = results["p"].notna()
    if usable.any():
        results.loc[usable, "p_holm"] = multipletests(
            results.loc[usable, "p"], method="holm"
        )[1]
    if output_dir is not None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        results.to_csv(out / "tests_fisher_exact.csv", index=False)
        for name, table in tables.items():
            table.to_csv(out / (name + "_observes.csv"))
    return results, tables

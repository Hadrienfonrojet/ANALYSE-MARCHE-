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
    """Comparer l'ouverture à la partie précédente, puis à la précédente de même couleur.

    Une ouverture inconnue ne constitue jamais une répétition ni un changement.
    L'historique porte sur l'échantillon collecté, pas sur toutes les parties Lichess.
    """
    d = frame.sort_values(['user_id', 'timestamp', 'game_id']).copy()
    known = d['opening_family'].notna() & ~d['opening_family'].isin(['Inconnue', '', 'UNKNOWN'])
    d['known_opening'] = known
    for suffix, keys in [('all', ['user_id']), ('same_color', ['user_id', 'color'])]:
        grouped = d.groupby(keys, observed=True)
        d['prev_game_' + suffix] = grouped['game_id'].shift()
        d['prev_opening_' + suffix] = grouped['opening_family'].shift()
        d['prev_result_' + suffix] = grouped['result'].shift()
        previous_known = grouped['known_opening'].shift().eq(True)
        valid = known & previous_known
        d['repeat_' + suffix] = np.where(
            valid, d['opening_family'].eq(d['prev_opening_' + suffix]).astype(float), np.nan)
    grouped = d.groupby('user_id', observed=True)
    d['prev_color'] = grouped['color'].shift()
    d['same_color_consecutive'] = np.where(d['prev_color'].notna(),
        d['color'].eq(d['prev_color']).astype(float), np.nan)
    return d


def chi2_details(frame, a, b, label, min_expected=5):
    """Test de Pearson sans correction de Yates ; tableaux et diagnostic explicites."""
    complete = frame[[a, b]].dropna()
    observed = pd.crosstab(complete[a], complete[b])
    observed = observed.loc[observed.sum(axis=1).gt(0), observed.sum(axis=0).gt(0)]
    n = int(observed.to_numpy().sum())
    result = dict(test=label, n=n, chi2=np.nan, ddl=np.nan, p=np.nan,
                  cramer_v=np.nan, expected_lt5=np.nan, min_expected=np.nan,
                  valid=False, independence_assumed=True, interpretation='exploratoire',
                  fisher_p=np.nan, status='tableau insuffisant')
    expected = pd.DataFrame(index=observed.index, columns=observed.columns, dtype=float)
    residuals = expected.copy()
    if min(observed.shape, default=0) < 2:
        return result, observed, expected, residuals
    stat, p, ddl, exp = chi2_contingency(observed, correction=False)
    expected = pd.DataFrame(exp, index=observed.index, columns=observed.columns)
    residuals = (observed - expected) / np.sqrt(expected)
    result.update(chi2=float(stat), p=float(p), ddl=int(ddl),
        cramer_v=float(np.sqrt(stat / (n * min(observed.shape[0]-1, observed.shape[1]-1)))),
        expected_lt5=int((exp < min_expected).sum()), min_expected=float(exp.min()),
        valid=bool((exp >= min_expected).all()),
        status='effectifs suffisants' if (exp >= min_expected).all() else 'effectifs faibles')
    if observed.shape == (2, 2):
        result['fisher_p'] = float(fisher_exact(observed.to_numpy())[1])
    return result, observed, expected, residuals


def correct_multiple_tests(results):
    """Holm contrôle le risque familial sans exiger des tests indépendants.

    Cela ne répare pas les valeurs p invalides dues aux observations dépendantes.
    """
    out = results.copy()
    out['p_holm'] = np.nan
    usable = out['p'].notna() & out['valid'].fillna(False)
    if usable.any():
        out.loc[usable, 'p_holm'] = multipletests(out.loc[usable, 'p'], method='holm')[1]
    return out


def repetition_scenarios(frame):
    """Définir les populations avant de lancer les tests."""
    d = add_transitions(frame)
    return {
        'toutes_couleurs': (d, 'repeat_all', 'prev_result_all', 'prev_game_all'),
        'precedente_meme_couleur': (d, 'repeat_same_color', 'prev_result_same_color', 'prev_game_same_color'),
        'consecutives_meme_couleur': (d[d['same_color_consecutive'].eq(1)], 'repeat_all', 'prev_result_all', 'prev_game_all'),
        'consecutives_couleur_changee': (d[d['same_color_consecutive'].eq(0)], 'repeat_all', 'prev_result_all', 'prev_game_all'),
    }


def independent_transition_sample(frame, previous_game):
    """Sensibilité : au plus une transition par joueur et aucun ID de partie partagé.

    Ce filtrage ne supprime pas les adversaires communs ou les autres dépendances.
    """
    used_games, used_users, chosen = set(), set(), []
    ordered = frame.dropna(subset=[previous_game]).sort_values(['timestamp', 'game_id', 'user_id'])
    for idx, row in ordered.iterrows():
        games = {str(row['game_id']), str(row[previous_game])}
        if row['user_id'] not in used_users and not games & used_games:
            chosen.append(idx)
            used_games.update(games)
            used_users.add(row['user_id'])
    return frame.loc[chosen].copy()


def player_bootstrap(frame, repeat_column, n_boot=1000, seed=42):
    """IC descriptif du contraste de score, pondération égale des joueurs éligibles.

    Rééchantillonnage des joueurs ayant répétition ET changement ; ni causalité,
    ni correction complète de la dépendance entre adversaires communs.
    """
    valid = frame.dropna(subset=[repeat_column, 'score'])
    means = valid.groupby(['user_id', repeat_column], observed=True)['score'].mean().unstack()
    if 0.0 not in means or 1.0 not in means:
        return dict(players=0, difference=np.nan, ci_low=np.nan, ci_high=np.nan)
    delta = (means[1.0] - means[0.0]).dropna().to_numpy()
    if len(delta) < 2:
        return dict(players=len(delta), difference=float(delta.mean()) if len(delta) else np.nan,
                    ci_low=np.nan, ci_high=np.nan)
    rng = np.random.default_rng(seed)
    draws = np.array([rng.choice(delta, size=len(delta), replace=True).mean() for _ in range(n_boot)])
    return dict(players=len(delta), difference=float(delta.mean()),
                ci_low=float(np.quantile(draws, .025)), ci_high=float(np.quantile(draws, .975)))


def run_repetition_tests(frame, output_dir=None):
    """Deux questions par définition, puis stratifications, sensibilité et exports."""
    records, tables, rates, boot = [], {}, [], []
    scenarios = repetition_scenarios(frame)
    def run(part, a, b, name):
        record, observed, expected, residuals = chi2_details(part, a, b, name)
        records.append(record)
        tables[name] = (observed, expected, residuals)
    for name, (part, repeat, previous, previous_game) in scenarios.items():
        eligible = part.dropna(subset=[repeat, previous, 'result'])
        run(eligible, previous, repeat, name + '__resultat_precedent_repetition')
        run(eligible, repeat, 'result', name + '__repetition_resultat_courant')
        rates.append(dict(scenario=name, transitions=len(eligible),
            players=eligible['user_id'].nunique(),
            repeat_rate=float(eligible[repeat].mean()) if len(eligible) else np.nan))
        boot.append(dict(scenario=name, **player_bootstrap(eligible, repeat)))
        sensitivity = independent_transition_sample(eligible, previous_game)
        run(sensitivity, repeat, 'result', name + '__sensibilite_une_transition')
        for dim in ['color', 'format_partie', 'elo_band']:
            for value, subset in eligible.groupby(dim, observed=True):
                run(subset, repeat, 'result', name + '__' + dim + '_' + str(value))
    d = add_transitions(frame)
    run(d, 'same_color_consecutive', 'result', 'couleur_repetee__resultat_courant')
    run(d, 'same_color_consecutive', 'repeat_all', 'couleur_repetee__ouverture_repetee')
    results = correct_multiple_tests(pd.DataFrame(records))
    rates, boot = pd.DataFrame(rates), pd.DataFrame(boot)
    if output_dir is not None:
        out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
        results.to_csv(out / 'tests_repetition_chi2.csv', index=False)
        rates.to_csv(out / 'taux_repetition.csv', index=False)
        boot.to_csv(out / 'bootstrap_joueurs.csv', index=False)
        for i, (name, values) in enumerate(tables.items()):
            for kind, tab in zip(['observes', 'attendus', 'residus'], values):
                tab.to_csv(out / f'table_{i:03d}_{kind}.csv')
        pd.DataFrame({'table_id': range(len(tables)), 'test': list(tables)}).to_csv(out / 'index_tables.csv', index=False)
    return results, tables, rates, boot

"""Tests reproductibles hors ligne : python -m unittest discover -s tests -v."""
import unittest
from pathlib import Path
import tempfile
import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency
from analyses.Tests_repetition import (add_transitions, chi2_details, correct_multiple_tests,
    repetition_scenarios, independent_transition_sample, player_bootstrap, run_repetition_tests)


def example_panel(players=12, games=40, seed=123):
    """Jeu simulé pour tester le code ; ce ne sont pas des résultats Lichess."""
    rng = np.random.default_rng(seed)
    rows = []
    for user in range(players):
        for i in range(games):
            rows.append(dict(user_id=f'u{user}', game_id=f'g{user}_{i}',
                timestamp=pd.Timestamp('2024-01-01', tz='UTC') + pd.Timedelta(minutes=i*10),
                color=rng.choice(['white','black']), opening_family=rng.choice(['Sicilian Defense','French Defense','Italian Game']),
                result=rng.choice(['Win','Draw','Loss']), score=0., format_partie=rng.choice(['blitz','rapid']),
                elo_band=rng.choice(['1200-1400','1400-1600'])))
    d = pd.DataFrame(rows)
    d['score'] = d['result'].map({'Win':1.,'Draw':.5,'Loss':0.})
    return add_transitions(d)


class TestTransitions(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame(dict(user_id=['a']*4, game_id=['1','2','3','4'],
            timestamp=pd.date_range('2024-01-01', periods=4, tz='UTC'),
            color=['white','black','white','white'], opening_family=['A','B','A','B'],
            result=['Win','Loss','Draw','Win']))
    def test_first_observation_missing(self):
        d=add_transitions(self.frame)
        self.assertTrue(pd.isna(d.iloc[0].repeat_all))
        self.assertTrue(pd.isna(d.iloc[1].repeat_same_color))
    def test_same_color_is_not_previous_game(self):
        d=add_transitions(self.frame)
        self.assertEqual(d.iloc[2].repeat_all,0)
        self.assertEqual(d.iloc[2].repeat_same_color,1)
        self.assertEqual(d.iloc[2].prev_game_same_color,'1')
    def test_color_repeat(self):
        d=add_transitions(self.frame)
        self.assertEqual(d.iloc[2].same_color_consecutive,0)
        self.assertEqual(d.iloc[3].same_color_consecutive,1)
    def test_unknown_not_a_change(self):
        self.frame.loc[1,'opening_family']='Inconnue'
        d=add_transitions(self.frame)
        self.assertTrue(pd.isna(d.iloc[1].repeat_all))
        self.assertTrue(pd.isna(d.iloc[2].repeat_all))
    def test_sort_and_no_future_leak(self):
        d=add_transitions(self.frame.iloc[::-1])
        self.assertEqual(list(d.game_id),['1','2','3','4'])
        self.assertEqual(d.iloc[2].prev_result_same_color,'Win')
    def test_separate_users(self):
        self.frame.loc[2:,'user_id']='b'
        self.assertTrue(pd.isna(add_transitions(self.frame).iloc[2].repeat_all))


class TestStatistics(unittest.TestCase):
    def test_known_chi2(self):
        d=pd.DataFrame([{'a':a,'b':b} for a,b,n in [('x','u',20),('x','v',10),('y','u',10),('y','v',20)] for _ in range(n)])
        result,obs,exp,res=chi2_details(d,'a','b','known')
        self.assertAlmostEqual(result['chi2'],chi2_contingency([[20,10],[10,20]],correction=False)[0])
        self.assertAlmostEqual(result['cramer_v'],1/3)
        self.assertTrue(result['valid'])
        self.assertAlmostEqual(((obs-exp)**2/exp).to_numpy().sum(),result['chi2'])
    def test_constant_and_empty(self):
        for d in [pd.DataFrame({'a':[1]*5,'b':[1]*5}),pd.DataFrame(columns=['a','b'])]:
            result,*_=chi2_details(d,'a','b','empty')
            self.assertTrue(np.isnan(result['p']))
            self.assertFalse(result['valid'])
    def test_sparse_fisher(self):
        d=pd.DataFrame({'a':['x','x','y','y'],'b':['u','v','u','v']})
        result,*_=chi2_details(d,'a','b','sparse')
        self.assertFalse(result['valid'])
        self.assertTrue(np.isfinite(result['fisher_p']))
    def test_holm_only_eligible(self):
        d=correct_multiple_tests(pd.DataFrame({'p':[.01,.04,.02], 'valid':[True,True,False]}))
        self.assertAlmostEqual(d.iloc[0].p_holm,.02)
        self.assertTrue(np.isnan(d.iloc[2].p_holm))
    def test_four_definitions(self):
        self.assertEqual(len(repetition_scenarios(example_panel())),4)
    def test_sensitivity_no_shared_games(self):
        d=example_panel();s=independent_transition_sample(d,'prev_game_all')
        self.assertFalse(s.user_id.duplicated().any())
        ids=list(s.game_id)+list(s.prev_game_all)
        self.assertEqual(len(ids),len(set(ids)))
    def test_bootstrap_reproducible(self):
        d=example_panel()
        self.assertEqual(player_bootstrap(d,'repeat_all',50),player_bootstrap(d,'repeat_all',50))
    def test_exports_and_no_delete(self):
        with tempfile.TemporaryDirectory() as td:
            keep=Path(td)/'keep.txt';keep.write_text('keep')
            results,tables,rates,boot=run_repetition_tests(example_panel(),td)
            self.assertGreater(len(results),20)
            self.assertEqual(len(rates),4)
            self.assertTrue((Path(td)/'tests_repetition_chi2.csv').exists())
            self.assertEqual(keep.read_text(),'keep')
            self.assertEqual(len(tables),len(results))

if __name__=='__main__':unittest.main()

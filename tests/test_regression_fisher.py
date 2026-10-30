"""Vérifier Fisher exact, le modèle multiple, le F et les descriptifs."""

import unittest
import numpy as np
import pandas as pd
from scipy.stats import fisher_exact
from analyses.Tests_repetition import fisher_details, run_fisher_tests
from analyses.Regression_multiple import (
    prepare_regression,
    regression_multiple,
    fisher_global_ols,
)
from analyses.Analyse_ouvertures import statistiques_descriptives


def regression_example(seed=42):
    rng = np.random.default_rng(seed)
    n = 400
    d = pd.DataFrame(
        {
            "repeat_same_color": rng.integers(0, 2, n),
            "elo_diff": rng.normal(0, 100, n),
            "is_white": rng.integers(0, 2, n),
            "format_partie": rng.choice(["blitz", "rapid"], n),
            "user_id": [f"u{i//10}" for i in range(n)],
        }
    )
    d["score"] = (
        0.2
        + 0.15 * d.repeat_same_color
        + 0.02 * d.elo_diff / 100
        + 0.05 * d.is_white
        + 0.03 * d.format_partie.eq("rapid")
        + rng.normal(0, 0.05, n)
    )
    return d


class TestRegressionFisher(unittest.TestCase):
    def test_fisher_known_table(self):
        rows = [
            {"a": a, "b": b}
            for a, b, n in [(0, 0, 6), (0, 1, 2), (1, 0, 1), (1, 1, 4)]
            for _ in range(n)
        ]
        result, table = fisher_details(pd.DataFrame(rows), "a", "b", "known")
        self.assertAlmostEqual(result["odds_ratio"], 12)
        self.assertAlmostEqual(
            result["p"], fisher_exact([[6, 2], [1, 4]], alternative="two-sided")[1]
        )

    def test_fisher_missing_category(self):
        result, table = fisher_details(
            pd.DataFrame({"a": [0, 0], "b": [0, 1]}), "a", "b", "constant"
        )
        self.assertTrue(np.isnan(result["p"]))

    def test_regression_and_f_equal_statsmodels(self):
        summary, coeff, model = regression_multiple(regression_example())
        self.assertEqual(summary.iloc[0].statut, "estime")
        self.assertEqual(summary.iloc[0].joueurs, 40)
        self.assertAlmostEqual(
            summary.iloc[0].F_classique, float(model.fvalue), places=8
        )
        self.assertAlmostEqual(
            summary.iloc[0].p_F_classique, float(model.f_pvalue), places=8
        )
        beta = coeff.set_index("variable").loc["repeat_same_color", "coefficient"]
        self.assertAlmostEqual(beta, 0.15, delta=0.03)
        self.assertTrue(np.isfinite(summary.iloc[0].F_wald_groupes))
        self.assertTrue(coeff.ecart_type_groupe.notna().all())

    def test_regression_degenerate_and_small(self):
        for sample in [
            regression_example().head(10),
            regression_example().assign(repeat_same_color=1),
        ]:
            summary, coeff, model = regression_multiple(sample)
            self.assertEqual(summary.iloc[0].statut, "non_estimable")
            self.assertIsNone(model)

    def test_regression_drops_missing_explicitly(self):
        d = regression_example()
        d.loc[0, "elo_diff"] = np.nan
        self.assertEqual(len(prepare_regression(d)), 399)

    def test_descriptive_mean_std_max(self):
        d = pd.DataFrame(
            {
                name: [1.0, 3.0]
                for name in [
                    "rating",
                    "opponent_rating",
                    "elo_diff",
                    "score",
                    "experience_opening_prior",
                ]
            }
        )
        stats = statistiques_descriptives(d)
        np.testing.assert_allclose(stats["mean"], 2)
        np.testing.assert_allclose(stats["std"], np.sqrt(2))
        np.testing.assert_allclose(stats["max"], 3)


if __name__ == "__main__":
    unittest.main()

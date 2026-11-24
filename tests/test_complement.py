"""Cas limites du nettoyage, des fenêtres, des séries et des modèles."""

from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import Mock, patch
import numpy as np
import pandas as pd
from Nettoyage_donnees import preparer_parties, clean_games, sauvegarder_nettoyage
from analyse_statisitques import (
    statistiques_ouvertures,
    filtrer_periode,
    statistiques_temporelles,
    series_resultats,
    regressions_lineaires,
    analyser,
)
from Analyse_repetition_ouverture import preparer_cadres, tester_table
from Scripts_generation_data.Creation_Df_openings import (
    creer_openings,
    build_position_index,
    identify_opening,
    identify_games,
)
from Scripts_generation_data.Import_une_partie import telecharger_parties
from Stockage_SSPCloud import upload_folder_to_s3
from Master_file import identifier_parties, main
import config_projet as cfg


def fixture(results, openings=None):
    """Un petit historique daté dont les résultats sont fixés à la main."""
    return pd.DataFrame(
        {
            "user_id": [" Alice "] * len(results),
            "game_id": [f"g{i}" for i in range(len(results))],
            "date": pd.date_range("2024-01-01", periods=len(results), tz="UTC"),
            "result": results,
            "opening_name": openings or ["Italienne"] * len(results),
            "color": ["white"] * len(results),
            "rating": [1500] * len(results),
            "opponent_rating": [1400] * len(results),
            "format_partie": ["blitz"] * len(results),
        }
    )


class Complement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.reference = creer_openings(cls.directory.name)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_rates_keep_draws(self):
        df = clean_games(fixture(["Win", "Draw", "Loss", "Win"]))
        table = statistiques_ouvertures(df).iloc[0]
        self.assertEqual(table.n_parties, 4)
        self.assertEqual(table.taux_victoire, 0.5)
        self.assertEqual(table.taux_nulle, 0.25)
        self.assertEqual(table.taux_defaite, 0.25)
        self.assertEqual(table.score_moyen, 0.625)

    def test_unknown_excluded_reported(self):
        df = fixture(["Win", "Loss"], [None, "Italienne"])
        clean, report = preparer_parties(df)
        self.assertEqual(report["ouvertures_manquantes"], 1)
        self.assertEqual(statistiques_ouvertures(clean).n_parties.sum(), 1)

    def test_cleaning_audit(self):
        df = fixture([" Win ", "draw", "erreur"])
        df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
        clean, audit = preparer_parties(df)
        self.assertEqual(audit["lignes_brutes"], 4)
        self.assertEqual(audit["lignes_invalides_rejetees"], 1)
        self.assertEqual(audit["doublons_retires"], 1)
        self.assertEqual(len(clean), 2)
        self.assertEqual(clean.iloc[0].user_id, "alice")
        self.assertEqual(clean.iloc[0].elo_diff, 100)
        self.assertEqual(clean.iloc[0].win_next, 0)

    def test_milliseconds_and_iso_equivalent(self):
        iso = fixture(["Win", "Draw"])
        numeric = iso.drop(columns="date")
        numeric["timestamp_ms"] = iso.date.astype("int64") // 1_000_000
        pd.testing.assert_series_equal(clean_games(iso).date, clean_games(numeric).date)

    def test_window_half_open(self):
        data = clean_games(fixture(["Win"] * 4))
        selected = filtrer_periode(data, "2024-01-02", "2024-01-04")
        self.assertEqual(selected.game_id.tolist(), ["g1", "g2"])
        with self.assertRaises(ValueError):
            filtrer_periode(data, "2024-02-01", "2024-01-01")
        pd.testing.assert_frame_equal(data, clean_games(fixture(["Win"] * 4)))

    def test_month_window_empty(self):
        data = clean_games(fixture(["Win", "Draw"]))
        selected, monthly = statistiques_temporelles(data, "2025-01-01", "2025-02-01")
        self.assertTrue(selected.empty and monthly.empty)
        self.assertIn("taux_victoire", monthly)
        _, maxima = series_resultats(selected)
        self.assertTrue(maxima.empty)

    def test_streaks_draw_breaks_win_and_loss(self):
        data = clean_games(
            fixture(["Win", "Win", "Draw", "Win", "Loss", "Loss", "Draw", "Draw"])
        )
        detail, maxima = series_resultats(data)
        row = maxima.iloc[0]
        self.assertEqual(row.max_serie_victoire, 2)
        self.assertEqual(row.max_serie_defaite, 2)
        self.assertEqual(row.max_serie_nulle, 2)
        self.assertEqual(detail.longueur.sum(), 8)

    def test_streak_opening_change_breaks(self):
        data = clean_games(fixture(["Win"] * 4, ["A", "A", "B", "A"]))
        _, maxima = series_resultats(data)
        self.assertEqual(
            maxima.set_index("opening_name").loc["A", "max_serie_victoire"], 2
        )

    def test_streak_unknown_does_not_bridge(self):
        data = clean_games(fixture(["Win"] * 3, ["A", None, "A"]))
        _, maxima = series_resultats(data)
        self.assertEqual(maxima.max_serie_victoire.iloc[0], 1)

    def test_streak_window_clips(self):
        data = clean_games(fixture(["Win"] * 5))
        _, full = series_resultats(data)
        _, small = series_resultats(filtrer_periode(data, "2024-01-02", "2024-01-04"))
        self.assertEqual(full.max_serie_victoire.iloc[0], 5)
        self.assertEqual(small.max_serie_victoire.iloc[0], 2)

    def test_ties_break_run(self):
        frame = fixture(["Win"] * 3)
        frame.loc[1, "date"] = frame.loc[0, "date"]
        _, maxima = series_resultats(clean_games(frame))
        self.assertEqual(maxima.max_serie_victoire.iloc[0], 1)

    def test_players_do_not_share_runs(self):
        data = fixture(["Win"] * 4)
        data.loc[2:, "user_id"] = "bob"
        _, maxima = series_resultats(clean_games(data))
        self.assertEqual(maxima.max_serie_victoire.iloc[0], 2)

    def test_chi_square_known_table(self):
        rows = pd.DataFrame(
            {
                "repeat_opening": [0] * 30 + [1] * 30,
                "win_next": [0] * 20 + [1] * 10 + [0] * 10 + [1] * 20,
            }
        )
        result, _, _ = tester_table(rows)
        self.assertAlmostEqual(result["chi2"], 20 / 3)
        self.assertAlmostEqual(result["cramer_v"], 1 / 3)
        self.assertLess(result["p_fisher"], 0.05)

    def test_reference_and_depth(self):
        self.assertEqual(len(self.reference), 3865)
        row = self.reference[self.reference.reference_ply.between(11, 20)].iloc[0]
        a = identify_opening(
            " ".join(row.moves), build_position_index(self.reference, 5), 5, 5
        )
        self.assertLessEqual(a["opening_plies_examined"], 10)
        b = identify_opening(
            " ".join(row.moves), build_position_index(self.reference, 10), 10, 5
        )
        self.assertNotEqual(b["eco"], "UNKNOWN")

    def test_three_linear_models_same_sample(self):
        raw = pd.read_csv(cfg.ROOT / "data_demo/parties_demo.csv")
        parties = clean_games(identify_games(raw, self.reference))
        diagnostics, coefficients = regressions_lineaires(parties)
        self.assertEqual(diagnostics.modele.tolist(), ["victoire", "defaite", "nulle"])
        self.assertTrue(diagnostics.status.eq("estime").all())
        self.assertEqual(diagnostics.n_transitions.nunique(), 1)
        # Les trois résultats somment à un : les pentes doivent sommer à zéro.
        slopes = coefficients[coefficients.variable.eq("repeat_opening")]
        self.assertAlmostEqual(slopes.coefficient.sum(), 0, places=10)
        self.assertTrue(np.isfinite(slopes.se_groupee).all())

    def test_api_http_error_propagated(self):
        response = Mock(status_code=500)
        response.raise_for_status.side_effect = RuntimeError("HTTP500")
        http = Mock()
        http.get.return_value = response
        with self.assertRaises(RuntimeError):
            telecharger_parties("alice", session=http)
        response.close.assert_called_once()

    def test_api_429_waits_and_retries(self):
        limited = Mock(status_code=429, headers={"Retry-After": "3"})
        success = Mock(status_code=200)
        success.iter_lines.return_value = [b'{"id":"g1"}']
        http = Mock()
        http.get.side_effect = [limited, success]
        with patch("Scripts_generation_data.Import_une_partie.time.sleep") as sleep:
            rows = telecharger_parties("alice", session=http)
        sleep.assert_called_once_with(60)
        self.assertEqual(rows[0]["id"], "g1")

    def test_s3_and_local_preservation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "data.csv").write_text("data")
            (root / ".env").write_text("secret")
            client = Mock()
            upload_folder_to_s3(root, s3_client=client)
            self.assertTrue((root / "data.csv").exists())
            self.assertEqual(client.upload_file.call_count, 1)
            client.delete_object.assert_not_called()
            self.assertEqual(client.put_object.call_args.kwargs["IfNoneMatch"], "*")

    def test_source_without_moves_remains_explicit(self):
        data = identifier_parties(fixture(["Win"]), self.reference)
        self.assertEqual(
            data.opening_identification_status.iloc[0],
            "etiquette_fournie_profondeur_non_verifiee",
        )

    def test_exports_all_three_exercises(self):
        raw = pd.read_csv(cfg.ROOT / "data_demo/parties_demo.csv")
        parties = identify_games(raw, self.reference)
        with tempfile.TemporaryDirectory() as folder:
            result = analyser(parties, folder, "2024-01-15", "2024-03-01")
            self.assertEqual(len(result["intervalle"]), 1840)
            for name in [
                "exercice1_ouvertures.csv",
                "nouveau_jeu_intervalle.parquet",
                "exercice3_maxima.csv",
                "regressions_coefficients.csv",
                "reproductibilite.json",
            ]:
                self.assertTrue((Path(folder) / name).exists())
            with self.assertRaises(FileExistsError):
                analyser(parties, folder)

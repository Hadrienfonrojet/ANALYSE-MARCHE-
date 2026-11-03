"""Vérifications hors réseau ; aucune suppression ni écriture S3 réelle."""

import ast
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import numpy as np
import pandas as pd
import config_projet as cfg
from Nettoyage_donnees import clean_games, sauvegarder_nettoyage
from Analyse_repetition_ouverture import (
    creer_transitions,
    taux_apres_victoire,
    tester_table,
    bootstrap_joueurs,
    regression_ajustee,
    analyser,
)
from Scripts_generation_data.Creation_Df_openings import (
    creer_openings,
    build_position_index,
    identify_opening,
    identify_games,
)
from Stockage_SSPCloud import upload_folder_to_s3
from Master_file import enrichir_parties, main, preparer_utilisateurs


def panel(users=40, games=30):
    rng = np.random.default_rng(120)
    rows = []
    for u in range(users):
        for t in range(games):
            rows.append(
                dict(
                    user_id=f"u{u}",
                    game_id=f"g{u}_{t}",
                    timestamp_ms=1700000000000 + t * 120000,
                    result=rng.choice(["Win", "Draw", "Loss"], p=[0.48, 0.04, 0.48]),
                    color=rng.choice(["white", "black"]),
                    opening_name=rng.choice(["Italian Game", "French Defense"]),
                    rating=int(rng.integers(1200, 1800)),
                    opponent_rating=int(rng.integers(1200, 1800)),
                    format_partie=rng.choice(["blitz", "rapid"]),
                )
            )
    return pd.DataFrame(rows)


class Complement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.reference = creer_openings(Path(cls.temp.name) / "reference")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_full_reference_compatible(self):
        self.assertEqual(len(self.reference), 3865)
        self.assertTrue(
            {"eco", "name", "moves", "position_key"}.issubset(self.reference)
        )
        self.assertIsInstance(self.reference.iloc[0]["moves"], list)

    def test_identification_5_10(self):
        row = self.reference[self.reference.reference_ply.between(11, 20)].iloc[0]
        a = identify_opening(
            " ".join(row.moves), build_position_index(self.reference, 10), 10, 5
        )
        self.assertNotEqual(a["eco"], "UNKNOWN")
        self.assertLessEqual(a["opening_plies_examined"], 20)
        b = identify_opening(
            " ".join(row.moves), build_position_index(self.reference, 5), 5, 5
        )
        self.assertLessEqual(b["opening_plies_examined"], 10)
        self.assertLessEqual(b["opening_reference_ply"], 10)

    def test_unknown_short(self):
        a = identify_opening("e4 e5", build_position_index(self.reference), 10, 5)
        self.assertEqual(a["opening_identification_status"], "partie_trop_courte")

    def test_draws_and_last(self):
        df = panel(1, 3)
        df["result"] = ["Win", "Draw", "Win"]
        df["opening_name"] = "Italian Game"
        c = clean_games(df)
        self.assertEqual(c.win_next.iloc[0], 0)
        t = creer_transitions(df)
        self.assertEqual(len(t), 2)
        after, _ = taux_apres_victoire(t)
        self.assertEqual(len(after), 1)
        self.assertEqual(after.win_next.iloc[0], 0)

    def test_unknown_not_change_or_skip(self):
        df = panel(1, 3)
        df["opening_name"] = ["Italian Game", None, "Italian Game"]
        t = creer_transitions(df)
        self.assertTrue(t.repeat_opening.isna().all())
        self.assertEqual(t.game_id_next.tolist(), ["g0_1", "g0_2"])

    def test_next_same_color_distinct(self):
        df = panel(1, 3)
        df["color"] = ["white", "black", "white"]
        a = creer_transitions(df)
        b = creer_transitions(df, True)
        self.assertEqual(a.iloc[0].game_id_next, "g0_1")
        self.assertEqual(b.iloc[0].game_id_next, "g0_2")

    def test_timestamp_no_game_id(self):
        c = clean_games(panel(1, 2).drop(columns="game_id"))
        self.assertEqual(len(c), 2)

    def test_known_table(self):
        df = pd.DataFrame(
            {
                "repeat_opening": [0] * 30 + [1] * 30,
                "win_next": [0] * 20 + [1] * 10 + [0] * 10 + [1] * 20,
            }
        )
        r, o, e = tester_table(df)
        self.assertAlmostEqual(r["chi2"], 20 / 3)
        self.assertEqual(r["ddl"], 1)
        self.assertAlmostEqual(r["cramer_v"], 1 / 3)
        self.assertTrue(r["expected_ge5"])
        self.assertLess(r["p_fisher"], 0.05)

    def test_degenerate(self):
        r, _, _ = tester_table(
            pd.DataFrame({"repeat_opening": [1, 1], "win_next": [0, 1]})
        )
        self.assertTrue(np.isnan(r["p_chi2"]))

    def test_regression_and_bootstrap(self):
        t = creer_transitions(panel())
        a, _ = taux_apres_victoire(t)
        info, coef = regression_ajustee(a)
        self.assertEqual(info["status"], "estime_association_ajustee")
        self.assertIn("repeat_opening", coef.variable.tolist())
        self.assertTrue(np.isfinite(coef.se_groupees).all())
        b = bootstrap_joueurs(a, 100)
        self.assertLessEqual(b["ci_low"], b["ci_high"])

    def test_five_players_not_inference(self):
        a, _ = taux_apres_victoire(creer_transitions(panel(5)))
        self.assertEqual(regression_ajustee(a)[0]["status"], "non_estimable")
        self.assertTrue(np.isnan(bootstrap_joueurs(a, 10)["ci_low"]))

    def test_no_local_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "clean.parquet"
            sauvegarder_nettoyage(panel(1), p)
            original = p.read_bytes()
            with self.assertRaises(FileExistsError):
                sauvegarder_nettoyage(panel(1), p)
            self.assertEqual(p.read_bytes(), original)

    def test_s3_preserves(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "run"
            p.mkdir()
            (p / "data.parquet").write_bytes(b"data")
            (p / ".env").write_text("PRIVATE")
            s3 = Mock()
            location = upload_folder_to_s3(p, s3_client=s3)
            self.assertIn("hadrien2703", location)
            self.assertEqual(s3.upload_file.call_count, 1)
            self.assertEqual(s3.put_object.call_args.kwargs["IfNoneMatch"], "*")
            s3.delete_object.assert_not_called()
            self.assertTrue((p / "data.parquet").exists())
            s3.put_object.side_effect = RuntimeError("existing reservation")
            with self.assertRaises(RuntimeError):
                upload_folder_to_s3(p, s3_client=s3)
            self.assertEqual(s3.upload_file.call_count, 1)

    def test_enrichment_mock(self):
        raw = panel(1, 1)
        raw["user_id"] = "alice"
        raw["game_id"] = "abc"
        game = {
            "id": "abc",
            "createdAt": 1700000000000,
            "status": "mate",
            "winner": "white",
            "moves": "e4 e5",
            "opening": {"eco": "C20", "name": "King Pawn"},
            "players": {
                "white": {"user": {"id": "alice"}, "rating": 1600},
                "black": {"user": {"id": "bob"}, "rating": 1500},
            },
        }
        response = Mock(status_code=200)
        response.iter_lines.return_value = [json.dumps(game).encode()]
        session = Mock()
        session.post.return_value = response
        result = enrichir_parties(raw, session=session)
        self.assertEqual(result.iloc[0].opponent_rating, 1500)
        self.assertEqual(result.iloc[0].moves, "e4 e5")
        self.assertEqual(session.post.call_args.kwargs["data"], "abc")

    def test_users_list_five(self):
        with tempfile.TemporaryDirectory() as d, patch.object(cfg, "DATA_DIR", Path(d)):
            x = preparer_utilisateurs(["alice", "bob", "carol", "david", "eve"])
            self.assertEqual(len(x), 5)
            self.assertEqual(
                len(pd.read_parquet(Path(d) / "users_list_global.parquet")), 5
            )

    def test_master_offline_preserves(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            raw = panel(5)
            raw["moves"] = "e4 e5 Nf3 Nc6 Bc4 Bc5 c3 Nf6 d3 d6"
            source = root / "old.parquet"
            raw.to_parquet(source, index=False)

            def run():
                cfg.RUN_DIR = root / "run"
                cfg.DATA_DIR = cfg.RUN_DIR / "Data"
                cfg.RESULTS_DIR = cfg.RUN_DIR / "Resultats"
                cfg.DATA_DIR.mkdir(parents=True)
                cfg.RESULTS_DIR.mkdir()
                return cfg.RUN_DIR

            with patch.object(cfg, "create_run", side_effect=run), patch.object(
                cfg, "RUN_REGRESSIONS", False
            ):
                saved = (cfg.RUN_DIR, cfg.DATA_DIR, cfg.RESULTS_DIR)
                try:
                    path = main(["--raw-file", str(source)])
                    self.assertTrue(source.exists())
                    self.assertTrue((path / "Data/dfs_games_brut.parquet").exists())
                    self.assertTrue((path / "Resultats/tests_repetition.csv").exists())
                finally:
                    cfg.RUN_DIR, cfg.DATA_DIR, cfg.RESULTS_DIR = saved

    def test_exports_and_syntax(self):
        with tempfile.TemporaryDirectory() as d:
            result = analyser(panel(), d, bootstrap_simulations=30)
            self.assertEqual(len(result["tests"]), 3)
            self.assertTrue((Path(d) / "tests_repetition.csv").exists())
            with self.assertRaises(FileExistsError):
                analyser(panel(), d)
        for p in Path(".").rglob("*.py"):
            ast.parse(p.read_text())

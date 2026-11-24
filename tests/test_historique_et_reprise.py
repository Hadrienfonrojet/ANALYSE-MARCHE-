"""Vérifier les limites identifiées pendant la comparaison des deux projets."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
import requests

import config
import config_projet
import import_parties
from nettoyage import clean_games
from import_ouvertures import read_reference, identify_games
from analyse import regressions_lineaires, series_resultats
from Analyse_repetition_ouverture import preparer_cadres, tester_table
from test_complement import fixture


class HistoriqueEtReprise(unittest.TestCase):
    def test_rejet_date_interrompt_series_et_transitions(self):
        brut = fixture(["Win", "erreur", "Win"])
        parties = clean_games(brut)
        self.assertEqual(parties._chronology_break_before.tolist(), [False, True])
        self.assertTrue(preparer_cadres(parties)["immediat"].empty)
        self.assertEqual(series_resultats(parties)[1].max_serie_victoire.iloc[0], 1)
        self.assertTrue(parties.win_next.isna().all())

    def test_nettoyer_deux_fois_conserve_les_ruptures(self):
        parties = clean_games(fixture(["Win", "invalide", "Win", "Win"]))
        pd.testing.assert_frame_equal(parties, clean_games(parties))

    def test_rejet_autre_couleur_interrompt_aussi_cadre_meme_couleur(self):
        brut = fixture(["Win", "Win", "Win"])
        brut["variant"] = ["standard", "chess960", "standard"]
        brut["color"] = ["white", "black", "white"]
        cadres = preparer_cadres(brut)
        self.assertTrue(cadres["prochaine_meme_couleur"].empty)

    def test_date_inconnue_desactive_historique_pas_descriptifs(self):
        brut = fixture(["Win", "Loss", "Win"])
        brut.loc[1, "date"] = pd.NaT
        parties = clean_games(brut)
        self.assertEqual(len(parties), 2)
        self.assertTrue(parties._chronology_uncertain.all())
        self.assertTrue(preparer_cadres(parties)["immediat"].empty)
        self.assertTrue(series_resultats(parties)[1].empty)

    def test_dates_ex_aequo_pas_de_transition_entrante_ou_sortante(self):
        brut = fixture(["Win"] * 4)
        brut.loc[1, "date"] = brut.loc[2, "date"]
        self.assertTrue(preparer_cadres(brut)["immediat"].empty)

    def test_timeout_termine_reste_dans_historique(self):
        brut = fixture(["Win", "Loss", "Win"])
        brut["status"] = ["mate", "timeout", "mate"]
        self.assertEqual(len(clean_games(brut)), 3)
        self.assertEqual(len(preparer_cadres(brut)["immediat"]), 2)

    def test_chi2_groupe_unique_et_vide_signales(self):
        for n in [0, 5]:
            donnees = pd.DataFrame({"repeat_opening": [1] * n, "win_next": [1] * n})
            resultat, _, _ = tester_table(donnees)
            self.assertEqual(resultat["status"], "non_estimable")
            self.assertTrue(np.isnan(resultat["p_chi2"]))

    def test_config_ancienne_et_nouvelle_partagent_etat(self):
        self.assertIs(config, config_projet)

    def test_echec_reseau_ne_cree_pas_cache_de_reussite(self):
        with tempfile.TemporaryDirectory() as dossier, patch.object(
            import_parties, "DATA_DIR", dossier
        ):
            with patch.object(
                import_parties, "telecharger_parties", side_effect=requests.Timeout
            ):
                with self.assertRaises(requests.Timeout):
                    import_parties.extract_games_user("alice", "blitz", 10)
            self.assertEqual(list(Path(dossier).iterdir()), [])
            with patch.object(
                import_parties, "telecharger_parties", return_value=[]
            ) as appel:
                self.assertTrue(
                    import_parties.extract_games_user("alice", "blitz", 10).empty
                )
                self.assertTrue(
                    import_parties.extract_games_user("alice", "blitz", 10).empty
                )
                self.assertEqual(appel.call_count, 1)

    def test_cache_refuse_parametres_differents_ou_contenu_modifie(self):
        with tempfile.TemporaryDirectory() as dossier, patch.object(
            import_parties, "DATA_DIR", dossier
        ):
            with patch.object(import_parties, "telecharger_parties", return_value=[]):
                import_parties.extract_games_user("alice", "blitz", 10, since=100)
            with self.assertRaises(FileExistsError):
                import_parties.extract_games_user("alice", "blitz", 20, since=100)
            with self.assertRaises(FileExistsError):
                import_parties.extract_games_user("alice", "blitz", 10, since=200)
            (Path(dossier) / "api_alice_blitz.ndjson").write_text("{}\n")
            with self.assertRaises(ValueError):
                import_parties.extract_games_user("alice", "blitz", 10, since=100)

    def test_elo_manquant_ne_desaligne_pas_groupes_regression(self):
        brut = pd.read_csv(config.ROOT / "data_demo/parties_demo.csv")
        brut = identify_games(brut, read_reference(config.OPENINGS_REFERENCE_DIR))
        brut.loc[10, "opponent_rating"] = np.nan
        modeles, coefficients = regressions_lineaires(clean_games(brut))
        self.assertEqual(modeles.n_transitions.nunique(), 1)
        self.assertTrue(modeles.status.eq("estime").all())
        self.assertEqual(
            coefficients.loc[coefficients.variable.eq("repeat_opening")].shape[0], 3
        )

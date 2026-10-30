"""Vérifier les corrections des imports historiques et du nettoyage."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd
import requests

import config_projet as cfg
from Nettoyage_donnees import prepare
from Scripts_generation_data import Collecte_enrichie as api
from Scripts_generation_data import Import_des_users as users
from Scripts_generation_data import Import_une_partie as games


class TestImportsNettoyage(unittest.TestCase):

    def setUp(self):
        self.previous = cfg.DATA_DIR, cfg.RESULTS_DIR
        self.temp = tempfile.TemporaryDirectory()
        cfg.DATA_DIR = Path(self.temp.name)
        cfg.RESULTS_DIR = Path(self.temp.name)

    def tearDown(self):
        cfg.DATA_DIR, cfg.RESULTS_DIR = self.previous
        self.temp.cleanup()

    def game(self):
        return {
            'id': 'partie1', 'createdAt': 1700000000000,
            'status': 'mate', 'winner': 'white',
            'players': {
                'white': {'user': {'id': 'alice'}, 'rating': 1500},
                'black': {'user': {'id': 'bob'}, 'rating': 1400},
            },
            'opening': {'eco': 'B20', 'name': 'Sicilian Defense: Example'},
        }

    def raw(self):
        return pd.DataFrame([api.parse_game(self.game(), 'alice', 'blitz', 'alice')])

    def test_missing_user_is_not_string_nan(self):
        raw = self.raw()
        invalid = raw.copy()
        invalid['user_id'] = None
        clean = prepare(pd.concat([raw, invalid], ignore_index=True))
        self.assertEqual(len(clean), 1)
        self.assertNotIn('nan', clean.user_id.tolist())

    def test_normalize_before_deduplication(self):
        raw = self.raw()
        duplicate = raw.copy()
        duplicate['user_id'] = ' ALICE '
        clean = prepare(pd.concat([raw, duplicate], ignore_index=True))
        self.assertEqual(len(clean), 1)
        self.assertEqual(clean.iloc[0].user_id, 'alice')

    def test_blank_opening_is_unknown(self):
        raw = self.raw()
        raw['opening_name'] = '   '
        clean = prepare(raw)
        self.assertEqual(clean.iloc[0].opening_family, 'Inconnue')
        self.assertTrue(pd.isna(clean.iloc[0].repeat_all))
        self.assertTrue(pd.isna(clean.iloc[0].experience_opening_prior))

    def test_invalid_rows_fail_clearly(self):
        raw = self.raw()
        raw['timestamp_ms'] = 'date invalide'
        with self.assertRaisesRegex(ValueError, 'Aucune partie valide'):
            prepare(raw)
        with self.assertRaisesRegex(ValueError, 'Colonnes requises'):
            prepare(self.raw().drop(columns='opponent_rating'))

    def test_conflicting_reference_rejected(self):
        reference = pd.DataFrame({
            'eco': ['B20','B20'],
            'name': ['Sicilian Defense: Example']*2,
            'family': ['A','B'],
        })
        with self.assertRaisesRegex(ValueError, 'Plusieurs familles'):
            prepare(self.raw(), reference)

    def test_finished_game_and_player_validation(self):
        game = self.game()
        self.assertEqual(api.parse_game(game,' ALICE ','blitz','a')['result'], 'Win')
        self.assertEqual(api.parse_game(game,'bob','blitz','a')['result'], 'Loss')
        self.assertIsNone(api.parse_game(game,'absent','blitz','a'))
        game.pop('winner')
        self.assertIsNone(api.parse_game(game,'alice','blitz','a'))
        game['status'] = 'draw'
        self.assertEqual(api.parse_game(game,'alice','blitz','a')['result'], 'Draw')
        game['status'] = 'started'
        self.assertIsNone(api.parse_game(game,'alice','blitz','a'))

    def test_discovery_depth_and_no_redundant_fetch(self):
        graph = {'alice':['bob'],'bob':['carol']}
        with patch.object(users,'get_recent_opponents',side_effect=lambda name,*args:graph[name]) as get:
            with patch.object(users.time,'sleep'):
                frame = users.discover_stratified(['ALICE'], target_per_seed=3)
        self.assertEqual(frame.discovery_depth.tolist(), [0,1,2])
        self.assertEqual(get.call_count, 2)
        self.assertTrue((cfg.DATA_DIR/'users_list_stratified.parquet').exists())

    def test_legacy_users_file_and_missing_origin(self):
        pd.DataFrame({'user_id':[' ALICE ','alice']}).to_parquet(
            cfg.DATA_DIR/'users_list_global.parquet',index=False,
        )
        with patch.object(cfg,'FORMATS',['blitz']):
            with patch.object(games,'extract_games_user',return_value=self.raw()) as extract:
                with patch.object(games.time,'sleep'):
                    raw = games.import_games_df(5)
        self.assertEqual(extract.call_count,1)
        self.assertEqual(raw.iloc[0].seed_origin,'alice')
        self.assertTrue((cfg.DATA_DIR/'games_blitz.parquet').exists())
        self.assertTrue((cfg.DATA_DIR/'games_enrichies_raw.parquet').exists())

    def test_http_context_closes_and_deduplicates(self):
        response=MagicMock()
        response.__enter__.return_value=response
        response.status_code=200
        line=json.dumps(self.game()).encode()
        response.iter_lines.return_value=iter([line,line])
        with patch.object(api.requests,'get',return_value=response):
            result=list(api.request_games('alice','blitz',2))
        self.assertEqual(len(result),1)
        response.__exit__.assert_called_once()

    def test_network_failure_and_rate_limit_are_explicit(self):
        with patch.object(api.requests,'get',side_effect=requests.ConnectionError('offline')):
            with self.assertRaisesRegex(RuntimeError,'Collecte échouée'):
                list(api.request_games('alice','blitz',1,retries=1))
        response=MagicMock()
        response.__enter__.return_value=response
        response.status_code=429
        response.headers={'Retry-After':'date au lieu de secondes'}
        with patch.object(api.requests,'get',return_value=response):
            with patch.object(api.time,'sleep') as sleep:
                with self.assertRaisesRegex(RuntimeError,'Limite API persistante'):
                    list(api.request_games('alice','blitz',1,retries=1))
        sleep.assert_called_once_with(60)


if __name__=='__main__':
    unittest.main()

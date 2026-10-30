"""Vérifier le point d'entrée pédagogique et la conservation des bases."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import config_projet as cfg
import Master_file as master
import Pipeline_ouvertures as pipeline
from test_analyses import example_panel

class TestMaster(unittest.TestCase):
    def test_same_entry_point(self):
        self.assertIs(master.run_pipeline, pipeline.run_pipeline)
        self.assertIs(master.main, pipeline.main)

    def test_invalid_parameters_before_creation(self):
        with patch.object(cfg, 'create_run') as create:
            with self.assertRaises(ValueError):
                master.run_pipeline(users_per_seed=0)
            with self.assertRaises(ValueError):
                master.run_pipeline(skip_collect=True)
            create.assert_not_called()

    def test_reanalysis_without_network_preserves_source(self):
        old=cfg.ROOT,cfg.RUN_DIR,cfg.DATA_DIR,cfg.RESULTS_DIR
        try:
            with tempfile.TemporaryDirectory() as td:
                cfg.ROOT=Path(td)
                raw=example_panel(5,30).rename(columns={'opening_family':'opening_name'})
                raw['timestamp_ms']=raw['timestamp'].astype('int64')//1_000_000
                raw['rating']=1500;raw['opponent_rating']=1450;raw['rating_diff_opponent']=50
                raw['eco']='B20'
                source=Path(td)/'ancienne_base.parquet';raw.to_parquet(source,index=False)
                before=source.read_bytes()
                with patch('requests.get',side_effect=AssertionError('Pas de collecte en réanalyse')):
                    clean,tests=master.run_pipeline(skip_collect=True,raw_file=source)
                self.assertEqual(source.read_bytes(),before)
                self.assertEqual(len(clean),150)
                self.assertTrue((cfg.DATA_DIR/'openings_complet.csv').exists())
                self.assertTrue((cfg.RESULTS_DIR/'repetition/tests_repetition_chi2.csv').exists())
                parameters=json.loads((cfg.RUN_DIR/'experience.json').read_text())
                self.assertEqual(parameters['mode'],'reanalyse')
        finally:
            cfg.ROOT,cfg.RUN_DIR,cfg.DATA_DIR,cfg.RESULTS_DIR=old

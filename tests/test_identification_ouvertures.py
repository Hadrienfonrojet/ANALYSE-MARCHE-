"""Tester le référentiel complet et l'identification à partir des coups, hors réseau."""

from io import StringIO
from pathlib import Path
import tempfile
import unittest

import chess
import chess.pgn
import pandas as pd

import config_projet as cfg
from Scripts_generation_data.Creation_openings_complet import read_reference, build_openings, position_key
from Scripts_generation_data.Identification_ouvertures import build_position_index, identify_opening, identify_games


LINE = 'e4 e5 Nf3 Nc6 Bc4 Bc5 c3 Nf6 d3 d6 O-O O-O Re1 a6 Bb3 Ba7 Nbd2 h6 Nf1 Be6'


def fixture_reference(rows):
    """Positions artificielles de test, sans prétendre à de nouveaux noms officiels."""
    records = []
    for name, pgn in rows:
        game = chess.pgn.read_game(StringIO(pgn))
        board = game.end().board()
        records.append({
            'eco': 'T00', 'name': name, 'family': name.split(':')[0],
            'position_key': position_key(board),
            'reference_ply': len(list(game.mainline_moves())),
        })
    return pd.DataFrame(records)


class TestIdentification(unittest.TestCase):

    def test_reference_includes_unobserved_openings(self):
        reference = build_openings(pd.DataFrame({'eco': ['ZZZ'], 'opening_name': ['Inconnue']}))
        self.assertGreater(len(reference), 3000)
        self.assertEqual(set(reference.source_file), {'a.tsv','b.tsv','c.tsv','d.tsv','e.tsv'})
        self.assertTrue(reference.position_key.notna().all())
        self.assertTrue((cfg.OPENINGS_CACHE_DIR / 'sources_reference.json').is_file())

    def test_deepest_completed_reference(self):
        reference = fixture_reference([
            ('Court','1. e4 e5'),
            ('Intermédiaire','1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5'),
            ('Long','1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d3 d6 6. O-O O-O'),
        ])
        at5 = identify_opening(LINE, build_position_index(reference,5),5,5)
        at10 = identify_opening(LINE, build_position_index(reference,10),10,5)
        self.assertEqual(at5['opening_name'],'Intermédiaire')
        self.assertEqual(at5['opening_plies_examined'],10)
        self.assertEqual(at10['opening_name'],'Long')
        self.assertEqual(at10['opening_reference_ply'],12)
        self.assertEqual(at10['opening_plies_examined'],20)

    def test_short_reference_is_labeled_with_actual_depth(self):
        reference=fixture_reference([('Court','1. e4 e5')])
        found=identify_opening(LINE,build_position_index(reference),10,5)
        self.assertEqual(found['opening_reference_ply'],2)
        self.assertEqual(found['opening_match_ply'],2)
        self.assertEqual(found['opening_plies_examined'],20)

    def test_reference_not_assigned_before_its_end(self):
        reference=fixture_reference([('Long','1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5')])
        found=identify_opening('e4 e5 Nf3 Nc6',build_position_index(reference),10,1)
        self.assertEqual(found['opening_name'],'Inconnue')

    def test_transposition_recognized(self):
        reference=fixture_reference([('Transposition','1. d4 Nf6 2. c4 e6 3. Nf3 d5')])
        found=identify_opening('Nf3 d5 d4 Nf6 c4 e6',build_position_index(reference),10,3)
        self.assertEqual(found['opening_name'],'Transposition')

    def test_missing_short_and_invalid_moves(self):
        reference=fixture_reference([('Court','1. e4 e5')])
        index=build_position_index(reference)
        self.assertEqual(identify_opening(None,index)['opening_identification_status'],'coups_absents')
        self.assertEqual(identify_opening('e4 e5',index)['opening_identification_status'],'partie_trop_courte')
        invalid='e4 e5 Nf3 Nc6 Bc4 Bc5 c3 Nf6 d3 IMPOSSIBLE'
        found=identify_opening(invalid,index)
        self.assertEqual(found['opening_identification_status'],'coups_invalides')
        self.assertEqual(found['opening_name'],'Inconnue')

    def test_no_future_moves_read(self):
        reference=fixture_reference([('Court','1. e4 e5')])
        found=identify_opening(LINE+' IMPOSSIBLE',build_position_index(reference),10,5)
        self.assertEqual(found['opening_name'],'Court')

    def test_api_labels_are_preserved_not_used_as_fallback(self):
        reference=fixture_reference([('Court','1. e4 e5')])
        raw=pd.DataFrame({'game_id':['a','b'],'moves':[LINE,None],
                          'eco':['API','API'],'opening_name':['Nom API','Nom API']})
        result=identify_games(raw,reference)
        self.assertEqual(result.iloc[0].opening_name,'Court')
        self.assertEqual(result.iloc[0].api_opening_name,'Nom API')
        self.assertEqual(result.iloc[1].opening_name,'Inconnue')

    def test_ambiguous_position_is_explicit(self):
        reference=fixture_reference([('Alias A','1. e4 e5'),('Alias B','1. e4 e5')])
        found=identify_opening(LINE,build_position_index(reference))
        self.assertEqual(found['opening_candidate_count'],2)
        self.assertEqual(found['opening_identification_status'],'plusieurs_noms')

    def test_five_local_tsv_are_all_read(self):
        with tempfile.TemporaryDirectory() as td:
            for letter in 'abcde':
                pd.DataFrame({'eco':[letter.upper()+'00'],'name':[letter],
                              'pgn':['1. e4 e5']}).to_csv(Path(td)/(letter+'.tsv'),sep='\t',index=False)
            reference=read_reference(td)
            self.assertEqual(len(reference),5)
            self.assertTrue(reference.reference_ply.eq(2).all())


if __name__=='__main__':
    unittest.main()

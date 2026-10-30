"""Exécuter les cellules sans collecte ni envoi réel, sur un panel simulé."""
import unittest

class TestNotebook(unittest.TestCase):
    def test_notebook_offline(self):
        import ast,json,sys,tempfile,contextlib,io
        from pathlib import Path
        import numpy as np,pandas as pd
        from unittest.mock import patch
        root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
        import config_projet as cfg
        from Scripts_generation_data.Collecte_enrichie import parse_game
        import nbformat
        nb=nbformat.read(root/'Analyse_data.ipynb',as_version=4);nbformat.validate(nb)
        for p in root.rglob('*.py'):ast.parse(p.read_text(),filename=str(p))
        rng=np.random.default_rng(84);rows=[]
        for u in range(12):
         for i in range(40):
          col=rng.choice(['white','black']);user=f'u{u}'
          family=rng.choice(['Sicilian Defense: Test','French Defense: Test','Italian Game: Test'])
          g={'id':f'g{u}_{i}','createdAt':1700000000000+i*100000,'status':'draw' if i%7==0 else 'mate','players':{'white':{'user':{'id':user if col=='white' else 'opponent'},'rating':int(rng.integers(1100,2000))},'black':{'user':{'id':user if col=='black' else 'opponent'},'rating':int(rng.integers(1100,2000))}},'opening':{'eco':'B20','name':family},'rated':True,'variant':'standard','moves':'e4 e5 Nf3 Nc6 Bc4 Bc5 c3 Nf6 d3 d6 O-O O-O Re1 a6 Bb3 Ba7 Nbd2 h6 Nf1 Be6'}
          if i%7:g['winner']=rng.choice(['white','black'])
          rows.append(parse_game(g,user,rng.choice(['blitz','rapid']),user))
        with tempfile.TemporaryDirectory() as td:
         cfg.ROOT=Path(td);source=Path(td)/'input.parquet';pd.DataFrame(rows).to_parquet(source,index=False)
         ns={'display':lambda *a,**k:None,'__name__':'notebook_test'}
         import os;ns['os']=os;ns['Path']=Path
         executed=0
         with contextlib.redirect_stdout(io.StringIO()),patch('requests.get',side_effect=AssertionError('No network in offline notebook test')):
          for cell in nb.cells:
           if cell.cell_type!='code':continue
           s=cell.source
           if 'subprocess.run' in s:continue
           exec(compile(s,'<notebook-cell>','exec'),ns)
           if 'RAW_FILE = None' in s:ns['RAW_FILE']=str(source)
           executed+=1
         from analyses import Tests_repetition as module
         for name in ['add_transitions','chi2_details','correct_multiple_tests','repetition_scenarios','independent_transition_sample','player_bootstrap','run_repetition_tests']:
          expected=next(n for n in ast.parse((root/'analyses/Tests_repetition.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name)
          actual=next(n for cell in nb.cells if cell.cell_type=='code' for n in ast.parse(cell.source).body if isinstance(n,ast.FunctionDef) and n.name==name)
          assert ast.dump(expected)==ast.dump(actual),name
         assert (cfg.RESULTS_DIR/'repetition/tests_repetition_chi2.csv').is_file()
         assert len(ns['tests_repetition'])>30
         assert (cfg.RESULTS_DIR/'correlations_spearman.png').is_file()
         assert Path(str(cfg.RUN_DIR)+'.zip').exists()
         print('PASS notebook:',executed,'code cells executed offline;',len(ns['tests_repetition']),'statistical comparisons; copied functions identical to module')
        print('PASS: Python syntax and Jupyter schema')

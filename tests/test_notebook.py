"""Exécuter toutes les cellules DEMO sans requête réseau ni stockage distant."""
import ast
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import nbformat
import config_projet as cfg


class Notebook(unittest.TestCase):
    def test_notebook_demo(self):
        root = Path(__file__).resolve().parents[1]
        notebook = nbformat.read(root / "Analyse_data.ipynb", as_version=4)
        nbformat.validate(notebook)
        self.assertEqual(len(notebook.cells), 77)
        namespace = {"__name__": "__notebook__"}
        saved = cfg.RUN_DIR, cfg.DATA_DIR, cfg.RESULTS_DIR
        try:
            with tempfile.TemporaryDirectory() as folder, patch.object(cfg, "ROOT", Path(folder)), contextlib.redirect_stdout(io.StringIO()):
                with patch("requests.get", side_effect=AssertionError("Réseau interdit dans DEMO")), patch("requests.post", side_effect=AssertionError("Réseau interdit dans DEMO")):
                    for i, cell in enumerate(notebook.cells):
                        if cell.cell_type == "code":
                            ast.parse(cell.source)
                            exec(compile(cell.source, f"<cellule {i}>", "exec"), namespace)
                self.assertTrue(namespace["DEMO"])
                self.assertEqual(len(namespace["resultats"]["tests"]), 3)
                self.assertFalse(namespace["UPLOAD_S3"])
                self.assertTrue((cfg.RESULTS_DIR / "tests_repetition.csv").exists())
        finally:
            cfg.RUN_DIR, cfg.DATA_DIR, cfg.RESULTS_DIR = saved

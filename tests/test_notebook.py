"""Vérifier les sorties enregistrées et les conditions de reproductibilité."""

from pathlib import Path
import ast
import hashlib
import json
import unittest
import nbformat
import config_projet as cfg


class Notebook(unittest.TestCase):
    def test_saved_notebooks_complete(self):
        for name in ["Analyse_data.ipynb", "notebooks/Rendu_Lichess.ipynb"]:
            notebook = nbformat.read(cfg.ROOT / name, as_version=4)
            nbformat.validate(notebook)
            code = [cell for cell in notebook.cells if cell.cell_type == "code"]
            self.assertTrue(code)
            self.assertEqual(
                [cell.execution_count for cell in code], list(range(1, len(code) + 1))
            )
            self.assertFalse(
                any(out.output_type == "error" for cell in code for out in cell.outputs)
            )
            self.assertTrue(
                all(cell.metadata.get("editable") for cell in notebook.cells)
            )
            for cell in code:
                ast.parse(cell.source)

    def test_demo_snapshot_hash(self):
        source = cfg.ROOT / "data_demo/parties_demo.csv"
        manifest = json.loads(source.with_suffix(".json").read_text())
        self.assertEqual(
            hashlib.sha256(source.read_bytes()).hexdigest(), manifest["sha256"]
        )
        for name, digest in manifest["reference_sha256"].items():
            self.assertEqual(
                hashlib.sha256(
                    (cfg.OPENINGS_REFERENCE_DIR / name).read_bytes()
                ).hexdigest(),
                digest,
            )

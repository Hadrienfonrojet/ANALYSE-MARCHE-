"""Exécuter le notebook dans le Python courant, puis conserver ses sorties."""

import argparse
from pathlib import Path
import sys
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager


def executer(path, destination=None):
    """Utiliser le noyau du même environnement que cette commande."""
    notebook = nbformat.read(path, as_version=4)
    root = Path(__file__).resolve().parent
    manager = KernelManager(kernel_name="python3")
    manager.kernel_spec.argv = [
        sys.executable,
        "-m",
        "ipykernel_launcher",
        "-f",
        "{connection_file}",
    ]
    client = NotebookClient(
        notebook, km=manager, timeout=240, resources={"metadata": {"path": str(root)}}
    )
    try:
        client.execute()
    finally:
        if manager.has_kernel:
            manager.shutdown_kernel(now=True)
    output = Path(destination) if destination else Path(path)
    nbformat.write(notebook, output)
    print(
        sum(c.cell_type == "code" for c in notebook.cells),
        "cellules exécutées dans",
        output,
    )
    return notebook


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parent / "Analyse_data.ipynb",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    executer(args.path, args.output)


if __name__ == "__main__":
    main()

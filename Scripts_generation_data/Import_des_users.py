"""Compatibilité : le code commenté se trouve dans import_utilisateurs.py."""

import sys
import import_utilisateurs as module

if __name__ == "__main__" and hasattr(module, "main"):
    module.main()
else:
    sys.modules[__name__] = module

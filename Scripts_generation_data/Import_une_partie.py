"""Compatibilité : le code commenté se trouve dans import_parties.py."""

import sys
import import_parties as module

if __name__ == "__main__" and hasattr(module, "main"):
    module.main()
else:
    sys.modules[__name__] = module

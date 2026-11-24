"""Compatibilité : le code commenté se trouve dans nettoyage.py."""

import sys
import nettoyage as module

if __name__ == "__main__" and hasattr(module, "main"):
    module.main()
else:
    sys.modules[__name__] = module

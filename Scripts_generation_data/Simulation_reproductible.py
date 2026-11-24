"""Compatibilité : le code commenté se trouve dans donnees_demo.py."""

import sys
import donnees_demo as module

if __name__ == "__main__" and hasattr(module, "main"):
    module.main()
else:
    sys.modules[__name__] = module

"""Compatibilité : le code commenté se trouve dans analyse.py."""

import sys
import analyse as module

if __name__ == "__main__" and hasattr(module, "main"):
    module.main()
else:
    sys.modules[__name__] = module

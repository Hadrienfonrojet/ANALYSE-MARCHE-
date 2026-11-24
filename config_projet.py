"""Compatibilité : le code commenté se trouve dans config.py."""

import sys
import config as module

if __name__ == "__main__" and hasattr(module, "main"):
    module.main()
else:
    sys.modules[__name__] = module

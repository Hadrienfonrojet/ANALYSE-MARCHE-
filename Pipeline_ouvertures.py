"""Autre commande de lancement du master, conservée pour les anciens usages.

Le déroulé complet et commenté est dans Master_file.py : validation, nouvelle
expérience, collecte, ouvertures, préparation, analyses et envoi optionnel.

Ces deux commandes exécutent le même code :
    python Master_file.py --users-per-seed 1 --games-per-format 5
    python -m Pipeline_ouvertures --users-per-seed 1 --games-per-format 5
"""

from Master_file import main, run_pipeline

if __name__ == "__main__":
    main()

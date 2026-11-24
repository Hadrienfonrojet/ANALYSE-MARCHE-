"""Reproduire les trois exercices, puis éventuellement conserver la collecte sur S3."""

import argparse
import hashlib
import json
from pathlib import Path
import pandas as pd
import config_projet as cfg
from Scripts_generation_data.Creation_Df_openings import creer_openings, identify_games
from Nettoyage_donnees import sauvegarder_nettoyage
from Stockage_SSPCloud import upload_folder_to_s3
from analyse_statisitques import analyser


def preparer_utilisateurs(users=None, token=None, discover=False):
    """Enregistrer la liste directe ou découvrir un réseau d’adversaires explicitement."""
    from Scripts_generation_data import Import_des_users as module

    module.DATA_DIR = str(cfg.DATA_DIR)
    if discover:
        frames = [
            module.discover_users_random_walk(
                seed, cfg.USERS_PER_SEED, token, random_seed=cfg.RANDOM_SEED
            )
            for seed in (users or cfg.SEED_USERS)
        ]
        result = pd.concat(frames, ignore_index=True).drop_duplicates("user_id")
    else:
        names = sorted(
            {
                str(u).strip().lower()
                for u in (users or cfg.SEED_USERS)
                if str(u).strip()
            }
        )
        result = pd.DataFrame({"user_id": names})
    if result.empty:
        raise ValueError("Préciser au moins un compte Lichess")
    result.to_parquet(cfg.DATA_DIR / "users_list_global.parquet", index=False)
    return result


def identifier_parties(raw, reference):
    """Classifier depuis les coups, ou documenter les étiquettes d’une base héritée."""
    if "moves" in raw:
        return identify_games(raw, reference)
    if "opening_name" not in raw:
        raise ValueError("La base doit contenir moves ou opening_name")
    result = raw.copy()
    result["opening_identification_status"] = (
        "etiquette_fournie_profondeur_non_verifiee"
    )
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--demo",
        action="store_true",
        help="Rejouer la base fictive livrée, hors réseau",
    )
    source.add_argument("--raw-file", type=Path, help="CSV ou Parquet personnel")
    source.add_argument(
        "--collect", action="store_true", help="Nouvelle collecte API Lichess"
    )
    parser.add_argument("--users", nargs="+")
    parser.add_argument("--discover", action="store_true")
    parser.add_argument("--since", help="Début UTC de collecte réelle, inclus")
    parser.add_argument("--until", help="Fin UTC de collecte réelle, exclue")
    parser.add_argument(
        "--debut", default="2024-01-15", help="Début de la fenêtre de l’exercice 2"
    )
    parser.add_argument(
        "--fin", default="2024-03-01", help="Fin exclue de la fenêtre de l’exercice 2"
    )
    parser.add_argument("--upload", action="store_true")
    args = parser.parse_args(argv)
    cfg.create_run()
    reference = creer_openings()
    if args.collect:
        from Scripts_generation_data import Import_une_partie as module

        token = cfg.get_lichess_token()
        selected = preparer_utilisateurs(args.users, token, args.discover)
        module.DATA_DIR = str(cfg.DATA_DIR)
        start = (
            int(pd.to_datetime(args.since, utc=True).timestamp() * 1000)
            if args.since
            else None
        )
        end = (
            int(pd.to_datetime(args.until, utc=True).timestamp() * 1000) - 1
            if args.until
            else None
        )
        if start is not None and end is not None and start >= end:
            raise ValueError("Bornes de collecte incohérentes")
        raw = module.import_games_df(
            cfg.GAMES_PER_FORMAT, token, since=start, until=end
        )
        origin = {
            "mode": "api",
            "users": selected.user_id.tolist(),
            "since": args.since,
            "until_exclu": args.until,
            "max_games_per_format": cfg.GAMES_PER_FORMAT,
            "attention": "Le plafond par cadence peut rendre l’historique incomplet",
        }
    else:
        path = cfg.ROOT / "data_demo/parties_demo.csv" if args.demo else args.raw_file
        raw = (
            pd.read_csv(path)
            if path.suffix.lower() == ".csv"
            else pd.read_parquet(path)
        )
        origin = {
            "mode": "simulation_figee" if args.demo else "fichier",
            "filename": path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    if raw.empty:
        raise ValueError("Aucune partie récupérée ; dossier conservé")
    raw.to_parquet(cfg.DATA_DIR / "dfs_games_brut.parquet", index=False)
    identified = identifier_parties(raw, reference)
    identified.to_parquet(cfg.DATA_DIR / "dfs_games.parquet", index=False)
    cleaned = sauvegarder_nettoyage(identified, cfg.DATA_DIR / "games_clean.parquet")
    # L’analyse reçoit la base identifiée pour que le bilan compte aussi les rejets.
    result = analyser(
        identified, cfg.RESULTS_DIR, args.debut, args.fin, cfg.RUN_REGRESSIONS
    )
    origin["lignes_nettoyees"] = len(cleaned)
    (cfg.RUN_DIR / "source.json").write_text(
        json.dumps(origin, ensure_ascii=False, indent=2)
    )
    print(result["ouvertures"].round(3).to_string(index=False))
    print(result["maxima"].to_string(index=False))
    print("Collecte locale conservée", cfg.RUN_DIR)
    if args.upload:
        upload_folder_to_s3(cfg.RUN_DIR)
    return cfg.RUN_DIR


if __name__ == "__main__":
    main()

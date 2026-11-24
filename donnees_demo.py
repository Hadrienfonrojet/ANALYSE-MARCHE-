"""Créer exactement la base fictive livrée à partir de lignes du référentiel Lichess."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import numpy as np
import pandas as pd
import config as cfg
from import_ouvertures import creer_openings


def simuler_parties(reference, seed=73, joueurs=40, parties_par_joueur=90):
    """Générer une trajectoire datée par joueur, avec résultat ternaire et coups légaux.

    Le résultat dépend du classement et de la couleur. Le coefficient causal simulé
    de la répétition vaut zéro. Les lignes sont des préfixes théoriques, pas des
    parties complètes réellement jouées sur Lichess.
    """
    families = [
        "Italian Game",
        "Sicilian Defense",
        "French Defense",
        "Queen's Gambit Declined",
    ]
    templates = []
    for name in families:
        candidates = reference[
            (reference.family == name) & reference.reference_ply.between(10, 20)
        ].sort_values(["reference_ply", "name"])
        if candidates.empty:
            raise ValueError("Famille absente du référentiel : " + name)
        templates.append(candidates.iloc[0])
    rng = np.random.default_rng(seed)
    rows = []
    start = pd.Timestamp("2024-01-01", tz="UTC")
    for player in range(joueurs):
        opening = int(rng.integers(4))
        base_rating = int(rng.integers(1200, 1850))
        for game in range(parties_par_joueur):
            if rng.random() < 0.40:
                opening = int(rng.integers(4))
            template = templates[opening]
            rating = base_rating + int(rng.integers(-40, 41))
            opponent = rating + int(rng.integers(-300, 301))
            color = str(rng.choice(["white", "black"]))
            p_win = (
                0.46
                + 0.25 * np.tanh((rating - opponent) / 400)
                + 0.02 * (color == "white")
            )
            result = str(
                rng.choice(["Win", "Draw", "Loss"], p=[p_win, 0.08, 0.92 - p_win])
            )
            date = start + pd.Timedelta(days=game, minutes=player)
            rows.append(
                {
                    "user_id": f"demo_{player:02d}",
                    "game_id": f"demo_{player:02d}_{game:03d}",
                    "timestamp_ms": int(date.timestamp() * 1000),
                    "result": result,
                    "color": color,
                    "format_partie": str(rng.choice(["blitz", "rapid"])),
                    "rating": rating,
                    "opponent_rating": opponent,
                    "moves": " ".join(template.moves),
                    "variant": "standard",
                    "status": "mate" if result != "Draw" else "draw",
                }
            )
    return pd.DataFrame(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=cfg.ROOT / "data_demo/parties_demo.csv"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Comparer à l’empreinte publiée sans écraser le CSV",
    )
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory() as folder:
        reference = creer_openings(data_dir=folder)
        data = simuler_parties(reference)
    payload = data.to_csv(index=False, lineterminator="\n").encode("utf-8")
    digest = sha256(payload).hexdigest()
    manifest = args.output.with_suffix(".json")
    if args.verify:
        expected = json.loads(manifest.read_text())
        actual_sources = {
            letter
            + ".tsv": sha256(
                (cfg.OPENINGS_REFERENCE_DIR / (letter + ".tsv")).read_bytes()
            ).hexdigest()
            for letter in "abcde"
        }
        if actual_sources != expected["reference_sha256"]:
            raise ValueError("Les sources du référentiel ont changé")
        if digest != expected["sha256"] or args.output.read_bytes() != payload:
            raise ValueError("La simulation reconstruite diffère de la base livrée")
        print("Simulation reconstruite à l’identique", digest)
        return
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)
    source_hashes = {
        letter
        + ".tsv": sha256(
            (cfg.OPENINGS_REFERENCE_DIR / (letter + ".tsv")).read_bytes()
        ).hexdigest()
        for letter in "abcde"
    }
    metadata = {
        "nature": "simulation",
        "seed": 73,
        "joueurs": 40,
        "lignes": len(data),
        "sha256": digest,
        "reference_revision": cfg.OPENINGS_REFERENCE_REV,
        "reference_sha256": source_hashes,
        "periode": "2024-01-01 au 2024-03-30, UTC",
        "coefficient_simule_repetition": 0,
        "note": "Résultats fictifs attribués à des préfixes d’ouverture légaux",
    }
    manifest.write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
    print(len(data), "lignes simulées enregistrées", digest)


if __name__ == "__main__":
    main()

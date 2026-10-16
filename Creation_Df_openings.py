# create_openings_df.py
import pandas as pd
import os

# Liste d'exemple : 50 ouvertures populaires avec ECO, nom, premiers coups
eco_db = [
    {"eco": "A00", "name": "Uncommon / Flank Opening", "moves": ["a3"]},
    {"eco": "A01", "name": "Nimzowitsch–Larsen Attack", "moves": ["b3"]},
    {"eco": "A02", "name": "Bird's Opening", "moves": ["f4"]},
    {"eco": "A04", "name": "Réti Opening", "moves": ["Nf3"]},
    {"eco": "A10", "name": "English Opening", "moves": ["c4"]},
    {"eco": "B01", "name": "Scandinavian Defense", "moves": ["e4", "d5"]},
    {"eco": "B02", "name": "Alekhine's Defense", "moves": ["e4", "Nf6"]},
    {"eco": "B07", "name": "Pirc Defense", "moves": ["e4", "d6", "d4", "Nf6"]},
    {"eco": "B08", "name": "Pirc Defense, Classical", "moves": ["e4", "d6", "d4", "Nf6", "Nc3", "g6"]},
    {"eco": "B10", "name": "Caro-Kann Defense", "moves": ["e4", "c6"]},
    {"eco": "B12", "name": "Caro-Kann Defense, Advance", "moves": ["e4", "c6", "d4", "d5", "e5"]},
    {"eco": "B20", "name": "Sicilian Defense", "moves": ["e4", "c5"]},
    {"eco": "B21", "name": "Sicilian Defense, Smith-Morra", "moves": ["e4", "c5", "d4"]},
    {"eco": "B22", "name": "Sicilian, Alapin", "moves": ["e4", "c5", "c3"]},
    {"eco": "B23", "name": "Sicilian, Closed", "moves": ["e4", "c5", "Nc3"]},
    {"eco": "B27", "name": "Sicilian, Closed, Classical", "moves": ["e4", "c5", "Nc3", "Nc6"]},
    {"eco": "B30", "name": "Sicilian, Najdorf", "moves": ["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6"]},
    {"eco": "B40", "name": "Sicilian, Kan", "moves": ["e4", "c5", "Nc3", "Nc6", "Nf3", "e6"]},
    {"eco": "C00", "name": "French Defense", "moves": ["e4", "e6"]},
    {"eco": "C02", "name": "French, Advance", "moves": ["e4", "e6", "d4", "d5", "e5"]},
    {"eco": "C10", "name": "French, Classical", "moves": ["e4", "e6", "d4", "d5", "Nc3"]},
    {"eco": "C20", "name": "King's Pawn Game", "moves": ["e4"]},
    {"eco": "C21", "name": "Center Game", "moves": ["e4", "e5", "d4"]},
    {"eco": "C23", "name": "Bishop's Opening", "moves": ["e4", "e5", "Bc4"]},
    {"eco": "C25", "name": "Vienna Game", "moves": ["e4", "e5", "Nc3"]},
    {"eco": "C30", "name": "King's Gambit", "moves": ["e4", "e5", "f4"]},
    {"eco": "C40", "name": "King's Knight Opening", "moves": ["e4", "e5", "Nf3"]},
    {"eco": "C41", "name": "Philidor Defense", "moves": ["e4", "e5", "Nf3", "d6"]},
    {"eco": "C42", "name": "Petrov's Defense", "moves": ["e4", "e5", "Nf3", "Nf6"]},
    {"eco": "C43", "name": "Bishop's Opening", "moves": ["e4", "e5", "Bc4", "Bc5"]},
    {"eco": "C44", "name": "King's Pawn Game", "moves": ["e4", "e5", "Nf3", "Nc6"]},
    {"eco": "C45", "name": "Scotch Game", "moves": ["e4", "e5", "Nf3", "Nc6", "d4"]},
    {"eco": "C50", "name": "Italian Game", "moves": ["e4", "e5", "Nf3", "Nc6", "Bc4"]},
    {"eco": "C55", "name": "Two Knights Defense", "moves": ["e4", "e5", "Nf3", "Nc6", "Bc4", "Nf6"]},
    {"eco": "C60", "name": "Ruy Lopez", "moves": ["e4", "e5", "Nf3", "Nc6", "Bb5"]},
    {"eco": "C65", "name": "Ruy Lopez, Berlin Defense", "moves": ["e4", "e5", "Nf3", "Nc6", "Bb5", "Nf6"]},
    {"eco": "C70", "name": "Ruy Lopez, Morphy Defense", "moves": ["e4", "e5", "Nf3", "Nc6", "Bb5", "a6"]},
    {"eco": "C78", "name": "Ruy Lopez, Modern Steinitz Defense", "moves": ["e4", "e5", "Nf3", "Nc6", "Bb5", "d6"]},
    {"eco": "C80", "name": "Ruy Lopez, Open", "moves": ["e4", "e5", "Nf3", "Nc6", "Bb5", "a6", "Ba4", "Nf6"]},
    {"eco": "D00", "name": "Queen's Pawn Game", "moves": ["d4"]},
    {"eco": "D02", "name": "Queen's Pawn Game, Chigorin", "moves": ["d4", "d5", "Nc3"]},
    {"eco": "D06", "name": "Queen's Gambit", "moves": ["d4", "d5", "c4"]},
    {"eco": "D10", "name": "Queen's Gambit Declined", "moves": ["d4", "d5", "c4", "e6"]},
    {"eco": "D20", "name": "Queen's Gambit Accepted", "moves": ["d4", "d5", "c4", "dxc4"]},
    {"eco": "D30", "name": "Queen's Gambit Declined, Tarrasch", "moves": ["d4", "d5", "c4", "e6", "Nc3", "Nf6"]},
    {"eco": "D35", "name": "Queen's Gambit Declined, Exchange", "moves": ["d4", "d5", "c4", "e6", "Nc3", "dxc4"]},
    {"eco": "D40", "name": "King's Indian Defense", "moves": ["d4", "Nf6", "c4", "g6"]},
    {"eco": "D50", "name": "Queen's Gambit Declined, Orthodox", "moves": ["d4", "d5", "c4", "e6", "Nc3", "Nf6", "Nf3", "Be7"]},
    {"eco": "E00", "name": "Catalan Opening", "moves": ["d4", "Nf6", "c4", "e6", "g3"]},
    {"eco": "E10", "name": "King's Indian Attack", "moves": ["Nf3", "d5", "g3"]},
]

# Transformer la liste en DataFrame
df_openings = pd.DataFrame(eco_db)

# Répertoire Data du projet (même dossier que Master_file.py)
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "Data")
os.makedirs(DATA_DIR, exist_ok=True)

# Chemin complet pour sauvegarder
save_path = os.path.join(DATA_DIR, "openings.parquet")

# Sauvegarde en parquet
df_openings.to_parquet(save_path)

print(f"DataFrame ouvertures créé et sauvegardé dans {save_path}")
print(df_openings.head())
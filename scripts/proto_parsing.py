# scripts/proto_parsing.py
# Prototype S2 — Objectif O5 / Livrable J4
# Démontre : lecture CSV → DataFrame normalisé

from src.parsing.parse_csv import parse_csv

if __name__ == "__main__":
    df = parse_csv("data/csv/test_kpi.csv", dtype="kpi")
    
    print("=== PROTOTYPE PARSING CSV ===")
    print(f"Fichier lu avec succès : {len(df)} lignes")
    print(f"Colonnes : {list(df.columns)}")
    print(f"Types :\n{df.dtypes}")
    print(f"\nAperçu :\n{df.head()}")
    print("\n parse_csv() → DataFrame OK")
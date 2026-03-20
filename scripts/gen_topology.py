import pandas as pd
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────
OUTPUT_DIR  = Path("data/csv")
OUTPUT_FILE = OUTPUT_DIR / "topology_inventory.csv"

print("[gen_topology] Génération de la topologie FTTH...")

# ── Topologie fixe — 1 OLT + splitters + 100 ONT ──────────────
# Structure : OLT_1 → Splitter_A/B/C/D (1:32 chacun) → ONT_101..ONT_200
rows = []

# OLT
rows.append({"node_id": "OLT_1", "node_type": "OLT",
             "location": "POP_Tunis", "parent": "-"})

# 4 Splitters (A, B, C, D) — 25 ONT chacun
splitters = ["Splitter_A", "Splitter_B", "Splitter_C", "Splitter_D"]
cabinets  = ["Cabinet_A",  "Cabinet_B",  "Cabinet_C",  "Cabinet_D"]

for spl, cab in zip(splitters, cabinets):
    rows.append({"node_id": spl, "node_type": "Splitter",
                 "location": cab, "parent": "OLT_1"})

# 100 ONT — 25 par splitter
ont_counter = 101
for spl, cab in zip(splitters, cabinets):
    for _ in range(25):
        rows.append({
            "node_id"  : f"ONT_{ont_counter}",
            "node_type": "ONT",
            "location" : cab,
            "parent"   : spl,
        })
        ont_counter += 1

# ── Assemblage & sauvegarde ────────────────────────────────────
df = pd.DataFrame(rows)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
df.to_csv(OUTPUT_FILE, index=False)

print(f"[gen_topology] ✓ Shape : {df.shape}")
print(f"[gen_topology] ✓ Fichier : {OUTPUT_FILE}")
print(df["node_type"].value_counts().to_string())
print(df.head(6).to_string())
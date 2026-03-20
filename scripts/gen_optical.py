import pandas as pd
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────
OUTPUT_DIR  = Path("data/csv")
OUTPUT_FILE = OUTPUT_DIR / "optical_budget_scenarios.csv"

# ── 8 scénarios fixes — identiques au dataset encadrant ────────
# Formule : total = fiber_loss + connector_loss + splitter_loss
# fiber_loss    = fiber_km × 0.35 dB/km
# connector_loss = connectors × 0.3 dB
# splitter_loss : 1:16=13dB, 1:32=16.5dB, 1:64=19dB,
#                 1:128=22dB, 1:256=24dB (+ marge 0.5 long distance)
# Status : OK ≤ 28dB, Risque ≤ 32dB, Non conforme > 32dB

scenarios = [
    {"scenario": "Scenario_A_1x16",      "fiber_km": 10.0, "connectors": 4,  "split_ratio": "1:16",
     "fiber_loss_dB": 3.50,  "connector_loss_dB": 1.2, "splitter_loss_dB": 13.0,
     "total_budget_dB": 17.70, "status": "OK"},

    {"scenario": "Scenario_B_1x32",      "fiber_km": 14.5, "connectors": 6,  "split_ratio": "1:32",
     "fiber_loss_dB": 5.07,  "connector_loss_dB": 1.8, "splitter_loss_dB": 16.5,
     "total_budget_dB": 23.38, "status": "OK"},

    {"scenario": "Scenario_C_1x64",      "fiber_km": 18.0, "connectors": 8,  "split_ratio": "1:64",
     "fiber_loss_dB": 6.30,  "connector_loss_dB": 2.4, "splitter_loss_dB": 19.0,
     "total_budget_dB": 27.70, "status": "OK"},

    {"scenario": "Scenario_D_1x32_long", "fiber_km": 26.0, "connectors": 10, "split_ratio": "1:32",
     "fiber_loss_dB": 9.10,  "connector_loss_dB": 3.0, "splitter_loss_dB": 16.5,
     "total_budget_dB": 28.60, "status": "Risque"},

    {"scenario": "Scenario_E_1x128",     "fiber_km": 24.0, "connectors": 12, "split_ratio": "1:128",
     "fiber_loss_dB": 8.40,  "connector_loss_dB": 3.6, "splitter_loss_dB": 22.0,
     "total_budget_dB": 34.00, "status": "Non conforme"},

    {"scenario": "Scenario_F_1x128_long","fiber_km": 30.0, "connectors": 12, "split_ratio": "1:128",
     "fiber_loss_dB": 10.50, "connector_loss_dB": 3.6, "splitter_loss_dB": 22.5,
     "total_budget_dB": 36.60, "status": "Non conforme"},

    {"scenario": "Scenario_G_1x256",     "fiber_km": 20.0, "connectors": 12, "split_ratio": "1:256",
     "fiber_loss_dB": 7.00,  "connector_loss_dB": 3.6, "splitter_loss_dB": 24.0,
     "total_budget_dB": 34.60, "status": "Non conforme"},

    {"scenario": "Scenario_H_1x256_long","fiber_km": 32.0, "connectors": 14, "split_ratio": "1:256",
     "fiber_loss_dB": 11.20, "connector_loss_dB": 4.2, "splitter_loss_dB": 24.5,
     "total_budget_dB": 39.90, "status": "Non conforme"},
]

# ── Assemblage & sauvegarde ────────────────────────────────────
df = pd.DataFrame(scenarios)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
df.to_csv(OUTPUT_FILE, index=False)

print(f"[gen_optical] ✓ Shape : {df.shape}")
print(f"[gen_optical] ✓ Fichier : {OUTPUT_FILE}")
print(df.to_string())
import numpy as np
import pandas as pd
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────
SEED       = 42
N_DAYS     = 30
FREQ       = "5min"
START_DATE = "2025-11-17 08:00:00"
N_ONT      = 100               # ONT_101 → ONT_200
OUTPUT_DIR  = Path("data/csv")
OUTPUT_FILE = OUTPUT_DIR / "ont_status_timeseries.csv"

np.random.seed(SEED)

# ── Axe temporel ───────────────────────────────────────────────
timestamps = pd.date_range(start=START_DATE, periods=N_DAYS * 24 * 12, freq=FREQ)
n = len(timestamps)            # 8640 points par ONT
ont_ids = [f"ONT_{i}" for i in range(101, 201)]  # ONT_101 .. ONT_200

print(f"[gen_ont] Génération : {N_ONT} ONT × {n} points = {N_ONT * n:,} lignes...")

# ── Génération par ONT ─────────────────────────────────────────
frames = []

for ont_id in ont_ids:
    # Puissance RX : entre -15 et -27 dBm (normale GPON)
    # Chaque ONT a sa propre puissance de base + bruit
    rx_base   = np.random.uniform(-22, -18)
    rx_power  = (rx_base + np.random.normal(0, 0.5, n)).clip(-40, -15)

    # Puissance TX : entre 0.5 et 3.0 dBm
    tx_base   = np.random.uniform(1.5, 2.5)
    tx_power  = (tx_base + np.random.normal(0, 0.15, n)).clip(0.01, 3.33)

    # Statut opérationnel : 'up' par défaut
    status = np.array(['up'] * n)

    # Injection pannes aléatoires (~0.6% de down par ONT)
    n_pannes = np.random.randint(0, 3)  # 0, 1 ou 2 pannes par ONT
    for _ in range(n_pannes):
        debut = np.random.randint(0, n - 12)
        duree = np.random.randint(3, 12)    # 15 min à 1h
        status[debut:debut + duree] = 'do'
        # Pendant la panne : rx_power chute
        rx_power[debut:debut + duree] = np.random.uniform(-40, -35, duree)

    frames.append(pd.DataFrame({
        "timestamp"    : timestamps,
        "ont_id"       : ont_id,
        "rx_power_dBm" : rx_power.round(2),
        "tx_power_dBm" : tx_power.round(2),
        "onuOperStatus": status,
    }))

# ── Assemblage & sauvegarde ────────────────────────────────────
df = pd.concat(frames, ignore_index=True)

# Tri par timestamp puis ont_id — même ordre que l'encadrant
df = df.sort_values(["timestamp", "ont_id"]).reset_index(drop=True)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
df.to_csv(OUTPUT_FILE, index=False)

n_down = (df["onuOperStatus"] == "do").sum()
print(f"[gen_ont] ✓ Shape : {df.shape}")
print(f"[gen_ont] ✓ ONT down : {n_down} points ({n_down/len(df)*100:.1f}%)")
print(f"[gen_ont] ✓ Fichier : {OUTPUT_FILE}")
print(df.head(3).to_string())
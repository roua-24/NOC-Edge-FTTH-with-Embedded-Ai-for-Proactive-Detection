import numpy as np
import pandas as pd
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────
SEED        = 42
N_DAYS      = 30
FREQ        = "5min"
START_DATE  = "2024-01-01"
OUTPUT_DIR  = Path("data/csv")
OUTPUT_FILE = OUTPUT_DIR / "kpi_olt_port_1.csv"

np.random.seed(SEED)

# ── Axe temporel ───────────────────────────────────────────────
timestamps = pd.date_range(start=START_DATE, periods=N_DAYS * 24 * 12, freq=FREQ)
n = len(timestamps)
print(f"[gen_kpi] Génération de {n} points sur {N_DAYS} jours...")

# ── Signal de base ─────────────────────────────────────────────
heure_du_jour = np.tile(np.arange(288), N_DAYS)
profil_jour   = 0.5 + 0.4 * np.sin(2 * np.pi * heure_du_jour / 288 - np.pi / 2)

bytes_in        = (profil_jour * 600e6 + np.random.normal(0, 20e6, n)).clip(50e6, 900e6)
bytes_out       = (bytes_in * 0.6     + np.random.normal(0, 10e6, n)).clip(30e6, 600e6)
if_errors       = np.random.poisson(lam=2, size=n).astype(float)
utilization_pct = (bytes_in / 900e6 * 100).clip(5, 99)

# ── Injection d'anomalies ──────────────────────────────────────
anomaly_flag = np.zeros(n, dtype=int)

idx_sat             = slice(7*288 + 180, 7*288 + 204)
bytes_in[idx_sat]        *= 5.5
utilization_pct[idx_sat]  = 99.0
anomaly_flag[idx_sat]     = 1

idx_err              = slice(14*288 + 60, 14*288 + 72)
if_errors[idx_err]       += np.random.poisson(50, 12)
anomaly_flag[idx_err]     = 1

idx_down             = slice(21*288 + 96, 21*288 + 132)
bytes_in[idx_down]        *= 0.05
bytes_out[idx_down]       *= 0.05
utilization_pct[idx_down]  = 2.0
anomaly_flag[idx_down]    = 1

pct = anomaly_flag.sum() / n * 100
print(f"[gen_kpi] Anomalies injectées : {anomaly_flag.sum()} points ({pct:.1f}%)")

# ── Assemblage & sauvegarde ────────────────────────────────────
df = pd.DataFrame({
    "timestamp"       : timestamps,
    "bytes_in"        : bytes_in.astype(int),
    "bytes_out"       : bytes_out.astype(int),
    "if_errors"       : if_errors.astype(int),
    "utilization_pct" : utilization_pct.round(2),
    "anomaly_flag"    : anomaly_flag,
})

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
df.to_csv(OUTPUT_FILE, index=False)

print(f"[gen_kpi] ✓ Fichier généré : {OUTPUT_FILE}")
print(f"[gen_kpi] ✓ Shape : {df.shape}")
print(df.head(3).to_string())
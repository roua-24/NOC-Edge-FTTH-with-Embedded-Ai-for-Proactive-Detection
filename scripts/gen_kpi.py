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

ifInOctets_bytes  = (profil_jour * 600e6 + np.random.normal(0, 20e6, n)).clip(50e6, 900e6)
ifOutOctets_bytes = (ifInOctets_bytes * 0.6 + np.random.normal(0, 10e6, n)).clip(30e6, 600e6)
ifInErrors        = np.random.poisson(lam=2, size=n).astype(float)
ifOutErrors       = np.random.poisson(lam=1, size=n).astype(float)
utilization_pct   = (ifInOctets_bytes / 900e6 * 100).clip(5, 99)

# ── Injection d'anomalies ──────────────────────────────────────
label_anomaly = np.zeros(n, dtype=int)

# Anomalie 1 : saturation OLT (j7, 2h)
idx_sat = slice(7*288 + 180, 7*288 + 204)
ifInOctets_bytes[idx_sat]  *= 5.5
utilization_pct[idx_sat]    = 99.0
label_anomaly[idx_sat]      = 1

# Anomalie 2 : burst d'erreurs (j14, 1h)
idx_err = slice(14*288 + 60, 14*288 + 72)
ifInErrors[idx_err]        += np.random.poisson(50, 12)
ifOutErrors[idx_err]       += np.random.poisson(20, 12)
label_anomaly[idx_err]      = 1

# Anomalie 3 : ONT down — chute de trafic (j21, 3h)
idx_down = slice(21*288 + 96, 21*288 + 132)
ifInOctets_bytes[idx_down]  *= 0.05
ifOutOctets_bytes[idx_down] *= 0.05
utilization_pct[idx_down]    = 2.0
label_anomaly[idx_down]      = 1

pct = label_anomaly.sum() / n * 100
print(f"[gen_kpi] Anomalies injectées : {label_anomaly.sum()} points ({pct:.1f}%)")

# ── Assemblage & sauvegarde ────────────────────────────────────
df = pd.DataFrame({
    "timestamp"        : timestamps,
    "ifInOctets_bytes" : ifInOctets_bytes.astype(int),
    "ifOutOctets_bytes": ifOutOctets_bytes.astype(int),
    "ifInErrors"       : ifInErrors.astype(int),
    "ifOutErrors"      : ifOutErrors.astype(int),
    "utilization_pct"  : utilization_pct.round(2),
    "label_anomaly"    : label_anomaly,
})

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
df.to_csv(OUTPUT_FILE, index=False)

print(f"[gen_kpi] ✓ Fichier généré : {OUTPUT_FILE}")
print(f"[gen_kpi] ✓ Shape : {df.shape}")
print(f"[gen_kpi] ✓ Colonnes : {list(df.columns)}")
print(df.head(2).to_string())
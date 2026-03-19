import numpy as np
import pandas as pd
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────
SEED        = 42
N_DAYS      = 30
FREQ        = "5min"
START_DATE  = "2024-01-01"
OUTPUT_DIR  = Path("data/csv")
OUTPUT_FILE = OUTPUT_DIR / "qos_metrics.csv"

np.random.seed(SEED)

# ── Axe temporel ───────────────────────────────────────────────
timestamps = pd.date_range(start=START_DATE, periods=N_DAYS * 24 * 12, freq=FREQ)
n = len(timestamps)
print(f"[gen_qos] Génération de {n} points sur {N_DAYS} jours...")

# ── Signal de base (QoS normale) ───────────────────────────────
# latence normale : ~5ms avec légère variation selon charge
heure_du_jour = np.tile(np.arange(288), N_DAYS)
charge        = 0.5 + 0.4 * np.sin(2 * np.pi * heure_du_jour / 288 - np.pi / 2)

latency_ms      = (5 + charge * 3 + np.random.normal(0, 0.5, n)).clip(1, 20)
jitter_ms       = (1 + charge * 1 + np.random.normal(0, 0.2, n)).clip(0.1, 8)
packet_loss_pct = (0.01 + np.random.exponential(0.02, n)).clip(0, 0.3)

# ── Labels dégradation (normal=0, dégradé=1) ───────────────────
label_degradation = np.zeros(n, dtype=int)

# Dégradation 1 : pic de latence (j5, 90 min)
idx_lat = slice(5*288 + 120, 5*288 + 138)   # 18 points = 90 min
latency_ms[idx_lat]         += np.random.uniform(80, 120, 18)
jitter_ms[idx_lat]          += np.random.uniform(15, 25, 18)
label_degradation[idx_lat]   = 1

# Dégradation 2 : pertes de paquets élevées (j12, 1h)
idx_loss = slice(12*288 + 200, 12*288 + 212)  # 12 points = 1h
packet_loss_pct[idx_loss]     = np.random.uniform(2, 8, 12)
latency_ms[idx_loss]         += np.random.uniform(20, 40, 12)
label_degradation[idx_loss]   = 1

# Dégradation 3 : congestion prolongée (j19, 2h30)
idx_cong = slice(19*288 + 60, 19*288 + 90)   # 30 points = 2h30
latency_ms[idx_cong]          = np.random.uniform(60, 95, 30)
jitter_ms[idx_cong]           = np.random.uniform(18, 28, 30)
packet_loss_pct[idx_cong]     = np.random.uniform(1, 4, 30)
label_degradation[idx_cong]   = 1

pct = label_degradation.sum() / n * 100
print(f"[gen_qos] Dégradations injectées : {label_degradation.sum()} points ({pct:.1f}%)")

# ── Assemblage & sauvegarde ────────────────────────────────────
df = pd.DataFrame({
    "timestamp"         : timestamps,
    "latency_ms"        : latency_ms.round(2),
    "jitter_ms"         : jitter_ms.round(2),
    "packet_loss_pct"   : packet_loss_pct.round(4),
    "label_degradation" : label_degradation,
})

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
df.to_csv(OUTPUT_FILE, index=False)

print(f"[gen_qos] ✓ Fichier généré : {OUTPUT_FILE}")
print(f"[gen_qos] ✓ Shape : {df.shape}")
print(df.head(3).to_string())
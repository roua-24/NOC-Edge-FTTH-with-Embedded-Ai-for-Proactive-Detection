import numpy as np
import pandas as pd
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────
SEED        = 42
N_DAYS      = 30
FREQ        = "5min"
START_DATE  = "2025-11-17 08:00:00"
OUTPUT_DIR  = Path("data/csv")
OUTPUT_FILE = OUTPUT_DIR / "qos_metrics.csv"

np.random.seed(SEED)

# ── Axe temporel ───────────────────────────────────────────────
timestamps = pd.date_range(start=START_DATE, periods=N_DAYS * 24 * 12, freq=FREQ)
n = len(timestamps)
print(f"[gen_qos] Génération de {n} points sur {N_DAYS} jours...")

# ── Signal de base aligné sur le dataset encadrant ─────────────
# latency : ~8ms moyenne, bruit gaussien (valeurs négatives possibles = bruit réel)
# packet_loss : distribution exponentielle, max ~3.4% en normal
heure_du_jour = np.tile(np.arange(288), N_DAYS)
charge        = 0.5 + 0.4 * np.sin(2 * np.pi * heure_du_jour / 288 - np.pi / 2)

latency_ms      = (8 + charge * 4 + np.random.normal(0, 1.5, n))
jitter_ms       = (1.5 + charge * 1.2 + np.random.normal(0, 0.4, n)).clip(0, 12)
packet_loss_pct = np.random.exponential(0.4, n).clip(0, 3.4)

# ── Labels dégradation — alignés sur encadrant (303/8640 = 3.5%) ──
label_degradation = np.zeros(n, dtype=int)

# Dégradation 1 : pic de latence (j5, 90 min = 18 points)
idx_lat = slice(5*288 + 120, 5*288 + 138)
latency_ms[idx_lat]          += np.random.uniform(15, 25, 18)
jitter_ms[idx_lat]           += np.random.uniform(5, 10, 18)
label_degradation[idx_lat]    = 1

# Dégradation 2 : pertes élevées (j10, 3h = 36 points)
idx_loss = slice(10*288 + 100, 10*288 + 136)
packet_loss_pct[idx_loss]     = np.random.uniform(1.5, 3.4, 36)
latency_ms[idx_loss]         += np.random.uniform(8, 15, 36)
label_degradation[idx_loss]   = 1

# Dégradation 3 : congestion prolongée (j17, 10h = 120 points)
idx_cong = slice(17*288 + 40, 17*288 + 160)
latency_ms[idx_cong]          = np.random.uniform(18, 33, 120)
jitter_ms[idx_cong]           = np.random.uniform(5, 12, 120)
packet_loss_pct[idx_cong]     = np.random.uniform(0.8, 3.0, 120)
label_degradation[idx_cong]   = 1

# Dégradation 4 : micro-coupures (j24, 2h = 24 points)
idx_micro = slice(24*288 + 200, 24*288 + 224)
latency_ms[idx_micro]         = np.random.uniform(20, 32, 24)
packet_loss_pct[idx_micro]    = np.random.uniform(1.0, 2.5, 24)
label_degradation[idx_micro]  = 1

pct = label_degradation.sum() / n * 100
print(f"[gen_qos] Dégradations injectées : {label_degradation.sum()} points ({pct:.1f}%)")

# ── Assemblage & sauvegarde ────────────────────────────────────
df = pd.DataFrame({
    "timestamp"         : timestamps,
    "latency_ms"        : latency_ms.round(2),
    "jitter_ms"         : jitter_ms.round(2),
    "packet_loss_pct"   : packet_loss_pct.round(3),
    "label_degradation" : label_degradation,
})

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
df.to_csv(OUTPUT_FILE, index=False)

print(f"[gen_qos] ✓ Fichier généré : {OUTPUT_FILE}")
print(f"[gen_qos] ✓ Shape : {df.shape}")
print(f"[gen_qos] ✓ Colonnes : {list(df.columns)}")
print(df.head(2).to_string())
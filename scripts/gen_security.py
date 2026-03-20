import numpy as np
import pandas as pd
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────
SEED        = 42
N_EVENTS    = 500
START_DATE  = "2025-11-17 08:00:00"
END_DATE    = "2025-12-17 08:00:00"
OUTPUT_DIR  = Path("data/csv")
OUTPUT_FILE = OUTPUT_DIR / "security_events.csv"

np.random.seed(SEED)

print(f"[gen_security] Génération de {N_EVENTS} événements sécurité...")

# ── Types d'événements — alignés sur l'encadrant ───────────────
event_types = [
    "SNMPv2c_detected",
    "bruteforce_login",
    "ARP_spoofing",
    "DHCP_rogue",
    "port_scan",
    "unauthorized_access",
]

severities = {
    "SNMPv2c_detected"   : "low",
    "bruteforce_login"   : "high",
    "ARP_spoofing"       : "low",
    "DHCP_rogue"         : "high",
    "port_scan"          : "medium",
    "unauthorized_access": "high",
}

# ── Génération des timestamps aléatoires dans la période ────────
start = pd.Timestamp(START_DATE)
end   = pd.Timestamp(END_DATE)
delta = int((end - start).total_seconds() / 60)  # en minutes

random_minutes = np.sort(np.random.choice(delta, N_EVENTS, replace=False))
timestamps = [start + pd.Timedelta(minutes=int(m)) for m in random_minutes]

# ── Tirage des types d'événements ──────────────────────────────
# Probabilités : SNMPv2c et ARP_spoofing plus fréquents
weights = [0.30, 0.20, 0.20, 0.10, 0.12, 0.08]
chosen_events = np.random.choice(event_types, N_EVENTS, p=weights)

# ── Assemblage & sauvegarde ────────────────────────────────────
df = pd.DataFrame({
    "timestamp"  : timestamps,
    "event_type" : chosen_events,
    "severity"   : [severities[e] for e in chosen_events],
    "description": [f"Fictive event: {e} detected" for e in chosen_events],
})

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
df.to_csv(OUTPUT_FILE, index=False)

print(f"[gen_security] ✓ Shape : {df.shape}")
print(f"[gen_security] ✓ Fichier : {OUTPUT_FILE}")
print(df["event_type"].value_counts().to_string())
print(df.head(3).to_string())
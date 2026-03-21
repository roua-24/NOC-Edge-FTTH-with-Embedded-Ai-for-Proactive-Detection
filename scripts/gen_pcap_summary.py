import numpy as np
import pandas as pd
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────
SEED        = 42
N_FLUX      = 100000
START_DATE  = "2025-11-17 08:00:00"
END_DATE    = "2025-12-17 08:00:00"
OUTPUT_DIR  = Path("data/traces")
OUTPUT_FILE = OUTPUT_DIR / "pcap_flows_summary.csv"

np.random.seed(SEED)

print(f"[gen_pcap] Generation de {N_FLUX:,} flux reseau...")

# ── Timestamps aleatoires sur la periode ───────────────────────
start = pd.Timestamp(START_DATE)
end   = pd.Timestamp(END_DATE)
delta_minutes = int((end - start).total_seconds() / 60)

random_minutes = np.sort(np.random.choice(delta_minutes, N_FLUX, replace=True))
timestamps = [start + pd.Timedelta(minutes=int(m)) for m in random_minutes]

# ── Protocoles — distribution realiste FTTH ────────────────────
protocoles = ["TCP", "UDP", "ARP", "ICMP", "DHCP"]
weights    = [0.40, 0.34, 0.12, 0.08, 0.06]
protocol   = np.random.choice(protocoles, N_FLUX, p=weights)

# ── IPs source et destination ──────────────────────────────────
def gen_ip():
    return (f"10.{np.random.randint(0,20)}."
            f"{np.random.randint(0,20)}."
            f"{np.random.randint(1,255)}")

src_ips = [gen_ip() for _ in range(N_FLUX)]
dst_ips = [gen_ip() for _ in range(N_FLUX)]

# ── Paquets et octets ──────────────────────────────────────────
packets = np.random.randint(1, 200, N_FLUX).astype(int)
bytes_  = (packets * np.random.randint(64, 1500, N_FLUX)).astype(int)

# ── Labels suspects — incidents reseau ────────────────────────
# DoS low-rate, ARP storm, DHCP rogue
label_suspicious = np.zeros(N_FLUX, dtype=int)

# ARP storm — jour 8
mask_arp = (np.array(protocol) == "ARP")
idx_storm = np.where(mask_arp)[0][:500]
label_suspicious[idx_storm] = 1

# DoS TCP — jour 15
idx_dos = np.random.choice(
    np.where(np.array(protocol) == "TCP")[0], 200, replace=False)
label_suspicious[idx_dos] = 1

pct = label_suspicious.sum() / N_FLUX * 100
print(f"[gen_pcap] Flux suspects : {label_suspicious.sum()} ({pct:.1f}%)")

# ── Assemblage & sauvegarde ────────────────────────────────────
df = pd.DataFrame({
    "timestamp"       : timestamps,
    "src_ip"          : src_ips,
    "dst_ip"          : dst_ips,
    "protocol"        : protocol,
    "packets"         : packets,
    "bytes"           : bytes_,
    "label_suspicious": label_suspicious,
})

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
df.to_csv(OUTPUT_FILE, index=False)

print(f"[gen_pcap] [OK] Shape : {df.shape}")
print(f"[gen_pcap] [OK] Fichier : {OUTPUT_FILE}")
print(df.head(3).to_string())
import numpy as np
from pathlib import Path

# -- Configuration -----------------------------------------------------
SEED        = 42
N_ONT       = 100          # ONT_101 .. ONT_200
OUTPUT_DIR  = Path("data/snmp")

np.random.seed(SEED)

print(f"[gen_snmp] Generation de {N_ONT + 1} fichiers snmpwalk...")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# -- Fichier OLT -------------------------------------------------------
olt_content = """IF-MIB::ifInOctets.1 = Counter32: {in_oct}
IF-MIB::ifOutOctets.1 = Counter32: {out_oct}
IF-MIB::ifInErrors.1 = Counter32: {in_err}
IF-MIB::ifOutErrors.1 = Counter32: {out_err}
IF-MIB::ifSpeed.1 = Gauge32: 100000000
SNMPv3::securityLevel.0 = STRING: noAuthNoPriv""".format(
    in_oct  = np.random.randint(5_000_000, 15_000_000),
    out_oct = np.random.randint(3_000_000,  8_000_000),
    in_err  = np.random.randint(0, 5),
    out_err = np.random.randint(0, 3),
)

olt_path = OUTPUT_DIR / "snmpwalk_olt_port_1.txt"
olt_path.write_text(olt_content, encoding="utf-8")
print(f"[gen_snmp] [OK] {olt_path.name}")

# -- Fichiers ONT ------------------------------------------------------
n_ok  = 0
for i in range(101, 201):
    rx_power = round(np.random.uniform(-27, -16), 2)
    tx_power = round(np.random.uniform(0.5, 3.0),  2)
    status   = 1 if np.random.random() > 0.05 else 2   # 1=up, 2=down
    in_err   = np.random.randint(0, 5)

    ont_content = (
        f"GPON-MIB::onuOperStatus.{i} = INTEGER: {status}\n"
        f"GPON-MIB::rxPower.{i} = Gauge32: {rx_power}\n"
        f"GPON-MIB::txPower.{i} = Gauge32: {tx_power}\n"
        f"IF-MIB::ifInErrors.{i} = Counter32: {in_err}"
    )

    ont_path = OUTPUT_DIR / f"snmpwalk_ONT_{i}.txt"
    ont_path.write_text(ont_content, encoding="utf-8")
    n_ok += 1

print(f"[gen_snmp] [OK] {n_ok} fichiers ONT generes")
print(f"[gen_snmp] [OK] Total : {n_ok + 1}/101 fichiers dans {OUTPUT_DIR}")
taux = (n_ok + 1) / 101 * 100
print(f"[gen_snmp] Taux : {taux:.0f}% (CDC >= 90%) - {'OK' if taux >= 90 else 'KO'}")
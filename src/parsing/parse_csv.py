import pandas as pd
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO,
                    format="[parse_csv] %(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

SCHEMAS = {
    "kpi"     : ["timestamp", "ifInOctets_bytes", "ifOutOctets_bytes",
                 "ifInErrors", "ifOutErrors", "utilization_pct", "label_anomaly"],
    "qos"     : ["timestamp", "latency_ms", "jitter_ms",
                 "packet_loss_pct", "label_degradation"],
    "ont"     : ["timestamp", "ont_id", "rx_power_dBm",
                 "tx_power_dBm", "onuOperStatus"],
    "optical" : ["scenario", "fiber_km", "connectors", "split_ratio",
                 "fiber_loss_dB", "connector_loss_dB",
                 "splitter_loss_dB", "total_budget_dB", "status"],
    "security": ["timestamp", "event_type", "severity", "description"],
    "topology": ["node_id", "node_type", "location", "parent"],
}

DATE_COLS = {
    "kpi"     : ["timestamp"],
    "qos"     : ["timestamp"],
    "ont"     : ["timestamp"],
    "optical" : [],
    "security": ["timestamp"],
    "topology": [],
}


def parse_csv(path: str, dtype: str) -> pd.DataFrame:
    path = Path(path)

    if dtype not in SCHEMAS:
        raise ValueError(f"dtype '{dtype}' inconnu. Valeurs acceptées : {list(SCHEMAS.keys())}")

    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {path}")

    logger.info(f"Lecture '{path.name}' (dtype={dtype})...")

    try:
        date_cols = DATE_COLS[dtype]
        df = pd.read_csv(path, parse_dates=date_cols if date_cols else False)

        missing = [c for c in SCHEMAS[dtype] if c not in df.columns]
        if missing:
            raise ValueError(f"Colonnes manquantes dans '{path.name}': {missing}")

        n_nan = df.isnull().sum().sum()
        if n_nan > 0:
            logger.warning(f"{n_nan} NaN détectés — application ffill()")
            df = df.ffill().dropna()

        if "timestamp" in df.columns:
            df = df.sort_values("timestamp").reset_index(drop=True)

        if dtype == "ont":
            df["ont_id"]       = df["ont_id"].astype("category")
            df["rx_power_dBm"] = df["rx_power_dBm"].astype("float32")
            df["tx_power_dBm"] = df["tx_power_dBm"].astype("float32")

        logger.info(f"✓ {len(df):,} lignes | colonnes : {list(df.columns)}")
        return df

    except pd.errors.ParserError as e:
        logger.error(f"Erreur parsing CSV : {e}")
        return pd.DataFrame()


if __name__ == "__main__":
    tests = [
        ("data/csv/kpi_olt_port_1.csv",           "kpi"),
        ("data/csv/qos_metrics.csv",              "qos"),
        ("data/csv/ont_status_timeseries.csv",    "ont"),
        ("data/csv/optical_budget_scenarios.csv", "optical"),
        ("data/csv/security_events.csv",          "security"),
        ("data/csv/topology_inventory.csv",       "topology"),
    ]

    succes = 0
    for path, dtype in tests:
        print(f"\n{'─'*50}")
        try:
            df = parse_csv(path, dtype)
            if not df.empty:
                print(f"  ✓ {dtype:10} → shape {df.shape}")
                succes += 1
        except Exception as e:
            print(f"  ✗ {dtype:10} → ERREUR : {e}")

    print(f"\n{'─'*50}")
    print(f"Résultat : {succes}/{len(tests)} fichiers parsés avec succès")
    taux = succes / len(tests) * 100
print(f"Taux de parsing : {taux:.0f}% (CDC exige >= 90%) — {'OK' if taux >= 90 else 'INSUFFISANT'}")
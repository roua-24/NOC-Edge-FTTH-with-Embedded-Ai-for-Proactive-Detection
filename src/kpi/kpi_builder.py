"""
Module : KPI — kpi_builder.py
Role   : Calcul des KPIs FTTH/GPON a partir du DataFrame brut
Entree : DataFrame brut (parse_csv dtype=kpi)
Sortie : DataFrame KPI enrichi avec colonnes calculees

KPIs calcules :
    debit_rx_mbps   — debit entrant en Mbit/s
    debit_tx_mbps   — debit sortant en Mbit/s
    error_rate_pct  — taux d'erreurs en %
    ont_up_count    — nombre d'ONT en etat UP (si df_ont fourni)
    ont_down_count  — nombre d'ONT en etat DOWN (si df_ont fourni)

Formule debit :
    debit_mbps = (ifInOctets_bytes * 8) / INTERVAL_SEC / 1_000_000
"""
import pandas as pd
import numpy as np
import logging
import time

logging.basicConfig(level=logging.INFO,
                    format="[kpi_builder] %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

LINK_CAPACITY_MBPS = 1000.0  # Capacite lien OLT (1 Gbit/s)
INTERVAL_SEC       = 300      # Resolution 5 minutes = 300 secondes


def compute_kpis(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule les KPIs FTTH a partir du DataFrame brut (dtype=kpi).

    Args:
        df_raw : DataFrame avec colonnes :
                 timestamp, ifInOctets_bytes, ifOutOctets_bytes,
                 ifInErrors, ifOutErrors, utilization_pct, label_anomaly

    Returns:
        pd.DataFrame enrichi avec colonnes :
        debit_rx_mbps, debit_tx_mbps, error_rate_pct
    """
    t0 = time.time()

    if df_raw.empty:
        raise ValueError("DataFrame vide - impossible de calculer les KPIs")

    # Verifier colonnes obligatoires
    required = ["ifInOctets_bytes", "ifOutOctets_bytes",
                "ifInErrors", "ifOutErrors"]
    missing = [c for c in required if c not in df_raw.columns]
    if missing:
        raise ValueError(f"Colonnes manquantes : {missing}")

    df = df_raw.copy()

    # ── Debit Rx / Tx (Mbit/s) ────────────────────────────────
    # Formule : octets * 8 bits / 300 secondes / 1_000_000
    df["debit_rx_mbps"] = (
        df["ifInOctets_bytes"] * 8 / INTERVAL_SEC / 1e6
    ).round(4)

    df["debit_tx_mbps"] = (
        df["ifOutOctets_bytes"] * 8 / INTERVAL_SEC / 1e6
    ).round(4)

    # Clip valeurs negatives impossibles
    df[["debit_rx_mbps", "debit_tx_mbps"]] = (
        df[["debit_rx_mbps", "debit_tx_mbps"]].clip(lower=0)
    )

    # ── Taux d'erreurs (%) ─────────────────────────────────────
    # Formule : (erreurs_in + erreurs_out) / (octets_in + octets_out) * 100
    total_octets = df["ifInOctets_bytes"] + df["ifOutOctets_bytes"]
    total_errors = df["ifInErrors"] + df["ifOutErrors"]

    df["error_rate_pct"] = (
        total_errors / total_octets.replace(0, np.nan) * 100
    ).fillna(0).round(6)

    elapsed = time.time() - t0
    n = len(df)
    logger.info(f"[OK] {n:,} points traites en {elapsed:.3f}s")

    if elapsed > 1.0:
        logger.warning(f"Performance : {elapsed:.2f}s > 1s CDC pour {n} points")

    return df.reset_index(drop=True)


def compute_ont_stats(df_ont: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule les statistiques ONT par timestamp.

    Args:
        df_ont : DataFrame avec colonnes :
                 timestamp, ont_id, rx_power_dBm,
                 tx_power_dBm, onuOperStatus

    Returns:
        pd.DataFrame groupe par timestamp avec :
        ont_up_count, ont_down_count, rx_power_mean, rx_power_min
    """
    if df_ont.empty:
        raise ValueError("DataFrame ONT vide")

    df_stats = df_ont.groupby("timestamp").agg(
        ont_up_count   = ("onuOperStatus", lambda x: (x == "up").sum()),
        ont_down_count = ("onuOperStatus", lambda x: (x == "do").sum()),
        rx_power_mean  = ("rx_power_dBm", "mean"),
        rx_power_min   = ("rx_power_dBm", "min"),
    ).reset_index()

    df_stats["rx_power_mean"] = df_stats["rx_power_mean"].round(2)
    df_stats["rx_power_min"]  = df_stats["rx_power_min"].round(2)

    logger.info(f"[OK] Stats ONT : {len(df_stats):,} timestamps")
    return df_stats


if __name__ == "__main__":  # pragma: no cover
    from src.parsing.parse_csv import parse_csv

    print("--- Test compute_kpis() ---")
    t0 = time.time()
    df_raw = parse_csv("data/csv/kpi_olt_port_1.csv", dtype="kpi")
    df_kpi = compute_kpis(df_raw)
    elapsed = time.time() - t0

    print(f"Shape    : {df_kpi.shape}")
    print(f"Colonnes : {list(df_kpi.columns)}")
    print(f"Temps    : {elapsed:.3f}s (CDC <= 1s pour 10k pts)")
    print(f"CDC perf : {'OK' if elapsed <= 1.0 else 'KO'}")
    print(df_kpi[["timestamp", "debit_rx_mbps",
                  "debit_tx_mbps", "error_rate_pct"]].head(5).to_string())

    print("\n--- Test compute_ont_stats() ---")
    df_ont  = parse_csv("data/csv/ont_status_timeseries.csv", dtype="ont")
    df_stats = compute_ont_stats(df_ont)
    print(f"Shape    : {df_stats.shape}")
    print(df_stats.head(3).to_string())
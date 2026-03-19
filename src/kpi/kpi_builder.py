"""
Module : KPI — kpi_builder.py
Rôle   : Calcul des KPIs FTTH/GPON à partir du DataFrame brut
Entrée : DataFrame brut (parse_csv / parse_snmp)
Sortie : DataFrame KPI avec colonnes calculées

KPIs calculés :
    debit_rx_mbps      — débit entrant en Mbit/s
    debit_tx_mbps      — débit sortant en Mbit/s
    utilization_pct    — taux d'utilisation en %
    error_rate_pct     — taux d'erreurs en %
    ont_up_count       — nombre d'ONT en état UP
    ont_down_count     — nombre d'ONT en état DOWN

Formule débit :
    debit_mbps = (delta_octets * 8) / delta_t_sec / 1_000_000
"""
import pandas as pd
import numpy as np


LINK_CAPACITY_MBPS = 1000.0   # Capacité lien OLT (1 Gbit/s)
INTERVAL_SEC = 300             # Résolution 5 minutes


def compute_kpis(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule les KPIs FTTH à partir du DataFrame brut.

    Parameters
    ----------
    df_raw : pd.DataFrame  — colonnes : timestamp, bytes_in, bytes_out, errors_in, errors_out

    Returns
    -------
    pd.DataFrame  — df_raw enrichi avec colonnes KPI
    """
    df = df_raw.copy()

    # Débit Rx / Tx (Mbit/s)
    df["debit_rx_mbps"] = (df["bytes_in"].diff() * 8) / INTERVAL_SEC / 1e6
    df["debit_tx_mbps"] = (df["bytes_out"].diff() * 8) / INTERVAL_SEC / 1e6
    df[["debit_rx_mbps", "debit_tx_mbps"]] = df[["debit_rx_mbps", "debit_tx_mbps"]].clip(lower=0)

    # Taux d'utilisation
    df["utilization_pct"] = (df["debit_rx_mbps"] / LINK_CAPACITY_MBPS * 100).round(2)

    # Taux d'erreurs
    total_pkts = df["bytes_in"] + df["bytes_out"]
    total_errs = df.get("errors_in", 0) + df.get("errors_out", 0)
    df["error_rate_pct"] = (total_errs / total_pkts.replace(0, np.nan) * 100).fillna(0).round(4)

    return df.dropna(subset=["debit_rx_mbps"]).reset_index(drop=True)

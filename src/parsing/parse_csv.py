"""
Module : PARSING — parse_csv.py
Rôle   : Lire les fichiers CSV synthétiques (KPIs, QoS, ONT, sécurité)
Entrée : chemin vers un fichier .csv
Sortie : pandas.DataFrame normalisé (timestamp en index)
"""
import pandas as pd
from pathlib import Path


SCHEMA = {
    "kpi": ["timestamp", "bytes_in", "bytes_out", "errors_in", "errors_out", "utilization"],
    "qos": ["timestamp", "latency_ms", "jitter_ms", "packet_loss_pct", "label"],
    "ont": ["timestamp", "ont_id", "rx_power_dbm", "tx_power_dbm", "status"],
    "security": ["timestamp", "event_type", "src_ip", "severity", "description"],
}


def parse_csv(filepath: str | Path, dtype: str = "kpi") -> pd.DataFrame:
    """
    Lit un fichier CSV et retourne un DataFrame avec timestamp parsé.

    Parameters
    ----------
    filepath : str | Path
    dtype    : str — type de fichier parmi : kpi, qos, ont, security

    Returns
    -------
    pd.DataFrame  avec colonne timestamp en datetime64
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Fichier introuvable : {filepath}")

    df = pd.read_csv(filepath)

    # Normalisation timestamp
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)

    return df

"""
Module : DÉTECTION IA — rules_engine.py
Rôle   : Alarmes basées sur seuils déterministes (complément à l'IA)
"""
import pandas as pd

THRESHOLDS = {
    "utilization_pct":  85.0,   # % — alerte saturation OLT
    "error_rate_pct":   1.0,    # % — alerte erreurs élevées
    "latency_ms":       100.0,  # ms — alerte dégradation QoS
    "jitter_ms":        20.0,   # ms
    "packet_loss_pct":  0.5,    # %
}


def apply_rules(df_kpi: pd.DataFrame) -> pd.DataFrame:
    """Ajoute une colonne 'rule_alarm' (bool) et 'rule_detail' (str) au DataFrame."""
    df = df_kpi.copy()
    df["rule_alarm"] = False
    df["rule_detail"] = ""

    for col, threshold in THRESHOLDS.items():
        if col in df.columns:
            mask = df[col] > threshold
            df.loc[mask, "rule_alarm"] = True
            df.loc[mask, "rule_detail"] += f"[{col}>{threshold}] "

    return df

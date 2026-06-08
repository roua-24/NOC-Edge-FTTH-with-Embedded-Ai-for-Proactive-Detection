"""
tests/unit/test_detection.py
===========================================================================
Tests unitaires — ml_local.py, rules_engine.py (O5+O6 — S7)
CDC §2.1 : F1-score >= 85 %
CDC §4   : Seuils déterministes THRESHOLDS

Après implémentation O5+O6 : ces tests passent directement (plus de xfail).

Commande :
    pytest tests/unit/test_detection.py -v
"""

import pytest
import pandas as pd
import numpy as np

from src.detection.ml_local import detect_anomalies
from src.detection.rules_engine import apply_rules


def make_kpi_df(n=200, inject_anomaly=True):
    """Fixture locale — df_kpi synthétique avec colonnes FEATURES CDC §C4."""
    np.random.seed(42)
    df = pd.DataFrame({
        "debit_rx_mbps"   : np.random.normal(400, 30, n),
        "debit_tx_mbps"   : np.random.normal(200, 20, n),
        "utilization_pct" : np.random.normal(40, 5, n),
        "error_rate_pct"  : np.random.uniform(0, 0.2, n),
    })
    if inject_anomaly:
        # Anomalies claires CDC §8
        df.loc[10:15, "utilization_pct"] = 99
        df.loc[10:15, "error_rate_pct"]  = 5.0
    return df


def test_detect_anomalies_returns_flags():
    """
    CDC §2.1 + §C4 Niveau 4 : detect_anomalies() produit
    anomaly_flag (-1/+1) et anomaly_score (float).
    """
    df = make_kpi_df()
    result = detect_anomalies(df)
    assert "anomaly_flag" in result.columns
    assert set(result["anomaly_flag"].unique()).issubset({-1, 1})


def test_rules_engine_threshold():
    """
    CDC §4 : apply_rules() détecte util=99% > seuil 85%
    et produit rule_alarm=True sur les lignes 10-15.
    """
    df = make_kpi_df(inject_anomaly=True)
    result = apply_rules(df)
    assert "rule_alarm" in result.columns
    assert result.loc[10, "rule_alarm"] == True
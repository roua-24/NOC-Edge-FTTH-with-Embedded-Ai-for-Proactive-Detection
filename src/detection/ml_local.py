"""
Module : DÉTECTION IA — ml_local.py
Rôle   : Détection d'anomalies non supervisée via Isolation Forest
Entrée : DataFrame KPI (df_kpi)
Sortie : df_kpi enrichi avec colonnes anomaly_flag (-1=anomalie, 1=normal) et anomaly_score

Cible F1-score >= 85% sur datasets synthétiques étiquetés
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

FEATURES      = ["debit_rx_mbps", "debit_tx_mbps", "utilization_pct", "error_rate_pct"]
CONTAMINATION = 0.05   # ~5% anomalies attendues (réglable)
RANDOM_STATE  = 42


def detect_anomalies(df_kpi: pd.DataFrame,
                     features: list[str] | None = None,
                     contamination: float = CONTAMINATION) -> pd.DataFrame:
    """
    Applique Isolation Forest sur les colonnes features du DataFrame KPI.

    Parameters
    ----------
    df_kpi        : pd.DataFrame  — DataFrame avec colonnes KPI calculées
    features      : list[str]     — colonnes utilisées (défaut : FEATURES)
    contamination : float         — proportion d'anomalies attendues [0.01–0.5]

    Returns
    -------
    pd.DataFrame enrichi avec :
        anomaly_flag  (int)   : -1 = anomalie, 1 = normal
        anomaly_score (float) : score de décision (plus négatif = plus anormal)
    """
    features = features or [f for f in FEATURES if f in df_kpi.columns]
    df = df_kpi.copy()
    X = df[features].fillna(0).values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(contamination=contamination, random_state=RANDOM_STATE, n_jobs=-1)
    df["anomaly_flag"]  = model.fit_predict(X_scaled)        # -1 ou 1
    df["anomaly_score"] = model.decision_function(X_scaled)  # négatif = suspect

    return df


def evaluate(df_kpi: pd.DataFrame, label_col: str = "label") -> dict:
    """Calcule precision, recall, F1 si colonne de labels disponible."""
    from sklearn.metrics import f1_score, precision_score, recall_score
    if label_col not in df_kpi.columns or "anomaly_flag" not in df_kpi.columns:
        raise ValueError("Colonnes manquantes pour évaluation")
    y_true = (df_kpi[label_col] == "anomaly").astype(int)
    y_pred = (df_kpi["anomaly_flag"] == -1).astype(int)
    return {
        "f1":        round(f1_score(y_true, y_pred, zero_division=0), 4),
        "precision": round(precision_score(y_true, y_pred, zero_division=0), 4),
        "recall":    round(recall_score(y_true, y_pred, zero_division=0), 4),
    }

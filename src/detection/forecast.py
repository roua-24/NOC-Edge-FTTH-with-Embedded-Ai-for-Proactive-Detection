"""
Module : DÉTECTION IA — forecast.py
Rôle   : Prévision de tendance court-terme par régression linéaire
Entrée : DataFrame KPI, colonne cible, horizon de prévision (en pas de 5 min)
Sortie : DataFrame avec prévisions et score de risque [0-100]
"""
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression


def forecast_trend(df_kpi: pd.DataFrame, target: str = "utilization_pct",
                   horizon: int = 12) -> dict:
    """
    Régression linéaire sur target, prévision horizon pas en avant.

    Parameters
    ----------
    df_kpi   : pd.DataFrame
    target   : str   — colonne à prévoir
    horizon  : int   — nombre de pas (5 min) → 12 = 1 heure

    Returns
    -------
    dict avec keys : forecast_values (list), risk_score (0-100), trend ('UP'/'DOWN'/'STABLE')
    """
    if target not in df_kpi.columns:
        raise ValueError(f"Colonne '{target}' introuvable")

    series = df_kpi[target].dropna().values
    X = np.arange(len(series)).reshape(-1, 1)
    model = LinearRegression().fit(X, series)

    future_X = np.arange(len(series), len(series) + horizon).reshape(-1, 1)
    preds = model.predict(future_X).tolist()

    max_pred  = max(preds)
    slope     = model.coef_[0]
    risk      = int(min(max(max_pred, 0), 100))
    trend     = "UP" if slope > 0.1 else ("DOWN" if slope < -0.1 else "STABLE")

    return {"forecast_values": preds, "risk_score": risk, "trend": trend, "slope": round(slope, 4)}

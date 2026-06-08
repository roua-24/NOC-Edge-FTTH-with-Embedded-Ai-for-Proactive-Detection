"""
forecast.py — Module Prévision : Régression linéaire (S7-S8)
===========================================================================
CDC §2.1  : Régression simple (tendance) — prévision horizon 1h
CDC §3    : Prévision → courbes de tendance et score de risque court-terme
CDC §C4   : Niveau 4 — signatures contractuelles forecast_trend()

Pipeline interne :
  1. X = np.arange(n).reshape(-1, 1)  — index temporel
  2. LinearRegression().fit(X, series) — ajustement tendance
  3. Prévision sur horizon (12 pas × 5min = 1h)
  4. risk_score = min(max(max_pred, 0), 100)
  5. trend = "UP" si slope > 0.1, "DOWN" si slope < -0.1, "STABLE" sinon

Commande :
  pytest tests/unit/test_forecast.py -v --cov=src/detection/forecast --cov-report=term-missing
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

logging.basicConfig(level=logging.INFO,
                    format="[forecast] %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

# ── Constantes CDC §C4 Niveau 4 ───────────────────────────────────────────
DEFAULT_TARGET  : str   = "utilization_pct"
DEFAULT_HORIZON : int   = 12        # 12 pas × 5min = 1h (CDC §C4)
SLOPE_UP        : float = 0.1      # seuil tendance montante
SLOPE_DOWN      : float = -0.1     # seuil tendance descendante
RISK_MAX        : float = 100.0    # score de risque plafonné (CDC §C4)
RISK_MIN        : float = 0.0


def forecast_trend(
    df_kpi: pd.DataFrame,
    target: str = DEFAULT_TARGET,
    horizon: int = DEFAULT_HORIZON,
) -> dict:

    if target not in df_kpi.columns:
        raise ValueError(
            f"Colonne cible '{target}' absente du DataFrame.\n"
            f"Colonnes disponibles : {list(df_kpi.columns)}"
        )

    series = df_kpi[target].dropna().values
    n = len(series)

    if n < 2:
        raise ValueError(
            f"Pas assez de points pour la régression : {n} ligne(s) — "
            f"minimum 2 requis."
        )

    result = _fit_and_predict(series, horizon)
    result["target"]   = target
    result["n_points"] = n
    return result


def predict_forecast(
    series: np.ndarray,
    horizon: int = DEFAULT_HORIZON,
) -> dict:
    """
    API alternative pour tab_diagnostics.py — accepte un array numpy brut.

    Paramètres
    ----------
    series  : 1-D array de valeurs historiques
    horizon : nombre de pas à prévoir (défaut : 12 = 1h)

    Retourne
    --------
    dict identique à forecast_trend() avec en plus :
        "forecast"  : np.ndarray — alias numpy de forecast_values
        "ci_upper"  : np.ndarray — borne IC supérieure (numpy pour fill_between)
        "ci_lower"  : np.ndarray — borne IC inférieure (numpy pour fill_between)
    """
    arr = np.asarray(series, dtype=float)
    n   = len(arr)

    if n < 2:
        zeros = np.zeros(horizon)
        return {
            "forecast_values": zeros.tolist(),
            "forecast":        zeros,
            "risk_score":      0.0,
            "trend":           "STABLE",
            "slope":           0.0,
            "ci_upper":        zeros,
            "ci_lower":        zeros,
            "horizon":         horizon,
            "n_points":        n,
        }

    result = _fit_and_predict(arr, horizon)
    # tab_diagnostics uses numpy arrays for matplotlib fill_between
    result["forecast"]  = np.array(result["forecast_values"])
    result["ci_upper"]  = np.array(result["ci_upper"])
    result["ci_lower"]  = np.array(result["ci_lower"])
    result["n_points"]  = n
    return result


# ── Noyau commun ──────────────────────────────────────────────────────────────
def _fit_and_predict(series: np.ndarray, horizon: int) -> dict:
    """Régression + prévision partagée par forecast_trend et predict_forecast."""
    n  = len(series)
    X  = np.arange(n).reshape(-1, 1)

    model = LinearRegression()
    model.fit(X, series)

    slope = float(model.coef_[0])

    # Prévision future (CDC §C4)
    X_future        = np.arange(n, n + horizon).reshape(-1, 1)
    forecast_values = model.predict(X_future).tolist()

    # IC 95% (± 1.96σ résidus)
    residuals = series - model.predict(X)
    sigma     = float(np.std(residuals))
    ci_upper  = [v + 1.96 * sigma for v in forecast_values]
    ci_lower  = [v - 1.96 * sigma for v in forecast_values]

    # Score de risque (CDC §C4)
    risk_score = float(min(max(max(forecast_values), RISK_MIN), RISK_MAX))

    # Tendance (CDC §C4)
    if slope > SLOPE_UP:
        trend = "UP"
    elif slope < SLOPE_DOWN:
        trend = "DOWN"
    else:
        trend = "STABLE"

    log.info(
        f"[forecast] n={n} | horizon={horizon} | "
        f"slope={slope:.4f} | trend={trend} | risk={risk_score:.1f}"
    )

    return {
        "forecast_values": [round(v, 4) for v in forecast_values],
        "risk_score":      round(risk_score, 2),
        "trend":           trend,
        "slope":           round(slope, 6),
        "horizon":         horizon,
        "ci_upper":        [round(v, 4) for v in ci_upper],
        "ci_lower":        [round(v, 4) for v in ci_lower],
    }
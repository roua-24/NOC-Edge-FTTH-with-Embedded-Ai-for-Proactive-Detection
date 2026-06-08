"""
tests/unit/test_forecast.py
===========================================================================
Tests unitaires — forecast.py (S7-S8)
CDC §2.1 : Régression simple — tendance court-terme
CDC §5   : Couverture >= 70 % sur modules critiques

Commande :
    pytest tests/unit/test_forecast.py -v --cov=src/detection/forecast --cov-report=term-missing
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.detection.forecast import (
    DEFAULT_HORIZON,
    DEFAULT_TARGET,
    SLOPE_DOWN,
    SLOPE_UP,
    forecast_trend,
)


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def df_tendance_montante() -> pd.DataFrame:
    """Série croissante — trend attendu : UP."""
    n = 100
    return pd.DataFrame({
        "timestamp"       : pd.date_range("2024-01-01", periods=n, freq="5min"),
        "utilization_pct" : np.linspace(20, 90, n),   # montée 20→90%
        "debit_rx_mbps"   : np.linspace(5, 25, n),
    })


@pytest.fixture
def df_tendance_descendante() -> pd.DataFrame:
    """Série décroissante — trend attendu : DOWN."""
    n = 100
    return pd.DataFrame({
        "timestamp"       : pd.date_range("2024-01-01", periods=n, freq="5min"),
        "utilization_pct" : np.linspace(90, 20, n),   # descente 90→20%
        "debit_rx_mbps"   : np.linspace(25, 5, n),
    })


@pytest.fixture
def df_tendance_stable() -> pd.DataFrame:
    """Série stable avec bruit faible — trend attendu : STABLE."""
    rng = np.random.default_rng(42)
    n = 100
    return pd.DataFrame({
        "timestamp"       : pd.date_range("2024-01-01", periods=n, freq="5min"),
        "utilization_pct" : 50.0 + rng.normal(0, 0.01, n),  # bruit minimal
        "debit_rx_mbps"   : 15.0 + rng.normal(0, 0.01, n),
    })


@pytest.fixture
def df_minimal() -> pd.DataFrame:
    """DataFrame minimal — 2 lignes (minimum requis)."""
    return pd.DataFrame({
        "utilization_pct" : [30.0, 35.0],
    })


@pytest.fixture
def df_sans_target() -> pd.DataFrame:
    """DataFrame sans utilization_pct — test ValueError."""
    return pd.DataFrame({
        "debit_rx_mbps" : [10.0, 15.0, 20.0],
    })


@pytest.fixture
def df_une_ligne() -> pd.DataFrame:
    """DataFrame avec 1 seule ligne — test ValueError."""
    return pd.DataFrame({
        "utilization_pct" : [50.0],
    })


# ── Tests structure sortie ─────────────────────────────────────────────────

class TestStructureSortie:
    """Tests de la structure du dict retourné par forecast_trend()."""

    def test_retourne_dict(self, df_tendance_montante):
        result = forecast_trend(df_tendance_montante)
        assert isinstance(result, dict)

    def test_cles_obligatoires(self, df_tendance_montante):
        """Toutes les clés CDC §C4 doivent être présentes."""
        result = forecast_trend(df_tendance_montante)
        for key in ["forecast_values", "risk_score", "trend", "slope",
                    "target", "horizon", "n_points"]:
            assert key in result, f"Clé manquante : {key}"

    def test_forecast_values_est_liste(self, df_tendance_montante):
        result = forecast_trend(df_tendance_montante)
        assert isinstance(result["forecast_values"], list)

    def test_forecast_values_longueur_horizon(self, df_tendance_montante):
        """forecast_values doit avoir exactement horizon éléments."""
        result = forecast_trend(df_tendance_montante, horizon=12)
        assert len(result["forecast_values"]) == 12

    def test_horizon_personnalise(self, df_tendance_montante):
        """horizon=6 → 6 valeurs prévues."""
        result = forecast_trend(df_tendance_montante, horizon=6)
        assert len(result["forecast_values"]) == 6

    def test_risk_score_entre_0_et_100(self, df_tendance_montante):
        """risk_score doit être entre 0 et 100 (CDC §C4)."""
        result = forecast_trend(df_tendance_montante)
        assert 0.0 <= result["risk_score"] <= 100.0

    def test_trend_valeur_valide(self, df_tendance_montante):
        """trend doit être UP, DOWN ou STABLE."""
        result = forecast_trend(df_tendance_montante)
        assert result["trend"] in {"UP", "DOWN", "STABLE"}

    def test_n_points_correct(self, df_tendance_montante):
        """n_points doit correspondre au nombre de lignes."""
        result = forecast_trend(df_tendance_montante)
        assert result["n_points"] == len(df_tendance_montante)

    def test_target_dans_resultat(self, df_tendance_montante):
        """La colonne cible doit être retournée dans le dict."""
        result = forecast_trend(df_tendance_montante, target="debit_rx_mbps")
        assert result["target"] == "debit_rx_mbps"

    def test_horizon_dans_resultat(self, df_tendance_montante):
        result = forecast_trend(df_tendance_montante, horizon=6)
        assert result["horizon"] == 6


# ── Tests tendances CDC §C4 ────────────────────────────────────────────────

class TestTendancesCDC:
    """Tests des 3 tendances UP / DOWN / STABLE (CDC §C4 Niveau 4)."""

    def test_trend_up_serie_croissante(self, df_tendance_montante):
        """Série linéaire croissante → trend = UP."""
        result = forecast_trend(df_tendance_montante)
        assert result["trend"] == "UP"
        assert result["slope"] > SLOPE_UP

    def test_trend_down_serie_decroissante(self, df_tendance_descendante):
        """Série linéaire décroissante → trend = DOWN."""
        result = forecast_trend(df_tendance_descendante)
        assert result["trend"] == "DOWN"
        assert result["slope"] < SLOPE_DOWN

    def test_trend_stable_serie_plate(self, df_tendance_stable):
        """Série quasi-stable → trend = STABLE."""
        result = forecast_trend(df_tendance_stable)
        assert result["trend"] == "STABLE"
        assert SLOPE_DOWN <= result["slope"] <= SLOPE_UP

    def test_forecast_montant_depasse_valeur_actuelle(self, df_tendance_montante):
        """Prévision sur série montante doit dépasser la dernière valeur."""
        last_val = df_tendance_montante["utilization_pct"].iloc[-1]
        result   = forecast_trend(df_tendance_montante)
        assert max(result["forecast_values"]) > last_val * 0.9  # marge 10%

    def test_risk_score_eleve_si_util_monte(self, df_tendance_montante):
        """Série montant vers 90% → risk_score élevé."""
        result = forecast_trend(df_tendance_montante)
        assert result["risk_score"] > 50.0

    def test_risk_score_plafonne_a_100(self):
        """risk_score ne peut pas dépasser 100 (CDC §C4)."""
        n = 50
        df = pd.DataFrame({
            "utilization_pct" : np.linspace(50, 200, n)  # dépasse 100%
        })
        result = forecast_trend(df)
        assert result["risk_score"] <= 100.0

    def test_risk_score_plancher_a_0(self, df_tendance_descendante):
        """risk_score ne peut pas être négatif (CDC §C4)."""
        result = forecast_trend(df_tendance_descendante)
        assert result["risk_score"] >= 0.0


# ── Tests target personnalisée ────────────────────────────────────────────

class TestTargetPersonnalisee:

    def test_target_debit_rx(self, df_tendance_montante):
        """forecast_trend() fonctionne sur debit_rx_mbps."""
        result = forecast_trend(df_tendance_montante, target="debit_rx_mbps")
        assert result["target"] == "debit_rx_mbps"
        assert len(result["forecast_values"]) == DEFAULT_HORIZON

    def test_target_absente_leve_valueerror(self, df_sans_target):
        """Colonne cible absente → ValueError."""
        with pytest.raises(ValueError, match="absente du DataFrame"):
            forecast_trend(df_sans_target)

    def test_df_une_ligne_leve_valueerror(self, df_une_ligne):
        """DataFrame < 2 lignes → ValueError."""
        with pytest.raises(ValueError, match="Pas assez de points"):
            forecast_trend(df_une_ligne)

    def test_df_minimal_2_lignes_fonctionne(self, df_minimal):
        """2 lignes — minimum requis — doit fonctionner."""
        result = forecast_trend(df_minimal)
        assert isinstance(result, dict)
        assert len(result["forecast_values"]) == DEFAULT_HORIZON


# ── Tests valeurs forecast ────────────────────────────────────────────────

class TestValeursForecast:

    def test_forecast_values_sont_float(self, df_tendance_montante):
        result = forecast_trend(df_tendance_montante)
        for v in result["forecast_values"]:
            assert isinstance(v, float)

    def test_slope_est_float(self, df_tendance_montante):
        result = forecast_trend(df_tendance_montante)
        assert isinstance(result["slope"], float)

    def test_forecast_continu_apres_serie(self, df_tendance_montante):
        """
        Les valeurs prévues doivent être dans la continuité
        de la série (pas de saut aberrant).
        """
        last_val = df_tendance_montante["utilization_pct"].iloc[-1]
        result   = forecast_trend(df_tendance_montante, horizon=3)
        first_pred = result["forecast_values"][0]
        # La première prévision doit être proche de la dernière valeur connue
        assert abs(first_pred - last_val) < 20.0, (
            f"Saut trop important : last={last_val:.1f}, pred={first_pred:.1f}"
        )
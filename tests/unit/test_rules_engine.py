"""
tests/unit/test_rules_engine.py
===========================================================================
Tests unitaires — rules_engine.py (O6 — S7)
CDC §4   : Seuils déterministes THRESHOLDS
CDC §5   : Couverture >= 70 % sur modules critiques

Compatibilité Python 3.14 + pandas >= 2.0 :
  rule_detail peut avoir dtype StringDtype (storage='python') ou object
  selon la version pandas — les deux sont valides pour une colonne str.

Commande :
    pytest tests/unit/test_rules_engine.py -v --cov=src/detection/rules_engine --cov-report=term-missing
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.detection.rules_engine import THRESHOLDS, apply_rules


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def df_normal() -> pd.DataFrame:
    """DataFrame sans aucune violation de seuil CDC §4."""
    n = 50
    return pd.DataFrame({
        "timestamp"       : pd.date_range("2024-01-01", periods=n, freq="5min"),
        "utilization_pct" : [50.0] * n,
        "error_rate_pct"  : [0.1]  * n,
        "debit_rx_mbps"   : [10.0] * n,
        "debit_tx_mbps"   : [5.0]  * n,
    })


@pytest.fixture
def df_avec_alarmes() -> pd.DataFrame:
    """DataFrame avec violations claires sur lignes 10-15."""
    n = 50
    df = pd.DataFrame({
        "timestamp"       : pd.date_range("2024-01-01", periods=n, freq="5min"),
        "utilization_pct" : [50.0] * n,
        "error_rate_pct"  : [0.1]  * n,
        "debit_rx_mbps"   : [10.0] * n,
        "debit_tx_mbps"   : [5.0]  * n,
    })
    df.loc[10:15, "utilization_pct"] = 99.0
    df.loc[10:15, "error_rate_pct"]  = 5.0
    return df


@pytest.fixture
def df_latency() -> pd.DataFrame:
    """DataFrame avec colonne latency_ms pour tester seuil 100ms."""
    n = 30
    df = pd.DataFrame({
        "timestamp"       : pd.date_range("2024-01-01", periods=n, freq="5min"),
        "utilization_pct" : [40.0] * n,
        "error_rate_pct"  : [0.1]  * n,
        "latency_ms"      : [50.0] * n,
    })
    df.loc[5:10, "latency_ms"] = 200.0
    return df


@pytest.fixture
def df_vide() -> pd.DataFrame:
    return pd.DataFrame()


# ── Helper compatibilité dtype string ─────────────────────────────────────

def _is_string_dtype(series: pd.Series) -> bool:
    """
    Vérifie que la série est de type string — compatible Python 3.14
    et toutes versions pandas.

    pandas >= 2.0 sur Python 3.14 peut retourner StringDtype au lieu
    de object. Les deux sont valides pour une colonne de chaînes.
    """
    dtype_str = str(series.dtype).lower()
    return (
        series.dtype == object
        or "string" in dtype_str
        or pd.api.types.is_string_dtype(series)
        or pd.api.types.is_object_dtype(series)
    )


# ── Tests structure sortie ─────────────────────────────────────────────────

class TestStructureSortie:

    def test_retourne_dataframe(self, df_normal):
        result = apply_rules(df_normal)
        assert isinstance(result, pd.DataFrame)

    def test_meme_nombre_lignes(self, df_normal):
        result = apply_rules(df_normal)
        assert len(result) == len(df_normal)

    def test_colonne_rule_alarm_presente(self, df_normal):
        result = apply_rules(df_normal)
        assert "rule_alarm" in result.columns

    def test_colonne_rule_detail_presente(self, df_normal):
        result = apply_rules(df_normal)
        assert "rule_detail" in result.columns

    def test_rule_alarm_est_bool(self, df_normal):
        result = apply_rules(df_normal)
        assert result["rule_alarm"].dtype == bool

    def test_rule_detail_est_str(self, df_normal):
        """
        rule_detail doit être une colonne de chaînes.
        Compatible Python 3.14 : StringDtype ou object sont tous les deux valides.
        """
        result = apply_rules(df_normal)
        assert _is_string_dtype(result["rule_detail"]), (
            f"dtype inattendu pour rule_detail : {result['rule_detail'].dtype}"
        )

    def test_rule_detail_valeurs_sont_str(self, df_normal):
        """Les valeurs de rule_detail doivent être des str (pas NaN)."""
        result = apply_rules(df_normal)
        assert result["rule_detail"].apply(lambda x: isinstance(x, str)).all()

    def test_dataframe_vide_leve_valueerror(self, df_vide):
        with pytest.raises(ValueError):
            apply_rules(df_vide)

    def test_colonnes_originales_preservees(self, df_normal):
        result = apply_rules(df_normal)
        for col in df_normal.columns:
            assert col in result.columns


# ── Tests seuils CDC §4 ───────────────────────────────────────────────────

class TestSeuilsCDC:

    def test_pas_alarme_sur_df_normal(self, df_normal):
        result = apply_rules(df_normal)
        assert result["rule_alarm"].sum() == 0

    def test_alarme_sur_utilization_depasse(self, df_avec_alarmes):
        result = apply_rules(df_avec_alarmes)
        assert result.loc[10, "rule_alarm"] == True

    def test_alarme_sur_error_rate_depasse(self, df_avec_alarmes):
        result = apply_rules(df_avec_alarmes)
        assert result.loc[12, "rule_alarm"] == True

    def test_alarme_sur_latency_depasse(self, df_latency):
        result = apply_rules(df_latency)
        assert result.loc[5, "rule_alarm"] == True

    def test_pas_alarme_sous_seuil_utilization(self):
        df = pd.DataFrame({
            "utilization_pct" : [84.9],
            "error_rate_pct"  : [0.1],
        })
        result = apply_rules(df)
        assert result.loc[0, "rule_alarm"] == False

    def test_alarme_exactement_seuil_plus_epsilon(self):
        df = pd.DataFrame({
            "utilization_pct" : [85.1],
            "error_rate_pct"  : [0.1],
        })
        result = apply_rules(df)
        assert result.loc[0, "rule_alarm"] == True

    def test_nombre_alarmes_correct(self, df_avec_alarmes):
        result = apply_rules(df_avec_alarmes)
        assert result["rule_alarm"].sum() == 6

    def test_lignes_normales_pas_alarme(self, df_avec_alarmes):
        result = apply_rules(df_avec_alarmes)
        normales = result.loc[~result.index.isin(range(10, 16))]
        assert normales["rule_alarm"].sum() == 0


# ── Tests rule_detail ─────────────────────────────────────────────────────

class TestRuleDetail:

    def test_detail_vide_si_pas_alarme(self, df_normal):
        result = apply_rules(df_normal)
        assert (result["rule_detail"] == "").all()

    def test_detail_non_vide_si_alarme(self, df_avec_alarmes):
        result = apply_rules(df_avec_alarmes)
        alarmes = result[result["rule_alarm"]]
        assert (alarmes["rule_detail"] != "").all()

    def test_detail_contient_util(self, df_avec_alarmes):
        result = apply_rules(df_avec_alarmes)
        assert "util" in result.loc[10, "rule_detail"]

    def test_detail_contient_error(self, df_avec_alarmes):
        result = apply_rules(df_avec_alarmes)
        assert "error" in result.loc[10, "rule_detail"]


# ── Tests colonnes absentes ───────────────────────────────────────────────

class TestColonnesAbsentes:

    def test_fonctionne_sans_latency_ms(self, df_normal):
        assert "latency_ms" not in df_normal.columns
        result = apply_rules(df_normal)
        assert "rule_alarm" in result.columns

    def test_fonctionne_sans_aucune_colonne_threshold(self):
        df = pd.DataFrame({
            "timestamp"     : pd.date_range("2024-01-01", periods=5, freq="5min"),
            "debit_rx_mbps" : [10.0] * 5,
        })
        result = apply_rules(df)
        assert result["rule_alarm"].sum() == 0

    def test_thresholds_valeurs_cdc(self):
        """Vérification des valeurs exactes THRESHOLDS (CDC §4)."""
        assert THRESHOLDS["utilization_pct"] == 85.0
        assert THRESHOLDS["error_rate_pct"]  == 1.0
        assert THRESHOLDS["latency_ms"]      == 100.0
        assert THRESHOLDS["jitter_ms"]       == 20.0
        assert THRESHOLDS["packet_loss_pct"] == 0.5
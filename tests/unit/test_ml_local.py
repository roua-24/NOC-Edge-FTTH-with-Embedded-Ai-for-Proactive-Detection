"""
tests/unit/test_ml_local.py
===========================================================================
Tests unitaires — ml_local.py (O5 — S7)
CDC §2.1 : F1-score >= 85 % sur dataset synthétique labélisé
CDC §5   : Couverture >= 70 % sur modules critiques

Commande :
    pytest tests/unit/test_ml_local.py -v --cov=src/detection --cov-report=term-missing
"""

import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.detection.ml_local import (
    CONTAMINATION,
    FEATURES,
    RANDOM_STATE,
    _run_cli,
    detect_anomalies,
    evaluate,
)


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def df_kpi_labeled() -> pd.DataFrame:
    """
    DataFrame synthétique avec FEATURES + label_anomaly.
    Anomalies injectées sur lignes 10-35 : séparation claire.
    """
    rng = np.random.default_rng(42)
    n = 500
    df = pd.DataFrame({
        "timestamp"       : pd.date_range("2024-01-01", periods=n, freq="5min"),
        "debit_rx_mbps"   : rng.uniform(5, 30, n),
        "debit_tx_mbps"   : rng.uniform(2, 15, n),
        "utilization_pct" : rng.uniform(20, 80, n),
        "error_rate_pct"  : rng.uniform(0, 0.5, n),
        "label_anomaly"   : 0,
    })
    anomaly_idx = list(range(10, 36))
    df.loc[anomaly_idx, "utilization_pct"] = 99.0
    df.loc[anomaly_idx, "error_rate_pct"]  = 5.0
    df.loc[anomaly_idx, "debit_rx_mbps"]   = 200.0
    df.loc[anomaly_idx, "label_anomaly"]   = 1
    return df


@pytest.fixture
def df_kpi_no_label(df_kpi_labeled) -> pd.DataFrame:
    return df_kpi_labeled.drop(columns=["label_anomaly"])


@pytest.fixture
def df_kpi_trop_petit() -> pd.DataFrame:
    return pd.DataFrame({
        "debit_rx_mbps"   : [10.0] * 5,
        "debit_tx_mbps"   : [5.0]  * 5,
        "utilization_pct" : [50.0] * 5,
        "error_rate_pct"  : [0.1]  * 5,
        "label_anomaly"   : [0]    * 5,
    })


@pytest.fixture
def df_kpi_feature_manquante(df_kpi_labeled) -> pd.DataFrame:
    return df_kpi_labeled.drop(columns=["debit_tx_mbps"])


@pytest.fixture
def csv_kpi_labeled(df_kpi_labeled, tmp_path) -> Path:
    """CSV temporaire simulant df_kpi_labeled.csv — pour test _run_cli()."""
    p = tmp_path / "df_kpi_labeled.csv"
    df_kpi_labeled.to_csv(p, index=False)
    return p


# ── Tests detect_anomalies() ───────────────────────────────────────────────

class TestDetectAnomalies:

    def test_retourne_dataframe(self, df_kpi_labeled):
        result = detect_anomalies(df_kpi_labeled)
        assert isinstance(result, pd.DataFrame)

    def test_meme_nombre_lignes(self, df_kpi_labeled):
        result = detect_anomalies(df_kpi_labeled)
        assert len(result) == len(df_kpi_labeled)

    def test_colonne_anomaly_flag_presente(self, df_kpi_labeled):
        result = detect_anomalies(df_kpi_labeled)
        assert "anomaly_flag" in result.columns

    def test_colonne_anomaly_score_presente(self, df_kpi_labeled):
        result = detect_anomalies(df_kpi_labeled)
        assert "anomaly_score" in result.columns

    def test_anomaly_flag_valeurs_valides(self, df_kpi_labeled):
        result = detect_anomalies(df_kpi_labeled)
        assert set(result["anomaly_flag"].unique()).issubset({-1, 1})

    def test_anomaly_score_est_float(self, df_kpi_labeled):
        result = detect_anomalies(df_kpi_labeled)
        assert result["anomaly_score"].dtype == float

    def test_colonnes_features_preservees(self, df_kpi_labeled):
        result = detect_anomalies(df_kpi_labeled)
        for feat in FEATURES:
            assert feat in result.columns

    def test_feature_manquante_leve_valueerror(self, df_kpi_feature_manquante):
        with pytest.raises(ValueError, match="Colonnes FEATURES manquantes"):
            detect_anomalies(df_kpi_feature_manquante)

    def test_dataframe_trop_petit_leve_valueerror(self, df_kpi_trop_petit):
        with pytest.raises(ValueError, match="trop petit"):
            detect_anomalies(df_kpi_trop_petit)

    def test_detecte_anomalies_injectees(self, df_kpi_labeled):
        result = detect_anomalies(df_kpi_labeled)
        anomaly_idx = list(range(10, 36))
        detection_rate = (result.loc[anomaly_idx, "anomaly_flag"] == -1).mean()
        assert detection_rate >= 0.5

    def test_contamination_personnalisee(self, df_kpi_labeled):
        result = detect_anomalies(df_kpi_labeled, contamination=0.10)
        ratio = (result["anomaly_flag"] == -1).mean()
        assert 0.05 <= ratio <= 0.20

    def test_features_personnalisees(self, df_kpi_labeled):
        result = detect_anomalies(df_kpi_labeled, features=["utilization_pct"])
        assert "anomaly_flag" in result.columns

    def test_determinisme_random_state(self, df_kpi_labeled):
        r1 = detect_anomalies(df_kpi_labeled)
        r2 = detect_anomalies(df_kpi_labeled)
        pd.testing.assert_series_equal(r1["anomaly_flag"], r2["anomaly_flag"])


# ── Tests evaluate() ──────────────────────────────────────────────────────

class TestEvaluate:

    def test_retourne_dict(self, df_kpi_labeled):
        df_result = detect_anomalies(df_kpi_labeled)
        assert isinstance(evaluate(df_result), dict)

    def test_cles_obligatoires(self, df_kpi_labeled):
        metrics = evaluate(detect_anomalies(df_kpi_labeled))
        for key in ["f1", "precision", "recall"]:
            assert key in metrics

    def test_f1_entre_0_et_1(self, df_kpi_labeled):
        metrics = evaluate(detect_anomalies(df_kpi_labeled))
        assert 0.0 <= metrics["f1"] <= 1.0

    def test_f1_cdc_85_pct(self, df_kpi_labeled):
        """CDC §2.1 : F1-score >= 85 %."""
        metrics = evaluate(detect_anomalies(df_kpi_labeled))
        assert metrics["f1"] >= 0.85, (
            f"CDC §2.1 non atteint : F1={metrics['f1']:.3f} < 0.85"
        )

    def test_precision_entre_0_et_1(self, df_kpi_labeled):
        metrics = evaluate(detect_anomalies(df_kpi_labeled))
        assert 0.0 <= metrics["precision"] <= 1.0

    def test_recall_entre_0_et_1(self, df_kpi_labeled):
        metrics = evaluate(detect_anomalies(df_kpi_labeled))
        assert 0.0 <= metrics["recall"] <= 1.0

    def test_n_total_correct(self, df_kpi_labeled):
        metrics = evaluate(detect_anomalies(df_kpi_labeled))
        assert metrics["n_total"] == len(df_kpi_labeled)

    def test_sans_anomaly_flag_leve_valueerror(self, df_kpi_labeled):
        with pytest.raises(ValueError, match="anomaly_flag absent"):
            evaluate(df_kpi_labeled)

    def test_sans_label_col_leve_valueerror(self, df_kpi_no_label):
        df_result = detect_anomalies(df_kpi_no_label)
        with pytest.raises(ValueError, match="label_anomaly"):
            evaluate(df_result)

    def test_n_anomalies_reelles_correct(self, df_kpi_labeled):
        metrics = evaluate(detect_anomalies(df_kpi_labeled))
        assert metrics["n_anomalies_reelles"] == df_kpi_labeled["label_anomaly"].sum()


# ── Test _run_cli() — couvre lignes 186-203 ───────────────────────────────

class TestRunCli:
    """
    Tests de _run_cli() — extrait du bloc __main__ pour être testable.
    Couvre les lignes 186-203 de ml_local.py (précédemment non couvertes).
    """

    def test_run_cli_retourne_dict(self, csv_kpi_labeled):
        """_run_cli() doit retourner un dict avec les métriques."""
        metrics = _run_cli(csv_path=csv_kpi_labeled)
        assert isinstance(metrics, dict)
        assert "f1" in metrics

    def test_run_cli_f1_valide(self, csv_kpi_labeled):
        """_run_cli() doit produire un F1 entre 0 et 1."""
        metrics = _run_cli(csv_path=csv_kpi_labeled)
        assert 0.0 <= metrics["f1"] <= 1.0

    def test_run_cli_affiche_shape(self, csv_kpi_labeled, capsys):
        """_run_cli() doit afficher Shape dans la sortie."""
        _run_cli(csv_path=csv_kpi_labeled)
        captured = capsys.readouterr()
        assert "Shape" in captured.out

    def test_run_cli_affiche_f1(self, csv_kpi_labeled, capsys):
        """_run_cli() doit afficher F1-score dans la sortie."""
        _run_cli(csv_path=csv_kpi_labeled)
        captured = capsys.readouterr()
        assert "F1-score" in captured.out
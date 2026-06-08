"""
tests/unit/test_prepare_labels.py
===========================================================================
Tests unitaires — prepare_labels.py (S7 — préparation df_kpi labélisé)
CDC §2.1 : Valide que le df_kpi labélisé respecte le schéma attendu
           par detect_anomalies() avant l'implémentation IsolationForest.
CDC §5   : Couverture >= 70 % sur modules critiques.

Schéma réel kpi_olt_port_1.csv :
    timestamp, ifInOctets_bytes, ifOutOctets_bytes,
    ifInErrors, ifOutErrors, utilization_pct, label_anomaly

Commande :
    pytest tests/unit/test_prepare_labels.py -v
    pytest tests/unit/test_prepare_labels.py -v --cov=scripts --cov-report=term-missing
"""

import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.prepare_labels import (
    FEATURES,
    LABEL_COL,
    THRESHOLD_ERROR,
    THRESHOLD_UTIL,
    derive_labels,
    export_labeled,
    load_raw_csv,
    validate_schema,
)


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def df_raw_avec_labels() -> pd.DataFrame:
    """
    DataFrame style CSV brut réel (colonnes ifInOctets_bytes etc.)
    avec label_anomaly présent — simule kpi_olt_port_1.csv (CDC §8).
    """
    rng = np.random.default_rng(42)
    n = 100
    return pd.DataFrame({
        "timestamp"         : pd.date_range("2024-01-01", periods=n, freq="5min"),
        "ifInOctets_bytes"  : rng.integers(1_000_000, 200_000_000, n),
        "ifOutOctets_bytes" : rng.integers(500_000,   100_000_000, n),
        "ifInErrors"        : rng.integers(0, 10, n),
        "ifOutErrors"       : rng.integers(0, 5, n),
        "utilization_pct"   : rng.uniform(20, 95, n),
        "label_anomaly"     : rng.choice([0, 1], size=n, p=[0.95, 0.05]),
    })


@pytest.fixture
def df_raw_sans_labels() -> pd.DataFrame:
    """DataFrame brut réel SANS label_anomaly — fallback seuils CDC §4."""
    rng = np.random.default_rng(77)
    n = 80
    return pd.DataFrame({
        "timestamp"         : pd.date_range("2024-02-01", periods=n, freq="5min"),
        "ifInOctets_bytes"  : rng.integers(1_000_000, 200_000_000, n),
        "ifOutOctets_bytes" : rng.integers(500_000,   100_000_000, n),
        "ifInErrors"        : rng.integers(0, 10, n),
        "ifOutErrors"       : rng.integers(0, 5, n),
        "utilization_pct"   : rng.uniform(20, 95, n),
    })


@pytest.fixture
def df_kpi_with_labels() -> pd.DataFrame:
    """DataFrame style df_kpi (FEATURES calculées) + label_anomaly."""
    rng = np.random.default_rng(42)
    n = 200
    return pd.DataFrame({
        "timestamp"       : pd.date_range("2024-01-01", periods=n, freq="5min"),
        "debit_rx_mbps"   : rng.uniform(5, 30, n),
        "debit_tx_mbps"   : rng.uniform(2, 15, n),
        "utilization_pct" : rng.uniform(20, 95, n),
        "error_rate_pct"  : rng.uniform(0, 2, n),
        "label_anomaly"   : rng.choice([0, 1], size=n, p=[0.95, 0.05]),
    })


@pytest.fixture
def df_kpi_no_labels() -> pd.DataFrame:
    """DataFrame style df_kpi SANS label_anomaly — fallback CDC §4."""
    rng = np.random.default_rng(99)
    n = 100
    return pd.DataFrame({
        "timestamp"       : pd.date_range("2024-02-01", periods=n, freq="5min"),
        "debit_rx_mbps"   : rng.uniform(5, 30, n),
        "debit_tx_mbps"   : rng.uniform(2, 15, n),
        "utilization_pct" : rng.uniform(20, 95, n),
        "error_rate_pct"  : rng.uniform(0, 2, n),
    })


@pytest.fixture
def df_kpi_missing_feature() -> pd.DataFrame:
    """DataFrame avec debit_tx_mbps manquant."""
    return pd.DataFrame({
        "timestamp"       : pd.date_range("2024-01-01", periods=10, freq="5min"),
        "debit_rx_mbps"   : [10.0] * 10,
        "utilization_pct" : [50.0] * 10,
        "error_rate_pct"  : [0.1]  * 10,
        "label_anomaly"   : [0]    * 10,
    })


# ── Tests load_raw_csv() ───────────────────────────────────────────────────

class TestLoadRawCsv:
    """
    Tests de load_raw_csv() — chargement CSV brut réel.
    Couvre les lignes 45-70 de prepare_labels.py (hausse couverture).
    """

    def test_charge_csv_valide(self, df_raw_avec_labels, tmp_path):
        """CSV brut valide → DataFrame chargé sans erreur."""
        p = tmp_path / "kpi_test.csv"
        df_raw_avec_labels.to_csv(p, index=False)
        result = load_raw_csv(p)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(df_raw_avec_labels)

    def test_colonnes_brutes_presentes(self, df_raw_avec_labels, tmp_path):
        """Colonnes ifInOctets_bytes etc. doivent être présentes."""
        p = tmp_path / "kpi_test.csv"
        df_raw_avec_labels.to_csv(p, index=False)
        result = load_raw_csv(p)
        for col in ["ifInOctets_bytes", "ifOutOctets_bytes", "ifInErrors"]:
            assert col in result.columns, f"Colonne manquante : {col}"

    def test_timestamp_parse_en_datetime(self, df_raw_avec_labels, tmp_path):
        """timestamp doit être parsé en datetime64."""
        p = tmp_path / "kpi_test.csv"
        df_raw_avec_labels.to_csv(p, index=False)
        result = load_raw_csv(p)
        assert pd.api.types.is_datetime64_any_dtype(result["timestamp"])

    def test_tri_chronologique(self, df_raw_avec_labels, tmp_path):
        """Le DataFrame doit être trié par timestamp."""
        df_melange = df_raw_avec_labels.sample(frac=1, random_state=0)
        p = tmp_path / "kpi_melange.csv"
        df_melange.to_csv(p, index=False)
        result = load_raw_csv(p)
        assert result["timestamp"].is_monotonic_increasing

    def test_fichier_manquant_leve_exception(self, tmp_path):
        """Fichier inexistant → exception (FileNotFoundError ou ValueError)."""
        p = tmp_path / "inexistant.csv"
        with pytest.raises(Exception):
            load_raw_csv(p)

    def test_colonne_brute_manquante_leve_valueerror(self, tmp_path):
        """CSV sans ifInOctets_bytes → ValueError."""
        df_incomplet = pd.DataFrame({
            "timestamp"     : pd.date_range("2024-01-01", periods=5, freq="5min"),
            "ifOutOctets_bytes" : [100] * 5,
            # ifInOctets_bytes manquant
        })
        p = tmp_path / "incomplet.csv"
        df_incomplet.to_csv(p, index=False)
        with pytest.raises(ValueError, match="Colonnes brutes manquantes"):
            load_raw_csv(p)


# ── Tests export_labeled() ─────────────────────────────────────────────────

class TestExportLabeled:
    """Tests de export_labeled() — couverture lignes 120-130."""

    def test_export_cree_fichier(self, df_kpi_with_labels, tmp_path):
        """export_labeled() doit créer le fichier CSV."""
        out = tmp_path / "df_kpi_labeled.csv"
        export_labeled(df_kpi_with_labels, out)
        assert out.exists()

    def test_export_contient_features(self, df_kpi_with_labels, tmp_path):
        """CSV exporté doit contenir toutes les FEATURES + label_anomaly."""
        out = tmp_path / "df_kpi_labeled.csv"
        export_labeled(df_kpi_with_labels, out)
        df_lu = pd.read_csv(out)
        for col in FEATURES + [LABEL_COL]:
            assert col in df_lu.columns, f"Colonne manquante dans export : {col}"

    def test_export_meme_nombre_lignes(self, df_kpi_with_labels, tmp_path):
        """CSV exporté doit avoir le même nombre de lignes que l'entrée."""
        out = tmp_path / "df_kpi_labeled.csv"
        export_labeled(df_kpi_with_labels, out)
        df_lu = pd.read_csv(out)
        assert len(df_lu) == len(df_kpi_with_labels)

    def test_export_cree_repertoire_si_absent(self, df_kpi_with_labels, tmp_path):
        """export_labeled() crée le répertoire parent si absent."""
        out = tmp_path / "nouveau_dossier" / "df_kpi_labeled.csv"
        export_labeled(df_kpi_with_labels, out)
        assert out.exists()


# ── Tests derive_labels() ──────────────────────────────────────────────────

class TestDeriveLabels:
    """Tests de derive_labels(df_kpi, df_raw) — signature 2 arguments."""

    def test_conserve_labels_existants(self, df_kpi_with_labels):
        """Si label_anomaly dans df_raw → conservé tel quel (CDC §8)."""
        original = df_kpi_with_labels[LABEL_COL].copy()
        result = derive_labels(df_kpi_with_labels.copy(), df_kpi_with_labels)
        pd.testing.assert_series_equal(
            result[LABEL_COL].astype(int),
            original.astype(int),
            check_names=False,
        )

    def test_labels_binaires_avec_source(self, df_kpi_with_labels):
        """label_anomaly doit être 0 ou 1 uniquement."""
        result = derive_labels(df_kpi_with_labels.copy(), df_kpi_with_labels)
        assert result[LABEL_COL].isin([0, 1]).all()

    def test_fallback_seuils_cdc(self, df_kpi_no_labels):
        """Sans label_anomaly dans df_raw → fallback seuils CDC §4."""
        result = derive_labels(df_kpi_no_labels.copy(), df_kpi_no_labels)
        assert LABEL_COL in result.columns
        assert result[LABEL_COL].isin([0, 1]).all()

    def test_fallback_coherent_avec_seuils(self, df_kpi_no_labels):
        """Fallback : anomalie SI util>85% OU error_rate>1% (CDC §4)."""
        result = derive_labels(df_kpi_no_labels.copy(), df_kpi_no_labels)
        expected = (
            (df_kpi_no_labels["utilization_pct"] > THRESHOLD_UTIL) |
            (df_kpi_no_labels["error_rate_pct"]  > THRESHOLD_ERROR)
        ).astype(int)
        pd.testing.assert_series_equal(
            result[LABEL_COL], expected, check_names=False,
        )

    def test_ratio_anomalies_raisonnable(self, df_kpi_with_labels):
        """Ratio anomalies entre 1 % et 30 % (CDC §8 cible ~5 %)."""
        result = derive_labels(df_kpi_with_labels.copy(), df_kpi_with_labels)
        ratio = result[LABEL_COL].mean()
        assert 0.01 <= ratio <= 0.30, f"Ratio inattendu : {ratio:.2%}"

    def test_label_depuis_df_raw_distinct(self, df_kpi_with_labels):
        """
        Cas réel : df_kpi sans label_anomaly + df_raw avec label_anomaly.
        derive_labels() doit réinjecter depuis df_raw.
        """
        df_kpi_sans = df_kpi_with_labels.drop(columns=[LABEL_COL])
        result = derive_labels(df_kpi_sans.copy(), df_kpi_with_labels)
        assert LABEL_COL in result.columns
        assert result[LABEL_COL].isin([0, 1]).all()
        pd.testing.assert_series_equal(
            result[LABEL_COL].reset_index(drop=True),
            df_kpi_with_labels[LABEL_COL].astype(int).reset_index(drop=True),
            check_names=False,
        )


# ── Tests validate_schema() ────────────────────────────────────────────────

class TestValidateSchema:
    """Tests de validate_schema() — conformité CDC §C4 Niveau 4."""

    def test_schema_valide_passe(self, df_kpi_with_labels):
        """DataFrame complet → aucune exception."""
        df = derive_labels(df_kpi_with_labels.copy(), df_kpi_with_labels)
        validate_schema(df)

    def test_schema_invalide_feature_manquante(self, df_kpi_missing_feature):
        """Feature manquante (debit_tx_mbps) → ValueError."""
        df = derive_labels(df_kpi_missing_feature.copy(), df_kpi_missing_feature)
        with pytest.raises(ValueError, match="colonnes manquantes"):
            validate_schema(df)

    def test_schema_sans_label_col(self, df_kpi_no_labels):
        """validate_schema() sans label_anomaly → ValueError."""
        with pytest.raises(ValueError):
            validate_schema(df_kpi_no_labels)

    def test_toutes_features_presentes(self, df_kpi_with_labels):
        """Toutes les FEATURES doivent être dans le DataFrame final."""
        df = derive_labels(df_kpi_with_labels.copy(), df_kpi_with_labels)
        for feat in FEATURES:
            assert feat in df.columns, f"Feature manquante : {feat}"

    def test_label_col_present(self, df_kpi_with_labels):
        """label_anomaly doit être présent après derive_labels."""
        result = derive_labels(df_kpi_with_labels.copy(), df_kpi_with_labels)
        assert LABEL_COL in result.columns

    def test_label_valeurs_binaires_strict(self):
        """label_anomaly avec valeur 2 → AssertionError."""
        df = pd.DataFrame({
            "timestamp"       : pd.date_range("2024-01-01", periods=5, freq="5min"),
            "debit_rx_mbps"   : [10.0] * 5,
            "debit_tx_mbps"   : [5.0]  * 5,
            "utilization_pct" : [50.0] * 5,
            "error_rate_pct"  : [0.1]  * 5,
            "label_anomaly"   : [0, 1, 0, 2, 0],
        })
        with pytest.raises(AssertionError):
            validate_schema(df)


# ── Fixture dédiée qualité ML ──────────────────────────────────────────────

@pytest.fixture
def df_kpi_ml_qualite() -> pd.DataFrame:
    """
    Fixture dédiée à TestMLQualite — anomalies clairement séparées
    des points normaux pour permettre à IsolationForest d'atteindre
    F1 >= 85 % (CDC §2.1).

    Logique : les anomalies (lignes 10-35) ont des valeurs extrêmes
    très distinctes des normaux → séparation claire dans l'espace
    des FEATURES → IsolationForest les détecte facilement.

    Cette fixture est différente de df_kpi_with_labels qui utilise
    des labels aléatoires sans séparation dans les valeurs — adaptée
    pour tester derive_labels() et validate_schema() mais pas le F1.
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
    # Injection anomalies clairement séparées — CDC §8
    anomaly_idx = list(range(10, 36))
    df.loc[anomaly_idx, "utilization_pct"] = 99.0   # >> seuil 85%
    df.loc[anomaly_idx, "error_rate_pct"]  = 5.0    # >> seuil 1%
    df.loc[anomaly_idx, "debit_rx_mbps"]   = 200.0  # très éloigné
    df.loc[anomaly_idx, "label_anomaly"]   = 1
    return df


# ── Tests qualité ML ───────────────────────────────────────────────────────

class TestMLQualite:
    """
    Tests de qualité ML — O5 S7 implémenté.
    CDC §2.1 : F1-score >= 85 % après detect_anomalies() + evaluate().
    Utilise df_kpi_ml_qualite : anomalies clairement séparées des normaux.
    """

    def test_f1_score_cdc(self, df_kpi_ml_qualite):
        """
        CDC §2.1 : F1-score >= 85 % sur dataset labélisé.
        Les anomalies injectées (util=99%, error=5%, debit=200)
        sont clairement distinctes des normaux — IsolationForest
        les détecte avec un F1 élevé.
        """
        from src.detection.ml_local import detect_anomalies, evaluate
        df = derive_labels(df_kpi_ml_qualite.copy(), df_kpi_ml_qualite)
        df_result = detect_anomalies(df)
        metrics   = evaluate(df_result, label_col=LABEL_COL)
        assert metrics["f1"] >= 0.85, (
            f"CDC §2.1 non atteint : F1={metrics['f1']:.3f} < 0.85\n"
            f"Anomalies réelles={metrics['n_anomalies_reelles']} | "
            f"Détectées={metrics['n_anomalies_detectees']}"
        )

    def test_colonnes_anomaly_flag_score(self, df_kpi_ml_qualite):
        """detect_anomalies() doit ajouter anomaly_flag et anomaly_score."""
        from src.detection.ml_local import detect_anomalies
        df = derive_labels(df_kpi_ml_qualite.copy(), df_kpi_ml_qualite)
        df_result = detect_anomalies(df)
        assert "anomaly_flag"  in df_result.columns
        assert "anomaly_score" in df_result.columns
        assert df_result["anomaly_flag"].isin([-1, 1]).all()
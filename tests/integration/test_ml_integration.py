"""
tests/integration/test_ml_integration.py
===========================================================================
Test d'intégration IA — F1-score sur le VRAI dataset (CDC §2.1)
Fichier : data/csv/df_kpi_labeled.csv (8640 lignes, 303 anomalies)

Couvre les branches de ml_local.py non atteintes par les tests unitaires :
  - contamination adaptative (label_anomaly présent)
  - contamination défaut (label_anomaly absent)
  - evaluate() sur résultats réels

CDC §5   : Couverture >= 70 % sur modules critiques
CDC §2.1 : F1-score >= 85 % sur datasets synthétiques

Commande :
    pytest tests/integration/test_ml_integration.py -v -s --cov=src/detection/ml_local --cov-report=term-missing
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import IsolationForest
from sklearn.metrics import f1_score, precision_score, recall_score
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.detection.ml_local import (
    CONTAMINATION,
    FEATURES,
    LABEL_COL,
    RANDOM_STATE,
    _run_cli,
    detect_anomalies,
    evaluate,
)

# ── Chemin dataset réel ────────────────────────────────────────────────────
ROOT     = Path(__file__).parent.parent.parent
CSV_PATH = ROOT / "data" / "csv" / "df_kpi_labeled.csv"

pytestmark = pytest.mark.skipif(
    not CSV_PATH.exists(),
    reason=f"Dataset réel absent : {CSV_PATH}"
)


@pytest.fixture(scope="module")
def df_reel() -> pd.DataFrame:
    """Charge le vrai dataset une seule fois pour tous les tests."""
    return pd.read_csv(CSV_PATH, parse_dates=["timestamp"])


@pytest.fixture(scope="module")
def df_reel_sans_label(df_reel) -> pd.DataFrame:
    """Dataset réel sans label_anomaly — test contamination défaut."""
    return df_reel.drop(columns=[LABEL_COL])


# ── Tests ratio et métriques réelles ─────────────────────────────────────

class TestContaminationOptimale:
    """Tests sur le vrai dataset — CDC §2.1."""

    def test_ratio_anomalies_reel(self, df_reel):
        """Ratio réel d'anomalies entre 1 % et 10 % (CDC §8)."""
        ratio = df_reel[LABEL_COL].mean()
        n_anom = int(df_reel[LABEL_COL].sum())
        print(f"\nDataset : {len(df_reel)} lignes | anomalies={n_anom} ({ratio*100:.2f}%)")
        assert 0.01 <= ratio <= 0.10

    def test_contamination_ratio_reel_ameliore_f1(self, df_reel):
        """contamination=ratio_réel → améliore la précision (CDC §2.1)."""
        df_r = detect_anomalies(df_reel)   # adaptatif via label_anomaly
        m    = evaluate(df_r)
        print(f"\ncontamination adaptative | F1={m['f1']:.4f} | "
              f"Prec={m['precision']:.4f} | Recall={m['recall']:.4f}")
        assert m["precision"] >= 0.70

    def test_contamination_adaptative_f1_cdc(self, df_reel):
        """CDC §2.1 : F1 >= 85 % avec contamination adaptative."""
        df_r = detect_anomalies(df_reel)
        m    = evaluate(df_r)
        print(f"\nF1 adaptatif = {m['f1']:.4f}")
        assert m["f1"] >= 0.85, (
            f"CDC §2.1 non atteint : F1={m['f1']:.3f} < 0.85"
        )

    def test_rappel_parfait_contamination_05(self, df_reel):
        """contamination=0.05 → Rappel=1.0 (aucune anomalie ratée)."""
        df_r = detect_anomalies(df_reel, contamination=0.05)
        m    = evaluate(df_r)
        print(f"\ncontamination=0.05 | F1={m['f1']:.4f} | "
              f"Recall={m['recall']:.4f}")
        assert m["recall"] >= 0.99

    def test_f1_acceptable_contamination_05(self, df_reel):
        """F1 >= 0.75 avec contamination=0.05 (documenté)."""
        df_r = detect_anomalies(df_reel, contamination=0.05)
        m    = evaluate(df_r)
        assert m["f1"] >= 0.75

    def test_contamination_defaut_sans_label(self, df_reel_sans_label):
        """Sans label_anomaly → contamination défaut 0.05 utilisée."""
        df_r = detect_anomalies(df_reel_sans_label)
        n_det = (df_r["anomaly_flag"] == -1).sum()
        n_attendu = int(len(df_reel_sans_label) * CONTAMINATION)
        print(f"\nSans label | détectées={n_det} | attendu≈{n_attendu}")
        assert abs(n_det - n_attendu) <= 5

    def test_features_personnalisees_reel(self, df_reel):
        """detect_anomalies() avec features=['utilization_pct'] sur dataset réel."""
        df_r = detect_anomalies(df_reel, features=["utilization_pct"])
        assert "anomaly_flag"  in df_r.columns
        assert "anomaly_score" in df_r.columns

    def test_contamination_explicite_reel(self, df_reel):
        """contamination=0.035 explicit → ~302 points détectés."""
        df_r  = detect_anomalies(df_reel, contamination=0.035)
        n_det = (df_r["anomaly_flag"] == -1).sum()
        print(f"\ncontamination=0.035 | détectées={n_det}")
        assert 250 <= n_det <= 380

    def test_metriques_completes_affichees(self, df_reel):
        """Affiche toutes les métriques pour le rapport de soutenance."""
        for cont in [0.035, 0.05, None]:
            label = f"{cont}" if cont else "adaptatif"
            df_r  = detect_anomalies(df_reel, contamination=cont)
            m     = evaluate(df_r)
            n_det = (df_r["anomaly_flag"] == -1).sum()
            print(
                f"\n--- contamination={label} ---\n"
                f"  F1        : {m['f1']:.4f}  "
                f"{'✅ >= 0.85' if m['f1'] >= 0.85 else '⚠ < 0.85'}\n"
                f"  Précision : {m['precision']:.4f}\n"
                f"  Rappel    : {m['recall']:.4f}\n"
                f"  Détectées : {n_det} / Réelles : {m['n_anomalies_reelles']}"
            )
        assert True

    def test_run_cli_sur_dataset_reel(self):
        """_run_cli() sur le vrai dataset — couvre le bloc CLI."""
        metrics = _run_cli(csv_path=CSV_PATH)
        assert isinstance(metrics, dict)
        assert metrics["f1"] >= 0.75
"""
prepare_labels.py — Préparation du df_kpi labélisé pour le Module IA
===========================================================================
CDC §2.1 : Le module IsolationForest nécessite une colonne 'label_anomaly'
(0 = normal, 1 = anomalie) dans df_kpi pour calculer le F1-score >= 85 %.

Schéma réel de kpi_olt_port_1.csv (8640 lignes, 7 colonnes) :
    timestamp, ifInOctets_bytes, ifOutOctets_bytes,
    ifInErrors, ifOutErrors, utilization_pct, label_anomaly

Pipeline :
    1. Charger kpi_olt_port_1.csv (CSV brut dataset v3 MAX)
    2. Appeler compute_kpis() de kpi_builder.py (S5-S6)
       → dérive debit_rx_mbps, debit_tx_mbps, error_rate_pct
    3. Conserver label_anomaly déjà présent (source CDC §8)
    4. Valider schéma FEATURES + label_anomaly
    5. Exporter data/csv/df_kpi_labeled.csv

Commande :
    python scripts/prepare_labels.py
    python scripts/prepare_labels.py data/csv/kpi_olt_port_1.csv
"""

import sys
import logging
from pathlib import Path

import pandas as pd

# ── src-layout import ──────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.kpi.kpi_builder import compute_kpis  # S5-S6 livrable

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# ── Constantes CDC §C4 Niveau 4 ───────────────────────────────────────────
FEATURES   = ["debit_rx_mbps", "debit_tx_mbps", "utilization_pct", "error_rate_pct"]
LABEL_COL  = "label_anomaly"

# Seuils fallback CDC §4 (si label_anomaly absent du CSV)
THRESHOLD_UTIL  = 85.0   # %
THRESHOLD_ERROR =  1.0   # %

DATA_DIR    = ROOT / "data" / "csv"
OUTPUT_PATH = DATA_DIR / "df_kpi_labeled.csv"


# ── Étape 1 : chargement CSV brut ─────────────────────────────────────────
def load_raw_csv(csv_path: Path) -> pd.DataFrame:
    """
    Charge kpi_olt_port_1.csv — CSV brut dataset v3 MAX.
    Colonnes attendues : timestamp, ifInOctets_bytes, ifOutOctets_bytes,
                         ifInErrors, ifOutErrors, utilization_pct, label_anomaly
    """
    log.info(f"Chargement : {csv_path}")
    df = pd.read_csv(csv_path, parse_dates=["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    required_raw = ["timestamp", "ifInOctets_bytes", "ifOutOctets_bytes", "ifInErrors"]
    missing = [c for c in required_raw if c not in df.columns]
    if missing:
        raise ValueError(
            f"Colonnes brutes manquantes dans {csv_path.name} : {missing}\n"
            f"Colonnes presentes : {list(df.columns)}"
        )
    log.info(f"  -> {len(df)} lignes | colonnes : {list(df.columns)}")
    return df


# ── Étape 2 : calcul KPIs via kpi_builder.py (S5-S6) ─────────────────────
def build_kpis(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Appelle compute_kpis() de kpi_builder.py pour produire :
        debit_rx_mbps, debit_tx_mbps, error_rate_pct
    Conserve utilization_pct et label_anomaly du CSV brut.
    """
    log.info("Calcul KPIs via kpi_builder.compute_kpis() ...")
    df_kpi = compute_kpis(df_raw)

    missing_features = [f for f in FEATURES if f not in df_kpi.columns]
    if missing_features:
        raise ValueError(
            f"compute_kpis() n'a pas produit les colonnes : {missing_features}\n"
            f"Colonnes produites : {list(df_kpi.columns)}\n"
            f"Verifier kpi_builder.py (S5-S6)."
        )
    log.info(f"  -> KPIs calcules : {[f for f in FEATURES if f in df_kpi.columns]}")
    return df_kpi


# ── Étape 3 : dérivation label_anomaly ────────────────────────────────────
def derive_labels(df: pd.DataFrame, df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Stratégie CDC §8 :
      - Si label_anomaly présent dans df_raw -> on le réinjecte (source de vérité)
      - Sinon -> fallback seuils déterministes CDC §4
    """
    if LABEL_COL in df_raw.columns:
        df[LABEL_COL] = df_raw[LABEL_COL].astype(int).values
        n_anom = df[LABEL_COL].sum()
        ratio  = n_anom / len(df) * 100
        log.info(
            f"  -> Labels issus du dataset v3 MAX (CDC §8) : "
            f"{n_anom} anomalies / {len(df)} lignes ({ratio:.2f} %)"
        )
    elif LABEL_COL in df.columns:
        df[LABEL_COL] = df[LABEL_COL].astype(int)
        log.info(f"  -> label_anomaly propagé par compute_kpis()")
    else:
        log.warning(
            f"  ! label_anomaly absent -- fallback seuils CDC §4 "
            f"(util>{THRESHOLD_UTIL}% OU error_rate>{THRESHOLD_ERROR}%)"
        )
        mask = (
            (df["utilization_pct"] > THRESHOLD_UTIL) |
            (df["error_rate_pct"]  > THRESHOLD_ERROR)
        )
        df[LABEL_COL] = mask.astype(int)
        log.info(f"  -> {df[LABEL_COL].sum()} anomalies derivees (fallback)")

    return df


# ── Étape 4 : validation schéma ───────────────────────────────────────────
def validate_schema(df: pd.DataFrame) -> None:
    """
    Valide le schéma final avant export.
    CDC §C4 Niveau 4 — colonnes requises : FEATURES + label_anomaly
    """
    required = FEATURES + [LABEL_COL]
    missing  = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Schema invalide -- colonnes manquantes : {missing}")

    assert df[LABEL_COL].isin([0, 1]).all(), \
        "label_anomaly doit etre 0 ou 1 uniquement"

    log.info("  OK Schema valide -- pret pour ml_local.detect_anomalies()")


# ── Étape 5 : export ──────────────────────────────────────────────────────
def export_labeled(df: pd.DataFrame, output_path: Path) -> None:
    """Exporte df_kpi_labeled.csv avec FEATURES + label_anomaly."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cols  = ["timestamp"] + FEATURES + [LABEL_COL]
    extra = [c for c in df.columns if c not in cols]
    df[cols + extra].to_csv(output_path, index=False)
    log.info(f"  -> Export : {output_path} ({len(df)} lignes)")


# ── Pipeline principal ─────────────────────────────────────────────────────
def prepare_labels(
    csv_path: Path,
    output_path: Path = OUTPUT_PATH,
) -> pd.DataFrame:
    """
    Pipeline complet : CSV brut -> df_kpi_labeled.csv
    Retourne : pd.DataFrame df_kpi labelisé
    """
    df_raw = load_raw_csv(csv_path)
    df_kpi = build_kpis(df_raw)
    df_kpi = derive_labels(df_kpi, df_raw)
    validate_schema(df_kpi)
    export_labeled(df_kpi, output_path)

    n_total = len(df_kpi)
    n_anom  = df_kpi[LABEL_COL].sum()
    log.info(
        f"\n{'='*55}\n"
        f"  df_kpi labelise pret -- CDC §2.1 IsolationForest\n"
        f"  Total    : {n_total} points\n"
        f"  Anomalies: {n_anom} ({n_anom/n_total*100:.2f} %)\n"
        f"  FEATURES : {FEATURES}\n"
        f"  Export   : {output_path}\n"
        f"{'='*55}"
    )
    return df_kpi


if __name__ == "__main__":
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA_DIR / "kpi_olt_port_1.csv"
    prepare_labels(src)
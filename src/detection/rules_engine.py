"""
rules_engine.py — Moteur de règles déterministes ( S7)
===========================================================================
CDC §2.1  : Alarmes basées sur seuils (utilisation >85 %, latence >100 ms)
CDC §4    : Contraintes de performance et seuils opérationnels
CDC §C4   : Niveau 4 — constantes THRESHOLDS documentées

Pour chaque ligne de df_kpi :
  - Vérifie chaque seuil THRESHOLDS si la colonne est présente
  - Produit rule_alarm (bool) et rule_detail (str descriptif)

Commande validation :
  pytest tests/unit/test_rules_engine.py -v
"""

from __future__ import annotations

import logging

import pandas as pd

logging.basicConfig(level=logging.INFO,
                    format="[rules_engine] %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

# ── Constantes — Seuils CDC §4 (§C4 Niveau 4) ────────────────────────────
THRESHOLDS: dict[str, float] = {
    "utilization_pct" : 85.0,   # % — saturation OLT (CDC §2.1 + §4)
    "error_rate_pct"  : 1.0,    # % — taux d'erreurs interface
    "latency_ms"      : 100.0,  # ms — latence QoS (CDC §2.1)
    "jitter_ms"       : 20.0,   # ms — gigue
    "packet_loss_pct" : 0.5,    # % — perte paquets (CDC §2.1)
}


def apply_rules(df_kpi: pd.DataFrame) -> pd.DataFrame:
    """
    Applique les règles déterministes CDC §4 sur df_kpi.

    Pour chaque ligne, vérifie chaque seuil THRESHOLDS.
    Colonnes non présentes dans df_kpi → ignorées (pas d'erreur).

    Paramètres
    ----------
    df_kpi : pd.DataFrame — sortie de kpi_builder.compute_kpis()
             ou de detect_anomalies()
             Colonnes utilisées si présentes :
               utilization_pct, error_rate_pct,
               latency_ms, jitter_ms, packet_loss_pct

    Retourne
    --------
    pd.DataFrame avec colonnes supplémentaires :
      - rule_alarm  : bool  (True si au moins un seuil dépassé)
      - rule_detail : str   (ex: "util=87.3%>85.0% | error=1.2%>1.0%")
    """
    if df_kpi.empty:
        raise ValueError(
            "apply_rules() reçoit un DataFrame vide — "
            "vérifier le pipeline kpi_builder."
        )

    df_result = df_kpi.copy()

    # Colonnes THRESHOLDS présentes dans df_kpi
    cols_actives = [c for c in THRESHOLDS if c in df_kpi.columns]

    if not cols_actives:
        log.warning(
            "Aucune colonne THRESHOLDS présente dans df_kpi. "
            f"Colonnes disponibles : {list(df_kpi.columns)}"
        )
        df_result["rule_alarm"]  = False
        df_result["rule_detail"] = ""
        return df_result

    # Labels courts pour rule_detail
    SHORT = {
        "utilization_pct" : "util",
        "error_rate_pct"  : "error",
        "latency_ms"      : "latency",
        "jitter_ms"       : "jitter",
        "packet_loss_pct" : "loss",
    }
    UNITS = {
        "utilization_pct" : "%",
        "error_rate_pct"  : "%",
        "latency_ms"      : "ms",
        "jitter_ms"       : "ms",
        "packet_loss_pct" : "%",
    }

    # Calcul vectorisé par colonne
    alarm_mask   = pd.Series(False, index=df_kpi.index)
    detail_parts = {col: pd.Series("", index=df_kpi.index)
                    for col in cols_actives}

    for col in cols_actives:
        seuil = THRESHOLDS[col]
        mask  = df_kpi[col] > seuil
        alarm_mask = alarm_mask | mask

        unit  = UNITS[col]
        short = SHORT[col]
        # Construire la partie detail seulement pour les lignes en alarme
        detail_parts[col] = mask.apply(
            lambda v, c=col, s=seuil, u=unit, sh=short:
            f"{sh}={df_kpi.loc[v.name if hasattr(v, 'name') else 0, c]:.1f}{u}>{s}{u}"
            if v else ""
        )

    # Reconstruction vectorisée du detail
    def build_detail(row_idx):
        parts = [
            detail_parts[col].iloc[row_idx]
            for col in cols_actives
            if detail_parts[col].iloc[row_idx]
        ]
        return " | ".join(parts)

    df_result["rule_alarm"]  = alarm_mask
    df_result["rule_detail"] = [
        build_detail(i) for i in range(len(df_result))
    ]

    n_alarms = alarm_mask.sum()
    log.info(
        f"[OK] {len(df_result):,} lignes analysées | "
        f"alarmes : {n_alarms} ({n_alarms / len(df_result) * 100:.2f} %) | "
        f"seuils actifs : {cols_actives}"
    )
    return df_result
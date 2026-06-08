# scripts/run_scenarios.py
# Batch PDF generation — all 6 incident scenarios (CDC §13)
# Usage: python -m scripts.run_scenarios
# Output: reports/rapport_S1_*.pdf … reports/rapport_S6_*.pdf
#
# README_PDF_Generation_S12.md §4 — do not modify the pipeline logic.

import os
import sys

# Fix Windows console encoding (cp1252 -> utf-8)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd
from datetime import datetime

from src.parsing.parse_csv import parse_csv
from src.kpi.kpi_builder import compute_kpis
from src.detection.ml_local import detect_anomalies
from src.detection.rules_engine import apply_rules
from src.security.snmp_audit import run_audit
from src.reports.pdf_generator import generate_pdf

os.makedirs("reports", exist_ok=True)

# ─── Scenario definitions (README §3) ─────────────────────────────────────────
SCENARIOS = [
    {
        "name":     "S1 — OLT Saturation",
        "csv":      "data/csv/kpi_olt_port_1.csv",
        "dtype":    "kpi",
        "ont_csv":  None,
        "inject":   "saturation",   # inject utilization spikes > 85 %
    },
    {
        "name":     "S2 — Optical Degradation",
        "csv":      "data/csv/kpi_olt_port_1.csv",
        "dtype":    "kpi",
        "ont_csv":  None,
        "inject":   "degradation",  # inject error_rate_pct spikes > 1 %
    },
    {
        "name":     "S3 — ONT Offline",
        "csv":      "data/csv/kpi_olt_port_1.csv",
        "dtype":    "kpi",
        "ont_csv":  "data/csv/ont_status_timeseries.csv",
        "inject":   None,
    },
    {
        "name":     "S4 — Error Burst",
        "csv":      "data/csv/kpi_olt_port_1.csv",
        "dtype":    "kpi",
        "ont_csv":  None,
        "inject":   "error_burst",  # short error_rate spike, no util change
    },
    {
        "name":     "S5 — Multivariate Anomaly",
        "csv":      "data/csv/kpi_olt_port_1.csv",
        "dtype":    "kpi",
        "ont_csv":  None,
        "inject":   "multivariate",  # all 4 features jointly anomalous — IF only
    },
    {
        "name":     "S6 — Splitter Non-Conformant",
        "csv":      "data/csv/kpi_olt_port_1.csv",
        "dtype":    "kpi",
        "ont_csv":  None,
        "inject":   "clean",        # no KPI anomalies — §3 must show zero
    },
]


# ─── Injection helpers (README §3 expected detections) ────────────────────────

def _inject_saturation(df: pd.DataFrame) -> pd.DataFrame:
    """S1: spike utilization_pct > 85 % on ~15 % of rows."""
    df = df.copy()
    n = len(df)
    idx = np.linspace(10, n - 10, max(1, n // 7), dtype=int)
    df.loc[idx, "utilization_pct"] = np.clip(
        df.loc[idx, "utilization_pct"] + 25.0, 85.1, 100.0
    )
    return df


def _inject_degradation(df: pd.DataFrame) -> pd.DataFrame:
    """S2: spike error_rate_pct > 1 % on ~10 % of rows."""
    df = df.copy()
    n = len(df)
    idx = np.linspace(5, n - 5, max(1, n // 10), dtype=int)
    df.loc[idx, "error_rate_pct"] = np.clip(
        df.loc[idx, "error_rate_pct"] + 2.0, 1.01, 10.0
    )
    return df


def _inject_error_burst(df: pd.DataFrame) -> pd.DataFrame:
    """S4: short concentrated error_rate burst (20 consecutive rows)."""
    df = df.copy()
    n = len(df)
    start = n // 3
    end   = min(start + 20, n)
    df.loc[start:end, "error_rate_pct"] = 3.5
    return df


def _inject_multivariate(df: pd.DataFrame) -> pd.DataFrame:
    """S5: all 4 features simultaneously unusual (jointly anomalous, no single threshold breach)."""
    df = df.copy()
    n = len(df)
    rng = np.random.default_rng(99)
    idx = rng.choice(n, size=max(1, n // 12), replace=False)
    # Stay below thresholds individually but be jointly extreme
    df.loc[idx, "utilization_pct"] = 82.0    # below 85 threshold
    df.loc[idx, "error_rate_pct"]  = 0.95    # below 1.0 threshold
    df.loc[idx, "debit_rx_mbps"]   = df["debit_rx_mbps"].quantile(0.98)
    df.loc[idx, "debit_tx_mbps"]   = df["debit_tx_mbps"].quantile(0.98)
    return df


def _inject_clean(df: pd.DataFrame) -> pd.DataFrame:
    """S6: clamp all KPIs to nominal range — zero anomalies expected."""
    df = df.copy()
    if "utilization_pct" in df.columns:
        df["utilization_pct"] = df["utilization_pct"].clip(0, 80)
    if "error_rate_pct" in df.columns:
        df["error_rate_pct"]  = df["error_rate_pct"].clip(0, 0.4)
    return df


INJECTORS = {
    "saturation":  _inject_saturation,
    "degradation": _inject_degradation,
    "error_burst": _inject_error_burst,
    "multivariate": _inject_multivariate,
    "clean":       _inject_clean,
    None:          lambda df: df,
}


# ─── Pipeline ─────────────────────────────────────────────────────────────────

def run_pipeline(scenario: dict) -> str:
    name    = scenario["name"]
    slug    = name.split("—")[0].strip().replace(" ", "_")
    inject  = scenario.get("inject")
    print(f"\n[run_scenarios] ▶ {name}")

    # 1. Parse CSV
    df_raw = parse_csv(scenario["csv"], dtype=scenario["dtype"])
    df_kpi = compute_kpis(df_raw)

    # 2. utilization_pct fallback (dynamic Δt — README §18)
    if "utilization_pct" not in df_kpi.columns:
        delta_t = df_raw["timestamp"].diff().dt.total_seconds().fillna(300)
        df_kpi["utilization_pct"] = (
            (df_raw["ifInOctets_bytes"].diff() * 8)
            / delta_t / 1_000_000 / 1000.0 * 100
        ).clip(0, 100).fillna(0)

    # Ensure all 4 KPI columns exist with sensible defaults
    for col, default in [
        ("utilization_pct", 50.0),
        ("error_rate_pct",  0.5),
        ("debit_rx_mbps",   200.0),
        ("debit_tx_mbps",   100.0),
    ]:
        if col not in df_kpi.columns:
            df_kpi[col] = default

    # 3. Inject scenario-specific data distortions
    injector = INJECTORS.get(inject, lambda df: df)
    df_kpi   = injector(df_kpi)

    # 4. ONT merge (S3)
    if scenario.get("ont_csv"):
        try:
            df_ont = parse_csv(scenario["ont_csv"], dtype="ont")
            df_kpi["onuOperStatus"] = "up"
            if "onuOperStatus" in df_ont.columns:
                down_ids = df_ont[df_ont["onuOperStatus"] == "down"]["ont_id"].unique()
                if len(down_ids) > 0:
                    n_down = min(len(down_ids), len(df_kpi))
                    df_kpi.loc[df_kpi.index[:n_down], "onuOperStatus"] = "down"
                    print(f"  [ONT] {n_down} rows marked DOWN from {len(down_ids)} ONT IDs")
        except Exception as e:
            print(f"  [ONT] skipped: {e}")
            df_kpi["onuOperStatus"] = "up"

    # 5. Anomaly detection + rule engine
    df_kpi = detect_anomalies(df_kpi)
    df_kpi = apply_rules(df_kpi)

    # 6. SNMP audit
    rapport = run_audit()

    # 7. Build audit dict with correct format for pdf_generator
    #    _section_securite expects {"score": int, "alerts": list[dict|str], "recommendations": list[str]}
    rapport_pdf = {
        "score": rapport.get("score", 72),
        "alerts": [],
        "recommendations": rapport.get("recommendations", []),
    }
    for alert in rapport.get("alerts", []):
        if isinstance(alert, (list, tuple)) and len(alert) >= 2:
            # (severity, message) tuple format from run_audit()
            rapport_pdf["alerts"].append({
                "device":  "-",
                "type":    str(alert[0]),
                "detail":  str(alert[1]),
            })
        elif isinstance(alert, dict):
            rapport_pdf["alerts"].append(alert)
        else:
            rapport_pdf["alerts"].append({
                "device":  "-",
                "type":    "SNMP",
                "detail":  str(alert),
            })

    # 8. Generate PDF
    ts       = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    path_out = f"reports/rapport_{slug}_{ts}.pdf"

    path = generate_pdf(
        df_kpi=df_kpi,
        rapport_conformite=rapport_pdf,
        figures=[],
        path_out=path_out,
        scenario=name,
    )

    nb_ia    = int((df_kpi["anomaly_flag"] == -1).sum()) if "anomaly_flag" in df_kpi.columns else 0
    nb_rules = int(df_kpi["rule_alarm"].sum())           if "rule_alarm"   in df_kpi.columns else 0
    print(f"  [OK] IA={nb_ia} anomalies, Rules={nb_rules} alarms → {path}")
    return path


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    paths  = []
    errors = []
    for sc in SCENARIOS:
        try:
            paths.append(run_pipeline(sc))
        except Exception as e:
            errors.append((sc["name"], str(e)))
            import traceback
            print(f"  [ERROR] {sc['name']}: {e}")
            traceback.print_exc()

    print(f"\n{'='*60}")
    print(f"Generated {len(paths)}/6 reports successfully.")
    if errors:
        print("Failed:")
        for name, err in errors:
            print(f"  - {name}: {err}")
    print(f"{'='*60}")

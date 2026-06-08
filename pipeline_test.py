"""
pipeline_test.py — Full pipeline smoke test
"""
import sys
sys.path.insert(0, ".")

from src.parsing.parse_csv import parse_csv
from src.kpi.kpi_builder import compute_kpis
from src.detection.ml_local import detect_anomalies, evaluate
from src.detection.rules_engine import apply_rules
from src.security.snmp_audit import run_audit

df_raw = parse_csv("data/csv/kpi_olt_port_1.csv", dtype="kpi")
df_kpi = compute_kpis(df_raw)

# Dynamic delta_t per README §18
delta_t = df_raw["timestamp"].diff().dt.total_seconds().fillna(300)
df_kpi["utilization_pct"] = (
    (df_raw["ifInOctets_bytes"].diff() * 8)
    / delta_t / 1_000_000 / 1000.0 * 100
).clip(0, 100).fillna(0)

df_kpi = detect_anomalies(df_kpi)
df_kpi = apply_rules(df_kpi)

metrics  = evaluate(df_kpi)
rapport  = run_audit()

print("Shape:", df_kpi.shape)
print("Columns:", list(df_kpi.columns))
print("Anomalies:", int((df_kpi["anomaly_flag"] == -1).sum()))
print("Rule alarms:", int(df_kpi["rule_alarm"].sum()))
print("F1:", round(metrics["f1"], 4))
print("SNMP Score:", rapport["score"])
print("PIPELINE OK")

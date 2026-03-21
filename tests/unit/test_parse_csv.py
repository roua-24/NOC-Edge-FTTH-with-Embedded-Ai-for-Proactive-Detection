import pytest
import pandas as pd
from src.parsing.parse_csv import parse_csv
from src.parsing.parse_snmp import parse_snmp, parse_snmp_dir
from src.parsing.parse_pcap import parse_pcap


# ── Tests parse_csv ────────────────────────────────────────────

def test_parse_csv_kpi_colonnes():
    df = parse_csv("data/csv/kpi_olt_port_1.csv", dtype="kpi")
    for col in ["timestamp", "ifInOctets_bytes", "ifOutOctets_bytes",
                "ifInErrors", "ifOutErrors", "utilization_pct", "label_anomaly"]:
        assert col in df.columns, f"Colonne manquante : {col}"

def test_parse_csv_kpi_shape():
    df = parse_csv("data/csv/kpi_olt_port_1.csv", dtype="kpi")
    assert len(df) > 0, "DataFrame vide"
    assert len(df.columns) == 7

def test_parse_csv_timestamp_dtype():
    df = parse_csv("data/csv/kpi_olt_port_1.csv", dtype="kpi")
    assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])

def test_parse_csv_tri_chronologique():
    df = parse_csv("data/csv/kpi_olt_port_1.csv", dtype="kpi")
    assert df["timestamp"].is_monotonic_increasing

def test_parse_csv_qos_colonnes():
    df = parse_csv("data/csv/qos_metrics.csv", dtype="qos")
    for col in ["timestamp", "latency_ms", "jitter_ms",
                "packet_loss_pct", "label_degradation"]:
        assert col in df.columns

def test_parse_csv_optical_shape():
    df = parse_csv("data/csv/optical_budget_scenarios.csv", dtype="optical")
    assert df.shape == (8, 9), f"Shape attendu (8,9), obtenu {df.shape}"

def test_parse_csv_fichier_manquant():
    with pytest.raises(FileNotFoundError):
        parse_csv("data/csv/fichier_inexistant.csv", dtype="kpi")

def test_parse_csv_dtype_inconnu():
    with pytest.raises(ValueError):
        parse_csv("data/csv/kpi_olt_port_1.csv", dtype="inconnu")

def test_parse_csv_tous_types():
    configs = [
        ("data/csv/kpi_olt_port_1.csv",           "kpi"),
        ("data/csv/qos_metrics.csv",              "qos"),
        ("data/csv/optical_budget_scenarios.csv", "optical"),
        ("data/csv/security_events.csv",          "security"),
        ("data/csv/topology_inventory.csv",       "topology"),
    ]
    for path, dtype in configs:
        df = parse_csv(path, dtype)
        assert not df.empty, f"DataFrame vide pour {dtype}"


# ── Tests parse_snmp ───────────────────────────────────────────

def test_parse_snmp_olt_colonnes():
    df = parse_snmp("data/snmp/snmpwalk_olt_port_1.txt")
    for col in ["equipment_id", "oid_name", "oid_type", "value", "unit"]:
        assert col in df.columns

def test_parse_snmp_olt_equipment_id():
    df = parse_snmp("data/snmp/snmpwalk_olt_port_1.txt")
    assert df["equipment_id"].iloc[0] == "OLT_1"

def test_parse_snmp_ont_equipment_id():
    df = parse_snmp("data/snmp/snmpwalk_ONT_101.txt")
    assert df["equipment_id"].iloc[0] == "ONT_101"

def test_parse_snmp_fichier_manquant():
    with pytest.raises(FileNotFoundError):
        parse_snmp("data/snmp/inexistant.txt")

def test_parse_snmp_dir_tous_equipements():
    df = parse_snmp_dir("data/snmp")
    n_eq = df["equipment_id"].nunique()
    assert n_eq >= 91, f"Moins de 90% des equipements parses : {n_eq}/101"


# ── Tests parse_pcap ───────────────────────────────────────────

def test_parse_pcap_colonnes():
    df = parse_pcap("data/traces/pcap_flows_summary.csv")
    for col in ["timestamp", "src_ip", "dst_ip", "protocol",
                "packets", "bytes", "label_suspicious"]:
        assert col in df.columns

def test_parse_pcap_shape():
    df = parse_pcap("data/traces/pcap_flows_summary.csv")
    assert len(df) >= 90000, f"Moins de 90% des flux parses : {len(df)}"

def test_parse_pcap_timestamp_dtype():
    df = parse_pcap("data/traces/pcap_flows_summary.csv")
    assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])

def test_parse_pcap_fichier_manquant():
    with pytest.raises(FileNotFoundError):
        parse_pcap("data/traces/inexistant.csv")
# ── Tests branches manquantes (couverture) ─────────────────────

def test_parse_csv_ont_complet():
    df = parse_csv("data/csv/ont_status_timeseries.csv", dtype="ont")
    assert not df.empty
    assert df["ont_id"].dtype.name == "category"
    assert str(df["rx_power_dBm"].dtype) == "float32"
    assert str(df["tx_power_dBm"].dtype) == "float32"

def test_parse_csv_security_colonnes():
    df = parse_csv("data/csv/security_events.csv", dtype="security")
    assert "event_type" in df.columns
    assert "severity" in df.columns
    assert len(df) == 500

def test_parse_pcap_tri_chronologique():
    df = parse_pcap("data/traces/pcap_flows_summary.csv")
    assert df["timestamp"].is_monotonic_increasing

def test_parse_pcap_protocoles_connus():
    df = parse_pcap("data/traces/pcap_flows_summary.csv")
    protocoles = df["protocol"].unique().tolist()
    assert "TCP" in protocoles or "UDP" in protocoles
def test_parse_csv_security_non_vide():
    df = parse_csv("data/csv/security_events.csv", dtype="security")
    assert not df.empty
    assert "timestamp" in df.columns

def test_parse_pcap_labels_suspects():
    df = parse_pcap("data/traces/pcap_flows_summary.csv")
    assert "label_suspicious" in df.columns
    assert df["label_suspicious"].sum() >= 0
    assert df["packets"].dtype == "int32"
    assert df["bytes"].dtype == "int32"
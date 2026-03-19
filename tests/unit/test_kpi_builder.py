"""Tests unitaires — kpi_builder.py"""
import pytest
import pandas as pd
from src.kpi.kpi_builder import compute_kpis
from src.kpi.budget_optique import compute_optical_budget


def test_budget_optique_ok():
    result = compute_optical_budget(distance_km=5.0, split_ratio=32, nb_connectors=4)
    assert result["status"] == "OK"
    assert result["perte_totale_db"] > 0


def test_budget_optique_hors_budget():
    result = compute_optical_budget(distance_km=30.0, split_ratio=256, nb_connectors=10)
    assert result["status"] == "HORS_BUDGET"


def test_compute_kpis_columns():
    df = pd.DataFrame({
        "timestamp":  pd.date_range("2024-01-01", periods=10, freq="5min"),
        "bytes_in":   range(0, 100_000_000, 10_000_000),
        "bytes_out":  range(0, 50_000_000, 5_000_000),
        "errors_in":  [0]*10,
        "errors_out": [0]*10,
    })
    result = compute_kpis(df)
    assert "debit_rx_mbps" in result.columns
    assert "utilization_pct" in result.columns
    assert "error_rate_pct" in result.columns

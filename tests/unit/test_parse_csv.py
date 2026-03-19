# tests/unit/test_parse_csv.py
import pytest 
import pandas as pd
from pathlib import Path
from src.parsing.parse_csv import parse_csv

def test_parse_csv_colonnes():
    df = parse_csv("data/csv/test_kpi.csv", dtype="kpi")
    assert "timestamp" in df.columns
    assert "bytes_in"  in df.columns
    assert "bytes_out" in df.columns

def test_parse_csv_types():
    df = parse_csv("data/csv/test_kpi.csv")
    assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])

def test_parse_csv_tri_chronologique():
    df = parse_csv("data/csv/test_kpi.csv")
    assert df["timestamp"].is_monotonic_increasing

def test_parse_csv_fichier_manquant():
    with pytest.raises(FileNotFoundError):
        parse_csv("data/csv/inexistant.csv")

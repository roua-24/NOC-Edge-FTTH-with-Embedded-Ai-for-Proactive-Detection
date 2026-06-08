"""
tests/unit/test_parse_pcap.py — Tests ciblés couverture parse_pcap.py
===========================================================================
CDC §3   : Parsing >= 90 % des fichiers fournis
CDC §5   : Couverture >= 70 % sur modules critiques

Lignes non couvertes ciblées :
  45   → ValueError colonnes manquantes
  50-51 → branche NaN (ffill + dropna)
  67-69 → except pd.errors.ParserError → retourne DataFrame vide
  73-85 → bloc __main__ (non testable directement — couvert par intégration)

Commande :
    pytest tests/unit/test_parse_pcap.py -v --cov=src/parsing/parse_pcap --cov-report=term-missing
"""

import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.parsing.parse_pcap import REQUIRED_COLS, parse_pcap

# ── Colonnes requises par parse_pcap ──────────────────────────────────────
COLS = REQUIRED_COLS  # ["timestamp","src_ip","dst_ip","protocol","packets","bytes","label_suspicious"]


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def csv_pcap_valide(tmp_path) -> Path:
    """CSV PCAP synthétique valide — toutes colonnes présentes, sans NaN."""
    n = 20
    rng = np.random.default_rng(0)
    df = pd.DataFrame({
        "timestamp"       : pd.date_range("2024-01-01", periods=n, freq="1min").astype(str),
        "src_ip"          : ["192.168.1.1"] * n,
        "dst_ip"          : ["10.0.0.1"] * n,
        "protocol"        : rng.choice(["TCP", "UDP", "ICMP"], n).tolist(),
        "packets"         : rng.integers(1, 100, n).tolist(),
        "bytes"           : rng.integers(100, 10000, n).tolist(),
        "label_suspicious": rng.integers(0, 2, n).tolist(),
    })
    p = tmp_path / "pcap_test.csv"
    df.to_csv(p, index=False)
    return p


@pytest.fixture
def csv_pcap_avec_nan(tmp_path) -> Path:
    """CSV PCAP avec NaN — couvre branche ffill() lignes 50-51."""
    df = pd.DataFrame({
        "timestamp"       : ["2024-01-01 00:00:00", None, "2024-01-01 00:02:00"],
        "src_ip"          : ["192.168.1.1", None, "192.168.1.3"],
        "dst_ip"          : ["10.0.0.1", "10.0.0.2", "10.0.0.3"],
        "protocol"        : ["TCP", None, "UDP"],
        "packets"         : [10, None, 30],
        "bytes"           : [1000, None, 3000],
        "label_suspicious": [0, None, 0],
    })
    p = tmp_path / "pcap_nan.csv"
    df.to_csv(p, index=False)
    return p


@pytest.fixture
def csv_pcap_colonnes_manquantes(tmp_path) -> Path:
    """CSV sans 'protocol' et 'bytes' — couvre ValueError ligne 45."""
    df = pd.DataFrame({
        "timestamp" : ["2024-01-01 00:00:00"],
        "src_ip"    : ["192.168.1.1"],
        "dst_ip"    : ["10.0.0.1"],
        # protocol, packets, bytes, label_suspicious manquants
    })
    p = tmp_path / "pcap_incomplet.csv"
    df.to_csv(p, index=False)
    return p


# ── Tests structure sortie ─────────────────────────────────────────────────

class TestStructureSortie:

    def test_retourne_dataframe(self, csv_pcap_valide):
        result = parse_pcap(str(csv_pcap_valide))
        assert isinstance(result, pd.DataFrame)

    def test_colonnes_requises_presentes(self, csv_pcap_valide):
        result = parse_pcap(str(csv_pcap_valide))
        for col in COLS:
            assert col in result.columns

    def test_timestamp_est_datetime(self, csv_pcap_valide):
        result = parse_pcap(str(csv_pcap_valide))
        assert pd.api.types.is_datetime64_any_dtype(result["timestamp"])

    def test_protocol_est_category(self, csv_pcap_valide):
        result = parse_pcap(str(csv_pcap_valide))
        assert str(result["protocol"].dtype) == "category"

    def test_packets_est_int32(self, csv_pcap_valide):
        result = parse_pcap(str(csv_pcap_valide))
        assert result["packets"].dtype == "int32"

    def test_bytes_est_int32(self, csv_pcap_valide):
        result = parse_pcap(str(csv_pcap_valide))
        assert result["bytes"].dtype == "int32"

    def test_tri_chronologique(self, csv_pcap_valide):
        result = parse_pcap(str(csv_pcap_valide))
        assert result["timestamp"].is_monotonic_increasing

    def test_pas_vide(self, csv_pcap_valide):
        result = parse_pcap(str(csv_pcap_valide))
        assert not result.empty


# ── Tests branches non couvertes ──────────────────────────────────────────

class TestBranchesNonCouvertes:
    """Tests ciblant précisément les lignes 45, 50-51, 67-69."""

    def test_ligne_45_valueerror_colonnes_manquantes(self, csv_pcap_colonnes_manquantes):
        """
        Ligne 45 : raise ValueError si colonnes requises manquantes.
        CSV sans 'protocol', 'packets', 'bytes', 'label_suspicious'.
        """
        with pytest.raises(ValueError, match="Colonnes manquantes"):
            parse_pcap(str(csv_pcap_colonnes_manquantes))

    def test_lignes_50_51_nan_applique_ffill(self, csv_pcap_avec_nan):
        """
        Lignes 50-51 : NaN détectés → ffill() appliqué → dropna().
        Le résultat ne doit pas contenir de NaN.
        """
        result = parse_pcap(str(csv_pcap_avec_nan))
        assert not result.empty
        # Après ffill + dropna, pas de NaN dans les colonnes numériques
        assert result["packets"].notna().all()
        assert result["bytes"].notna().all()

    def test_lignes_67_69_parser_error_retourne_df_vide(self, tmp_path):
        """
        Lignes 67-69 : pd.errors.ParserError → retourne DataFrame vide.
        On simule un fichier CSV corrompu (contenu non parsable).
        """
        # Fichier avec toutes les colonnes mais contenu corrompu
        p = tmp_path / "pcap_corrompu.csv"
        # Écrire un CSV avec les bonnes colonnes puis corrompre le contenu
        header = ",".join(COLS) + "\n"
        corrupt = header + "a,b,c\x00d,e\nf,,g\x00h\n"  # bytes nuls = corruption
        p.write_bytes(corrupt.encode("utf-8") + b"\xff\xfe" * 100)

        # Mocker pd.read_csv pour lever ParserError
        with patch("src.parsing.parse_pcap.pd.read_csv",
                   side_effect=pd.errors.ParserError("bad csv")):
            result = parse_pcap(str(p))

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_fichier_manquant_leve_exception(self, tmp_path):
        """FileNotFoundError si fichier inexistant."""
        with pytest.raises(FileNotFoundError):
            parse_pcap(str(tmp_path / "inexistant.csv"))


# ── Tests fonctionnels ────────────────────────────────────────────────────

class TestFonctionnel:

    def test_label_suspicious_present(self, csv_pcap_valide):
        result = parse_pcap(str(csv_pcap_valide))
        assert "label_suspicious" in result.columns

    def test_label_suspicious_binaire(self, csv_pcap_valide):
        result = parse_pcap(str(csv_pcap_valide))
        assert result["label_suspicious"].isin([0, 1]).all()

    def test_protocols_connus(self, csv_pcap_valide):
        """Les protocoles TCP/UDP/ICMP doivent être présents."""
        result = parse_pcap(str(csv_pcap_valide))
        protocoles = set(result["protocol"].cat.categories)
        assert protocoles.issubset({"TCP", "UDP", "ICMP", "ARP", "DNS", "HTTP"})

    def test_packets_positifs(self, csv_pcap_valide):
        result = parse_pcap(str(csv_pcap_valide))
        assert (result["packets"] > 0).all()

    def test_bytes_positifs(self, csv_pcap_valide):
        result = parse_pcap(str(csv_pcap_valide))
        assert (result["bytes"] > 0).all()
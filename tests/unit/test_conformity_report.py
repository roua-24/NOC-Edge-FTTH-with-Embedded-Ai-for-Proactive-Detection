"""
tests/unit/test_conformity_report.py
======================================
Tests unitaires pour src/security/conformity_report.py

§9 CDC : Rapport de conformité (score) - export TXT et JSON.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.security.conformity_report import generate_conformity_report, _score_bar


# -----------------------------------------------------------------------------
# Fixtures - rapports synthétiques
# -----------------------------------------------------------------------------

@pytest.fixture
def rapport_non_conforme() -> dict:
    return {
        "score": 40,
        "conformity": "NON CONFORME",
        "nb_files": 2,
        "nb_v2c": 2,
        "nb_v3": 0,
        "nb_authpriv": 0,
        "alerts": [
            "[olt.txt] SNMPv2c détecté sans SNMPv3",
            "[ont.txt] Community string faible : 'public'",
        ],
        "recommendations": [
            "[CRITIQUE] Migrer vers SNMPv3 authPriv",
            "[BASELINE] Appliquer SHA-256 + AES-256",
        ],
        "devices": [
            {
                "filename": "olt.txt",
                "has_v2c": True,
                "communities": ["public"],
                "has_v3": False,
                "has_authpriv": False,
                "has_sha": False,
                "has_aes": False,
                "device_score": 60,
                "alerts": ["SNMPv2c détecté sans SNMPv3"],
            }
        ],
        "baseline": {
            "snmp_version": "SNMPv3",
            "security_level": "authPriv",
            "auth_protocol": "SHA-256",
            "priv_protocol": "AES-256",
            "reference": "RFC 3411-3418",
        },
    }


@pytest.fixture
def rapport_conforme() -> dict:
    return {
        "score": 100,
        "conformity": "CONFORME",
        "nb_files": 2,
        "nb_v2c": 0,
        "nb_v3": 2,
        "nb_authpriv": 2,
        "alerts": [],
        "recommendations": ["Configuration conforme - maintenir la politique."],
        "devices": [
            {
                "filename": "ont_150.txt",
                "has_v2c": False,
                "communities": [],
                "has_v3": True,
                "has_authpriv": True,
                "has_sha": True,
                "has_aes": True,
                "device_score": 100,
                "alerts": [],
            }
        ],
        "baseline": {},
    }


# -----------------------------------------------------------------------------
# Tests - _score_bar
# -----------------------------------------------------------------------------

class TestScoreBar:

    def test_score_100_full_bar(self) -> None:
        bar = _score_bar(100)
        assert "100/100" in bar
        assert "." not in bar

    def test_score_0_empty_bar(self) -> None:
        bar = _score_bar(0)
        assert "0/100" in bar
        assert "#" not in bar

    def test_score_50_half_bar(self) -> None:
        bar = _score_bar(50)
        assert "50/100" in bar
        assert "#" in bar
        assert "." in bar

    def test_bar_contains_brackets(self) -> None:
        bar = _score_bar(75)
        assert bar.startswith("[")
        assert "]" in bar


# -----------------------------------------------------------------------------
# Tests - generate_conformity_report
# -----------------------------------------------------------------------------

class TestGenerateConformityReport:

    def test_creates_txt_and_json(self, tmp_path: Path, rapport_non_conforme: dict) -> None:
        """Les deux fichiers TXT et JSON doivent être créés."""
        result = generate_conformity_report(rapport_non_conforme, tmp_path)
        assert result["txt"].exists()
        assert result["json"].exists()

    def test_txt_filename(self, tmp_path: Path, rapport_non_conforme: dict) -> None:
        result = generate_conformity_report(rapport_non_conforme, tmp_path)
        assert result["txt"].name == "rapport_conformite_SNMP.txt"

    def test_json_filename(self, tmp_path: Path, rapport_non_conforme: dict) -> None:
        result = generate_conformity_report(rapport_non_conforme, tmp_path)
        assert result["json"].name == "rapport_conformite_SNMP.json"

    def test_txt_contains_score(self, tmp_path: Path, rapport_non_conforme: dict) -> None:
        generate_conformity_report(rapport_non_conforme, tmp_path)
        content = (tmp_path / "rapport_conformite_SNMP.txt").read_text(encoding="utf-8")
        assert "40/100" in content

    def test_txt_contains_conformity_level(self, tmp_path: Path, rapport_non_conforme: dict) -> None:
        generate_conformity_report(rapport_non_conforme, tmp_path)
        content = (tmp_path / "rapport_conformite_SNMP.txt").read_text(encoding="utf-8")
        assert "NON CONFORME" in content

    def test_txt_contains_alerts(self, tmp_path: Path, rapport_non_conforme: dict) -> None:
        generate_conformity_report(rapport_non_conforme, tmp_path)
        content = (tmp_path / "rapport_conformite_SNMP.txt").read_text(encoding="utf-8")
        assert "SNMPv2c" in content

    def test_txt_contains_recommendations(self, tmp_path: Path, rapport_non_conforme: dict) -> None:
        generate_conformity_report(rapport_non_conforme, tmp_path)
        content = (tmp_path / "rapport_conformite_SNMP.txt").read_text(encoding="utf-8")
        assert "CRITIQUE" in content

    def test_txt_contains_device_details(self, tmp_path: Path, rapport_non_conforme: dict) -> None:
        generate_conformity_report(rapport_non_conforme, tmp_path)
        content = (tmp_path / "rapport_conformite_SNMP.txt").read_text(encoding="utf-8")
        assert "olt.txt" in content

    def test_txt_no_alerts_message_for_conforme(self, tmp_path: Path, rapport_conforme: dict) -> None:
        generate_conformity_report(rapport_conforme, tmp_path)
        content = (tmp_path / "rapport_conformite_SNMP.txt").read_text(encoding="utf-8")
        assert "Aucune alerte" in content

    def test_json_valid_structure(self, tmp_path: Path, rapport_non_conforme: dict) -> None:
        """Le JSON doit être valide et contenir les clés meta + rapport."""
        generate_conformity_report(rapport_non_conforme, tmp_path)
        data = json.loads((tmp_path / "rapport_conformite_SNMP.json").read_text(encoding="utf-8"))
        assert "meta" in data
        assert "score" in data
        assert "conformity" in data
        assert "alerts" in data

    def test_json_meta_fields(self, tmp_path: Path, rapport_conforme: dict) -> None:
        generate_conformity_report(rapport_conforme, tmp_path)
        data = json.loads((tmp_path / "rapport_conformite_SNMP.json").read_text(encoding="utf-8"))
        assert data["meta"]["sprint"] == "S9"
        assert "generated_at" in data["meta"]
        assert "§9" in data["meta"]["cdc_reference"]

    def test_json_score_preserved(self, tmp_path: Path, rapport_conforme: dict) -> None:
        generate_conformity_report(rapport_conforme, tmp_path)
        data = json.loads((tmp_path / "rapport_conformite_SNMP.json").read_text(encoding="utf-8"))
        assert data["score"] == 100

    def test_creates_output_dir_if_missing(self, tmp_path: Path, rapport_conforme: dict) -> None:
        """Le répertoire de sortie doit être créé automatiquement."""
        new_dir = tmp_path / "sous_dossier" / "reports"
        assert not new_dir.exists()
        generate_conformity_report(rapport_conforme, new_dir)
        assert new_dir.exists()

    def test_accepts_string_path(self, tmp_path: Path, rapport_conforme: dict) -> None:
        """Doit accepter un chemin sous forme de chaîne."""
        result = generate_conformity_report(rapport_conforme, str(tmp_path))
        assert result["txt"].exists()

    def test_raises_on_empty_rapport(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="vide"):
            generate_conformity_report({}, tmp_path)

    def test_raises_on_missing_score_key(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="score"):
            generate_conformity_report({"conformity": "CONFORME"}, tmp_path)

    def test_returns_path_objects(self, tmp_path: Path, rapport_conforme: dict) -> None:
        result = generate_conformity_report(rapport_conforme, tmp_path)
        assert isinstance(result["txt"], Path)
        assert isinstance(result["json"], Path)

    def test_txt_contains_cdc_reference(self, tmp_path: Path, rapport_conforme: dict) -> None:
        generate_conformity_report(rapport_conforme, tmp_path)
        content = (tmp_path / "rapport_conformite_SNMP.txt").read_text(encoding="utf-8")
        assert "§9 CDC" in content or "CDC" in content

    def test_txt_utf8_encoded(self, tmp_path: Path, rapport_non_conforme: dict) -> None:
        """Le fichier TXT doit être encodé en UTF-8 (accents, symboles)."""
        generate_conformity_report(rapport_non_conforme, tmp_path)
        # Lecture sans spécifier encoding pour détecter les problèmes d'encodage
        content = (tmp_path / "rapport_conformite_SNMP.txt").read_bytes()
        # UTF-8 BOM absent - fichier UTF-8 pur
        assert content[:3] != b'\xef\xbb\xbf'
        content.decode("utf-8")  # Ne doit pas lever d'exception
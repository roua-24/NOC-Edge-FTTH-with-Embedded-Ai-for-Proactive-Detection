"""
tests/unit/test_snmp_audit.py
==============================
Tests unitaires pour src/security/snmp_audit.py

§9 CDC : Audit SNMPv2c vs SNMPv3, recommandations authPriv,
         score de conformite 0-100.

Couverture cible : >= 70 % de src/security/snmp_audit.py
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.security.snmp_audit import (
    SCORE_THRESHOLDS,
    WEAK_COMMUNITIES,
    _audit_single_file,
    _build_recommendations,
    _compute_global_score,
    _conformity_level,
    _DeviceAuditResult,
    audit_snmp,
    run_audit,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures — fichiers SNMP synthetiques en memoire
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def snmp_dir_mixed(tmp_path: Path) -> Path:
    (tmp_path / "olt_port1.txt").write_text(
        "SNMPv2c community public\n"
        "IF-MIB::ifInOctets.1 = Counter32: 1200000000\n",
        encoding="utf-8",
    )
    (tmp_path / "ont_101.txt").write_text(
        "SNMPv2c community private\n"
        "GPON-MIB::onuOperStatus.1 = INTEGER: active(1)\n",
        encoding="utf-8",
    )
    (tmp_path / "ont_150.txt").write_text(
        "SNMPv3 authPriv\n"
        "authProtocol SHA-256\n"
        "privProtocol AES-256\n"
        "GPON-MIB::onuOperStatus.1 = INTEGER: active(1)\n",
        encoding="utf-8",
    )
    (tmp_path / "ont_200.txt").write_text(
        "SNMPv3 authNoPriv\n"
        "authProtocol SHA-256\n"
        "GPON-MIB::onuOperStatus.1 = INTEGER: active(1)\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def snmp_dir_all_v2c(tmp_path: Path) -> Path:
    for i in range(3):
        (tmp_path / f"ont_{i}.txt").write_text(
            f"SNMPv2c community public\n"
            f"IF-MIB::ifInOctets.{i} = Counter32: {i * 1000}\n",
            encoding="utf-8",
        )
    return tmp_path


@pytest.fixture
def snmp_dir_all_authpriv(tmp_path: Path) -> Path:
    for i in range(3):
        (tmp_path / f"ont_{i}.txt").write_text(
            "SNMPv3 authPriv\n"
            "authProtocol SHA-256\n"
            "privProtocol AES-256\n"
            f"GPON-MIB::onuOperStatus.{i} = INTEGER: active(1)\n",
            encoding="utf-8",
        )
    return tmp_path


@pytest.fixture
def snmp_dir_empty(tmp_path: Path) -> Path:
    return tmp_path


# ─────────────────────────────────────────────────────────────────────────────
# Tests — _audit_single_file
# ─────────────────────────────────────────────────────────────────────────────

class TestAuditSingleFile:

    def test_detects_snmpv2c_community_public(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("SNMPv2c community public\n", encoding="utf-8")
        result = _audit_single_file(f)
        assert result.has_v2c is True
        assert "public" in result.communities

    def test_detects_snmpv2c_community_private(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("SNMPv2c community private\n", encoding="utf-8")
        result = _audit_single_file(f)
        assert result.has_v2c is True
        assert "private" in result.communities
        assert any("private" in a for a in result.alerts)

    def test_detects_snmpv3_authpriv(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text(
            "SNMPv3 authPriv\nauthProtocol SHA-256\nprivProtocol AES-256\n",
            encoding="utf-8",
        )
        result = _audit_single_file(f)
        assert result.has_v3 is True
        assert result.has_authpriv is True
        assert result.has_sha is True
        assert result.has_aes is True

    def test_detects_authnopriv(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("SNMPv3 authNoPriv\nauthProtocol SHA-256\n", encoding="utf-8")
        result = _audit_single_file(f)
        assert result.has_v3 is True
        assert result.has_authpriv is False
        assert result.has_auth_no_priv is True
        assert any("authNoPriv" in a for a in result.alerts)

    def test_score_v2c_public_penalized(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("SNMPv2c community public\n", encoding="utf-8")
        result = _audit_single_file(f)
        assert result.device_score == 60

    def test_score_authpriv_sha_aes_bonus(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text(
            "SNMPv3 authPriv\nauthProtocol SHA-256\nprivProtocol AES-256\n",
            encoding="utf-8",
        )
        result = _audit_single_file(f)
        assert result.device_score == 100

    def test_score_never_below_zero(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text(
            "SNMPv2c community public\ncommunity private\ncommunity default\n",
            encoding="utf-8",
        )
        result = _audit_single_file(f)
        assert result.device_score >= 0

    def test_score_never_above_100(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text(
            "SNMPv3 authPriv\nauthProtocol SHA-256\nprivProtocol AES-256\n",
            encoding="utf-8",
        )
        result = _audit_single_file(f)
        assert result.device_score <= 100

    def test_unreadable_file_returns_zero_score(self, tmp_path: Path) -> None:
        f = tmp_path / "ghost.txt"
        result = _audit_single_file(f)
        assert result.device_score == 0
        assert len(result.alerts) > 0

    def test_alert_v2c_without_v3(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("SNMPv2c community public\n", encoding="utf-8")
        result = _audit_single_file(f)
        assert any("SNMPv2c" in a for a in result.alerts)

    def test_no_alert_for_conformant_device(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text(
            "SNMPv3 authPriv\nauthProtocol SHA-256\nprivProtocol AES-256\n",
            encoding="utf-8",
        )
        result = _audit_single_file(f)
        assert result.alerts == []

    def test_authpriv_without_sha_alert(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("SNMPv3 authPriv\nprivProtocol AES-256\n", encoding="utf-8")
        result = _audit_single_file(f)
        assert any("SHA-256" in a for a in result.alerts)

    def test_authpriv_without_aes_alert(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("SNMPv3 authPriv\nauthProtocol SHA-256\n", encoding="utf-8")
        result = _audit_single_file(f)
        assert any("AES-256" in a for a in result.alerts)


# ─────────────────────────────────────────────────────────────────────────────
# Tests — _compute_global_score
# ─────────────────────────────────────────────────────────────────────────────

class TestComputeGlobalScore:

    def test_empty_list_returns_zero(self) -> None:
        assert _compute_global_score([]) == 0

    def test_single_device(self) -> None:
        r = _DeviceAuditResult(filename="test.txt", device_score=75)
        assert _compute_global_score([r]) == 75

    def test_average_rounded(self) -> None:
        r1 = _DeviceAuditResult(filename="a.txt", device_score=60)
        r2 = _DeviceAuditResult(filename="b.txt", device_score=80)
        assert _compute_global_score([r1, r2]) == 70

    def test_average_rounding(self) -> None:
        r1 = _DeviceAuditResult(filename="a.txt", device_score=61)
        r2 = _DeviceAuditResult(filename="b.txt", device_score=80)
        result = _compute_global_score([r1, r2])
        assert result in (70, 71)


# ─────────────────────────────────────────────────────────────────────────────
# Tests — _conformity_level
# ─────────────────────────────────────────────────────────────────────────────

class TestConformityLevel:

    def test_score_100_conforme(self) -> None:
        assert _conformity_level(100) == "CONFORME"

    def test_score_at_threshold_conforme(self) -> None:
        assert _conformity_level(SCORE_THRESHOLDS["conforme"]) == "CONFORME"

    def test_score_79_partiellement(self) -> None:
        assert _conformity_level(79) == "PARTIELLEMENT CONFORME"

    def test_score_at_threshold_partiel(self) -> None:
        assert _conformity_level(SCORE_THRESHOLDS["partiel"]) == "PARTIELLEMENT CONFORME"

    def test_score_49_non_conforme(self) -> None:
        assert _conformity_level(49) == "NON CONFORME"

    def test_score_zero_non_conforme(self) -> None:
        assert _conformity_level(0) == "NON CONFORME"


# ─────────────────────────────────────────────────────────────────────────────
# Tests — audit_snmp (interface publique)
# ─────────────────────────────────────────────────────────────────────────────

class TestAuditSnmp:

    def test_returns_dict_with_required_keys(self, snmp_dir_mixed: Path) -> None:
        rapport = audit_snmp(snmp_dir_mixed)
        required_keys = {
            "score", "conformity", "nb_files", "nb_v2c", "nb_v3",
            "nb_authpriv", "alerts", "recommendations", "devices", "baseline",
        }
        assert required_keys.issubset(rapport.keys())

    def test_nb_files_correct(self, snmp_dir_mixed: Path) -> None:
        rapport = audit_snmp(snmp_dir_mixed)
        assert rapport["nb_files"] == 4

    def test_score_range(self, snmp_dir_mixed: Path) -> None:
        rapport = audit_snmp(snmp_dir_mixed)
        assert 0 <= rapport["score"] <= 100

    def test_conformity_valid_value(self, snmp_dir_mixed: Path) -> None:
        rapport = audit_snmp(snmp_dir_mixed)
        assert rapport["conformity"] in {
            "CONFORME", "PARTIELLEMENT CONFORME", "NON CONFORME"
        }

    def test_all_v2c_low_score(self, snmp_dir_all_v2c: Path) -> None:
        rapport = audit_snmp(snmp_dir_all_v2c)
        assert rapport["score"] < SCORE_THRESHOLDS["conforme"]
        assert rapport["nb_v2c"] == 3
        assert rapport["nb_v3"] == 0

    def test_all_authpriv_high_score(self, snmp_dir_all_authpriv: Path) -> None:
        rapport = audit_snmp(snmp_dir_all_authpriv)
        assert rapport["score"] == 100
        assert rapport["conformity"] == "CONFORME"
        assert rapport["nb_authpriv"] == 3
        assert rapport["alerts"] == []

    def test_empty_dir_no_files(self, snmp_dir_empty: Path) -> None:
        rapport = audit_snmp(snmp_dir_empty)
        assert rapport["nb_files"] == 0
        assert rapport["score"] == 0

    def test_alerts_prefixed_with_filename(self, snmp_dir_mixed: Path) -> None:
        rapport = audit_snmp(snmp_dir_mixed)
        for alert in rapport["alerts"]:
            assert alert.startswith("[")

    def test_recommendations_not_empty(self, snmp_dir_mixed: Path) -> None:
        rapport = audit_snmp(snmp_dir_mixed)
        assert len(rapport["recommendations"]) > 0

    def test_devices_list_length(self, snmp_dir_mixed: Path) -> None:
        rapport = audit_snmp(snmp_dir_mixed)
        assert len(rapport["devices"]) == rapport["nb_files"]

    def test_device_dict_keys(self, snmp_dir_mixed: Path) -> None:
        rapport = audit_snmp(snmp_dir_mixed)
        required = {
            "filename", "has_v2c", "communities", "has_v3",
            "has_authpriv", "has_sha", "has_aes", "device_score", "alerts",
        }
        for device in rapport["devices"]:
            assert required.issubset(device.keys())

    def test_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            audit_snmp(tmp_path / "inexistant")

    def test_raises_not_a_directory(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_text("test", encoding="utf-8")
        with pytest.raises(NotADirectoryError):
            audit_snmp(f)

    def test_accepts_string_path(self, snmp_dir_all_authpriv: Path) -> None:
        rapport = audit_snmp(str(snmp_dir_all_authpriv))
        assert rapport["nb_files"] == 3

    def test_nb_v2c_count(self, snmp_dir_mixed: Path) -> None:
        rapport = audit_snmp(snmp_dir_mixed)
        assert rapport["nb_v2c"] == 2

    def test_nb_v3_count(self, snmp_dir_mixed: Path) -> None:
        rapport = audit_snmp(snmp_dir_mixed)
        assert rapport["nb_v3"] == 2

    def test_nb_authpriv_count(self, snmp_dir_mixed: Path) -> None:
        rapport = audit_snmp(snmp_dir_mixed)
        assert rapport["nb_authpriv"] == 1

    def test_weak_communities_detected(self, snmp_dir_mixed: Path) -> None:
        rapport = audit_snmp(snmp_dir_mixed)
        alerts_text = " ".join(rapport["alerts"])
        assert "public" in alerts_text or "private" in alerts_text

    def test_critique_recommendation_for_v2c(self, snmp_dir_all_v2c: Path) -> None:
        rapport = audit_snmp(snmp_dir_all_v2c)
        recs_text = " ".join(rapport["recommendations"])
        assert "CRITICAL" in recs_text

    def test_baseline_loaded(self, snmp_dir_mixed: Path) -> None:
        rapport = audit_snmp(snmp_dir_mixed)
        assert isinstance(rapport["baseline"], dict)


# ─────────────────────────────────────────────────────────────────────────────
# Tests — constantes et configuration
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:

    def test_weak_communities_contains_public_private(self) -> None:
        assert "public" in WEAK_COMMUNITIES
        assert "private" in WEAK_COMMUNITIES

    def test_score_thresholds_order(self) -> None:
        assert SCORE_THRESHOLDS["conforme"] > SCORE_THRESHOLDS["partiel"]

    def test_score_thresholds_in_range(self) -> None:
        for val in SCORE_THRESHOLDS.values():
            assert 0 <= val <= 100


# ─────────────────────────────────────────────────────────────────────────────
# Tests — run_audit() — UI adapter
# ─────────────────────────────────────────────────────────────────────────────

_V2C = "SNMPv2c::community.0 = STRING: public\n"
_V3N = "SNMPv3 authNoPriv\nauthProtocol SHA-256\n"
_V3A = "SNMPv3 authPriv\nauthProtocol SHA-256\nprivProtocol AES-256\n"


class TestRunAuditFallback:
    """run_audit() fallback when SNMP_DIR missing or empty."""

    def test_returns_dict(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.security.snmp_audit.SNMP_DIR", tmp_path / "none")
        assert isinstance(run_audit(), dict)

    def test_has_score(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.security.snmp_audit.SNMP_DIR", tmp_path / "none")
        assert "score" in run_audit()

    def test_has_devices_v2c(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.security.snmp_audit.SNMP_DIR", tmp_path / "none")
        assert "devices_v2c" in run_audit()

    def test_has_devices_v3(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.security.snmp_audit.SNMP_DIR", tmp_path / "none")
        assert "devices_v3" in run_audit()

    def test_has_events_detected(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.security.snmp_audit.SNMP_DIR", tmp_path / "none")
        assert "events_detected" in run_audit()

    def test_has_alerts(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.security.snmp_audit.SNMP_DIR", tmp_path / "none")
        assert "alerts" in run_audit()

    def test_has_devices(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.security.snmp_audit.SNMP_DIR", tmp_path / "none")
        assert "devices" in run_audit()

    def test_alerts_are_2tuples(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.security.snmp_audit.SNMP_DIR", tmp_path / "none")
        for a in run_audit()["alerts"]:
            assert isinstance(a, (list, tuple)) and len(a) == 2

    def test_devices_are_7tuples(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.security.snmp_audit.SNMP_DIR", tmp_path / "none")
        for d in run_audit()["devices"]:
            assert len(d) == 7

    def test_score_is_int(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.security.snmp_audit.SNMP_DIR", tmp_path / "none")
        assert isinstance(run_audit()["score"], int)

    def test_events_is_int(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.security.snmp_audit.SNMP_DIR", tmp_path / "none")
        assert isinstance(run_audit()["events_detected"], int)

    def test_empty_dir_triggers_fallback(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.security.snmp_audit.SNMP_DIR", tmp_path)
        r = run_audit()
        assert isinstance(r, dict) and "score" in r


class TestRunAuditReal:
    """run_audit() with synthetic SNMP files."""

    def _w(self, p, c):
        p.write_text(c, encoding="utf-8")

    def test_returns_dict(self, tmp_path, monkeypatch):
        self._w(tmp_path / "f.txt", _V3N)
        monkeypatch.setattr("src.security.snmp_audit.SNMP_DIR", tmp_path)
        assert isinstance(run_audit(), dict)

    def test_has_all_required_keys(self, tmp_path, monkeypatch):
        self._w(tmp_path / "f.txt", _V3N)
        monkeypatch.setattr("src.security.snmp_audit.SNMP_DIR", tmp_path)
        r = run_audit()
        for k in ("score", "devices_v2c", "devices_v3",
                  "events_detected", "alerts", "devices"):
            assert k in r

    def test_alerts_are_2tuples(self, tmp_path, monkeypatch):
        self._w(tmp_path / "f.txt", _V2C)
        monkeypatch.setattr("src.security.snmp_audit.SNMP_DIR", tmp_path)
        for a in run_audit()["alerts"]:
            assert isinstance(a, (list, tuple)) and len(a) == 2

    def test_v2c_public_is_critical(self, tmp_path, monkeypatch):
        self._w(tmp_path / "f.txt", _V2C)
        monkeypatch.setattr("src.security.snmp_audit.SNMP_DIR", tmp_path)
        assert "CRITICAL" in [s for s, _ in run_audit()["alerts"]]

    def test_score_in_range(self, tmp_path, monkeypatch):
        self._w(tmp_path / "f.txt", _V3A)
        monkeypatch.setattr("src.security.snmp_audit.SNMP_DIR", tmp_path)
        assert 0 <= run_audit()["score"] <= 100

    def test_v2c_count(self, tmp_path, monkeypatch):
        self._w(tmp_path / "a.txt", _V2C)
        self._w(tmp_path / "b.txt", _V2C)
        self._w(tmp_path / "c.txt", _V3A)
        monkeypatch.setattr("src.security.snmp_audit.SNMP_DIR", tmp_path)
        assert run_audit()["devices_v2c"] == 2

    def test_v3_count(self, tmp_path, monkeypatch):
        self._w(tmp_path / "a.txt", _V3A)
        self._w(tmp_path / "b.txt", _V3A)
        monkeypatch.setattr("src.security.snmp_audit.SNMP_DIR", tmp_path)
        assert run_audit()["devices_v3"] == 2

    def test_devices_are_7tuples(self, tmp_path, monkeypatch):
        self._w(tmp_path / "f.txt", _V3A)
        monkeypatch.setattr("src.security.snmp_audit.SNMP_DIR", tmp_path)
        for d in run_audit()["devices"]:
            assert len(d) == 7

    def test_events_int(self, tmp_path, monkeypatch):
        self._w(tmp_path / "f.txt", _V3N)
        monkeypatch.setattr("src.security.snmp_audit.SNMP_DIR", tmp_path)
        assert isinstance(run_audit()["events_detected"], int)

    def test_severity_valid(self, tmp_path, monkeypatch):
        self._w(tmp_path / "f.txt", _V2C)
        monkeypatch.setattr("src.security.snmp_audit.SNMP_DIR", tmp_path)
        for sev, _ in run_audit()["alerts"]:
            assert sev in {"CRITICAL", "MAJOR", "WARNING", "INFO"}

    def test_noauthnopriv_generates_alert(self, tmp_path, monkeypatch):
        self._w(tmp_path / "f.txt", _V3N)
        monkeypatch.setattr("src.security.snmp_audit.SNMP_DIR", tmp_path)
        assert len(run_audit()["alerts"]) > 0

    def test_authpriv_score_high(self, tmp_path, monkeypatch):
        self._w(tmp_path / "f.txt", _V3A)
        monkeypatch.setattr("src.security.snmp_audit.SNMP_DIR", tmp_path)
        assert run_audit()["score"] >= 70
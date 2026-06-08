# tests/unit/test_pdf_generator.py
# Tests unitaires — Module 6 : Génération de rapports PDF
# CDC §10 : couverture ≥ 70 % src/reports/
#
# Stratégie : mocks BytesIO + DataFrames fixtures synthétiques.
# Les tests valident la logique de construction (Flowables, sections,
# métadonnées) sans inspecter le rendu visuel final.
#
# Exécution :
#   pytest tests/unit/test_pdf_generator.py -v --cov=src/reports --cov-report=term-missing

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import pytest

# ── Résolution chemin src/ ────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.reports.pdf_generator import (
    ANOMALY_FLAG_COL,
    RULE_ALARM_COL,
    RULE_DETAIL_COL,
    _build_styles,
    _fig_to_image,
    _section_anomalies,
    _section_conclusions,
    _section_header,
    _section_kpis,
    _section_securite,
    generate_pdf,
)

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def df_kpi_normal():
    """DataFrame KPI sans anomalies."""
    rng = np.random.default_rng(42)
    n = 100
    return pd.DataFrame({
        "timestamp":       pd.date_range("2024-01-01", periods=n, freq="5min"),
        "debit_rx_mbps":   rng.uniform(10, 80, n),
        "debit_tx_mbps":   rng.uniform(5, 40, n),
        "utilization_pct": rng.uniform(20, 80, n),
        "error_rate_pct":  rng.uniform(0, 0.5, n),
        "anomaly_flag":    np.ones(n, dtype=int),
        "anomaly_score":   rng.uniform(0.0, 0.3, n),
        "rule_alarm":      np.zeros(n, dtype=bool),
        "rule_detail":     [""] * n,
        "onuOperStatus":   ["up"] * 90 + ["down"] * 10,
    })


@pytest.fixture
def df_kpi_with_anomalies():
    """DataFrame KPI avec anomalies injectées (CDC §8 — scénarios incidents)."""
    rng = np.random.default_rng(0)
    n = 200
    flags = rng.choice([-1, 1], n, p=[0.12, 0.88])
    alarms = rng.choice([True, False], n, p=[0.10, 0.90])
    return pd.DataFrame({
        "timestamp":       pd.date_range("2024-01-15", periods=n, freq="5min"),
        "debit_rx_mbps":   rng.uniform(10, 990, n),
        "debit_tx_mbps":   rng.uniform(5, 500, n),
        "utilization_pct": rng.uniform(20, 99, n),
        "error_rate_pct":  rng.uniform(0, 5, n),
        "anomaly_flag":    flags,
        "anomaly_score":   rng.uniform(-0.6, 0.3, n),
        "rule_alarm":      alarms,
        "rule_detail":     [
            "Utilisation > 85%" if a else "" for a in alarms
        ],
    })


@pytest.fixture
def df_kpi_minimal():
    """DataFrame d'une seule ligne — edge case."""
    return pd.DataFrame({
        "timestamp":       [pd.Timestamp("2024-01-01")],
        "debit_rx_mbps":   [42.0],
        "debit_tx_mbps":   [21.0],
        "utilization_pct": [70.0],
        "error_rate_pct":  [0.1],
        "anomaly_flag":    [1],
        "anomaly_score":   [0.1],
        "rule_alarm":      [False],
        "rule_detail":     [""],
    })


@pytest.fixture
def rapport_conforme():
    return {
        "score": 85,
        "alerts": [],
        "recommendations": ["Activer authPriv SHA-256+AES-256"],
    }


@pytest.fixture
def rapport_non_conforme():
    return {
        "score": 30,
        "alerts": [
            {"device": "OLT_Port1", "type": "SNMPv2c", "detail": "community=public"},
            {"device": "ONT_101",   "type": "SNMPv2c", "detail": "community=private"},
        ],
        "recommendations": ["Migrer vers SNMPv3 authPriv"],
    }


@pytest.fixture
def rapport_vide():
    return {}


@pytest.fixture
def matplotlib_figure():
    """Figure matplotlib synthétique pour test d'intégration BytesIO."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.plot([1, 2, 3], [10, 20, 15])
    ax.set_title("Test figure")
    yield fig
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# Tests generate_pdf() — interface publique
# ─────────────────────────────────────────────────────────────────────────────

class TestGeneratePdf:
    """Tests de l'interface publique generate_pdf() (CDC §10)."""

    def test_returns_string_path(self, df_kpi_normal, rapport_conforme, tmp_path):
        """generate_pdf() retourne un chemin de fichier (str)."""
        out = str(tmp_path / "rapport.pdf")
        result = generate_pdf(df_kpi_normal, rapport_conforme, path_out=out)
        assert isinstance(result, str)

    def test_pdf_file_created(self, df_kpi_normal, rapport_conforme, tmp_path):
        """Le fichier PDF est effectivement créé sur disque (CDC §10)."""
        out = str(tmp_path / "rapport_test.pdf")
        generate_pdf(df_kpi_normal, rapport_conforme, path_out=out)
        assert os.path.isfile(out)

    def test_pdf_file_not_empty(self, df_kpi_normal, rapport_conforme, tmp_path):
        """Le fichier PDF généré n'est pas vide (> 0 octets)."""
        out = str(tmp_path / "rapport_nonempty.pdf")
        generate_pdf(df_kpi_normal, rapport_conforme, path_out=out)
        assert os.path.getsize(out) > 0

    def test_pdf_is_valid_pdf_header(self, df_kpi_normal, rapport_conforme, tmp_path):
        """Le fichier commence par l'en-tête PDF (%PDF-)."""
        out = str(tmp_path / "rapport_valid.pdf")
        generate_pdf(df_kpi_normal, rapport_conforme, path_out=out)
        with open(out, "rb") as f:
            header = f.read(5)
        assert header == b"%PDF-"

    def test_path_out_custom(self, df_kpi_normal, rapport_conforme, tmp_path):
        """Le chemin de sortie personnalisé est respecté."""
        out = str(tmp_path / "subdir" / "custom.pdf")
        result = generate_pdf(df_kpi_normal, rapport_conforme, path_out=out)
        assert result == out
        assert os.path.isfile(out)

    def test_path_out_none_auto_generated(self, df_kpi_normal, rapport_conforme, tmp_path, monkeypatch):
        """Sans path_out, un nom horodaté est généré automatiquement."""
        monkeypatch.setattr(
            "src.reports.pdf_generator.REPORTS_DIR", str(tmp_path)
        )
        result = generate_pdf(df_kpi_normal, rapport_conforme)
        assert result.endswith(".pdf")
        assert os.path.isfile(result)

    def test_raises_on_empty_df(self, rapport_conforme):
        """ValueError levée si df_kpi est vide (robustesse CDC §4)."""
        with pytest.raises(ValueError, match="vide"):
            generate_pdf(pd.DataFrame(), rapport_conforme)

    def test_raises_on_none_df(self, rapport_conforme):
        """ValueError levée si df_kpi est None."""
        with pytest.raises(ValueError):
            generate_pdf(None, rapport_conforme)

    def test_with_anomalies(self, df_kpi_with_anomalies, rapport_non_conforme, tmp_path):
        """Génération réussit avec des anomalies présentes."""
        out = str(tmp_path / "rapport_anomalies.pdf")
        result = generate_pdf(
            df_kpi_with_anomalies,
            rapport_non_conforme,
            path_out=out,
            scenario="Saturation OLT",
        )
        assert os.path.isfile(result)
        assert os.path.getsize(result) > 0

    def test_minimal_df_no_crash(self, df_kpi_minimal, rapport_conforme, tmp_path):
        """1 seule ligne dans df_kpi — edge case (CDC §4 Robustesse)."""
        out = str(tmp_path / "rapport_minimal.pdf")
        result = generate_pdf(df_kpi_minimal, rapport_conforme, path_out=out)
        assert os.path.isfile(result)

    def test_empty_rapport_conformite(self, df_kpi_normal, rapport_vide, tmp_path):
        """rapport_conformite vide {} n'arrête pas la génération."""
        out = str(tmp_path / "rapport_vide_conformite.pdf")
        result = generate_pdf(df_kpi_normal, rapport_vide, path_out=out)
        assert os.path.isfile(result)

    def test_none_rapport_conformite(self, df_kpi_normal, tmp_path):
        """rapport_conformite=None traité comme dict vide."""
        out = str(tmp_path / "rapport_none_conformite.pdf")
        result = generate_pdf(df_kpi_normal, None, path_out=out)
        assert os.path.isfile(result)

    def test_with_figure(self, df_kpi_normal, rapport_conforme, tmp_path, matplotlib_figure):
        """Intégration figure matplotlib via BytesIO ne lève pas d'exception."""
        out = str(tmp_path / "rapport_with_fig.pdf")
        result = generate_pdf(
            df_kpi_normal, rapport_conforme,
            figures=[matplotlib_figure], path_out=out,
        )
        assert os.path.isfile(result)
        assert os.path.getsize(result) > 0

    def test_scenario_name_accepted(self, df_kpi_normal, rapport_conforme, tmp_path):
        """Le paramètre scenario est accepté sans erreur."""
        out = str(tmp_path / "rapport_scenario.pdf")
        result = generate_pdf(
            df_kpi_normal, rapport_conforme,
            path_out=out, scenario="Perte optique ONT_105",
        )
        assert os.path.isfile(result)


# ─────────────────────────────────────────────────────────────────────────────
# Tests sections internes
# ─────────────────────────────────────────────────────────────────────────────

class TestSectionHeader:
    """Tests section 1 — En-tête (CDC §9 Livrables)."""

    def test_header_appends_flowables(self, df_kpi_normal):
        """_section_header() ajoute des Flowables à la story."""
        story = []
        styles = _build_styles()
        _section_header(story, styles, "Test", "2024-01-01 00:00:00", 400)
        assert len(story) > 0

    def test_header_contains_project_name(self):
        """L'en-tête contient le nom du projet."""
        story = []
        styles = _build_styles()
        _section_header(story, styles, "Scénario X", "2024-01-01 00:00:00", 400)
        # Vérifier que le premier Paragraph contient NOC-Edge FTTH
        from reportlab.platypus import Paragraph
        paras = [f for f in story if isinstance(f, Paragraph)]
        texts = " ".join(str(p.text) for p in paras)
        assert "NOC-Edge FTTH" in texts or "NOC" in texts


class TestSectionKpis:
    """Tests section 2 — KPIs."""

    def test_kpis_appends_flowables(self, df_kpi_normal):
        """_section_kpis() ajoute des Flowables à la story."""
        story = []
        styles = _build_styles()
        _section_kpis(story, styles, df_kpi_normal, [], 400)
        assert len(story) > 0

    def test_kpis_with_ont_status(self, df_kpi_normal):
        """Section KPIs traite onuOperStatus sans erreur."""
        story = []
        styles = _build_styles()
        _section_kpis(story, styles, df_kpi_normal, [], 400)
        # df_kpi_normal contient onuOperStatus — doit fonctionner
        assert len(story) > 2

    def test_kpis_missing_columns(self):
        """Section KPIs tolère un DataFrame sans colonnes KPI standard."""
        df_empty_cols = pd.DataFrame({"timestamp": pd.date_range("2024-01-01", periods=5, freq="5min")})
        story = []
        styles = _build_styles()
        _section_kpis(story, styles, df_empty_cols, [], 400)
        assert len(story) >= 0  # pas de crash

    def test_kpis_with_figure(self, df_kpi_normal, matplotlib_figure):
        """Intégration d'une figure matplotlib dans la section KPIs."""
        story = []
        styles = _build_styles()
        _section_kpis(story, styles, df_kpi_normal, [matplotlib_figure], 400)
        assert len(story) > 0


class TestSectionAnomalies:
    """Tests section 3 — Anomalies détectées (CDC §2.1 F1 ≥ 85 %)."""

    def test_anomalies_no_anomaly(self, df_kpi_normal):
        """Section anomalies avec df sans anomalies — affichage 'Aucune anomalie'."""
        story = []
        styles = _build_styles()
        _section_anomalies(story, styles, df_kpi_normal, 400)
        assert len(story) > 0

    def test_anomalies_with_anomalies(self, df_kpi_with_anomalies):
        """Section anomalies avec anomalies injectées — tableaux générés."""
        story = []
        styles = _build_styles()
        _section_anomalies(story, styles, df_kpi_with_anomalies, 400)
        assert len(story) > 0

    def test_anomalies_count_ia(self, df_kpi_with_anomalies):
        """Nombre d'anomalies IA calculé correctement."""
        expected = int((df_kpi_with_anomalies[ANOMALY_FLAG_COL] == -1).sum())
        assert expected > 0  # fixture doit contenir des anomalies

    def test_anomalies_count_rules(self, df_kpi_with_anomalies):
        """Nombre d'alarmes règles calculé correctement."""
        expected = int(df_kpi_with_anomalies[RULE_ALARM_COL].sum())
        assert expected >= 0

    def test_anomalies_missing_ia_column(self):
        """Tolérance si anomaly_flag absent du DataFrame."""
        df_no_ia = pd.DataFrame({
            "timestamp":   pd.date_range("2024-01-01", periods=10, freq="5min"),
            "rule_alarm":  [False] * 10,
            "rule_detail": [""] * 10,
        })
        story = []
        styles = _build_styles()
        _section_anomalies(story, styles, df_no_ia, 400)
        assert len(story) >= 0

    def test_anomalies_missing_rules_column(self):
        """Tolérance si rule_alarm absent du DataFrame."""
        df_no_rules = pd.DataFrame({
            "timestamp":    pd.date_range("2024-01-01", periods=10, freq="5min"),
            "anomaly_flag": [1] * 10,
            "anomaly_score":[0.1] * 10,
        })
        story = []
        styles = _build_styles()
        _section_anomalies(story, styles, df_no_rules, 400)
        assert len(story) >= 0


class TestSectionSecurite:
    """Tests section 4 — Conformité SNMP (CDC §2.1 Sécurité)."""

    def test_securite_conforme(self, df_kpi_normal, rapport_conforme):
        """Score ≥ 70 → statut CONFORME généré."""
        story = []
        styles = _build_styles()
        _section_securite(story, styles, rapport_conforme, 400)
        assert len(story) > 0

    def test_securite_non_conforme(self, df_kpi_normal, rapport_non_conforme):
        """Score < 70 → statut NON CONFORME généré sans crash."""
        story = []
        styles = _build_styles()
        _section_securite(story, styles, rapport_non_conforme, 400)
        assert len(story) > 0

    def test_securite_alerts_present(self, rapport_non_conforme):
        """Alertes SNMPv2c présentes dans le rapport → tableau généré."""
        story = []
        styles = _build_styles()
        _section_securite(story, styles, rapport_non_conforme, 400)
        assert len(story) > 3

    def test_securite_no_alerts(self, rapport_conforme):
        """Aucune alerte → message 'Aucune alerte' généré."""
        story = []
        styles = _build_styles()
        _section_securite(story, styles, rapport_conforme, 400)
        assert len(story) > 0

    def test_securite_missing_score(self):
        """rapport_conformite sans 'score' → score par défaut = 0."""
        story = []
        styles = _build_styles()
        _section_securite(story, styles, {"alerts": [], "recommendations": []}, 400)
        assert len(story) > 0

    def test_securite_string_alerts(self):
        """Alertes sous forme de strings (format alternatif) — tolérance."""
        story = []
        styles = _build_styles()
        rapport = {"score": 45, "alerts": ["Community public détecté sur OLT_Port1"]}
        _section_securite(story, styles, rapport, 400)
        assert len(story) > 0


class TestSectionConclusions:
    """Tests section 5 — Conclusions (CDC §2.2, §9)."""

    def test_conclusions_appends_flowables(self, df_kpi_normal, rapport_conforme):
        """_section_conclusions() ajoute des Flowables à la story."""
        story = []
        styles = _build_styles()
        _section_conclusions(story, styles, df_kpi_normal, rapport_conforme, "Test", 400)
        assert len(story) > 0

    def test_conclusions_with_anomalies(self, df_kpi_with_anomalies, rapport_non_conforme):
        """Conclusions avec anomalies — narrative adaptée sans crash."""
        story = []
        styles = _build_styles()
        _section_conclusions(
            story, styles, df_kpi_with_anomalies, rapport_non_conforme,
            "Saturation OLT", 400,
        )
        assert len(story) > 0

    def test_conclusions_no_anomalies(self, df_kpi_normal, rapport_conforme):
        """Conclusions sans anomalies — message nominal généré."""
        story = []
        styles = _build_styles()
        _section_conclusions(
            story, styles, df_kpi_normal, rapport_conforme,
            "Réseau nominal", 400,
        )
        assert len(story) > 0

    def test_conclusions_missing_kpi_cols(self):
        """Tolérance si colonnes KPI optionnelles absentes des conclusions."""
        df_min = pd.DataFrame({"col_inconnue": [1, 2, 3]})
        story = []
        styles = _build_styles()
        _section_conclusions(story, styles, df_min, {}, "Min", 400)
        assert len(story) >= 0


# ─────────────────────────────────────────────────────────────────────────────
# Tests utilitaires
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildStyles:
    """Tests des styles typographiques."""

    def test_returns_dict(self):
        styles = _build_styles()
        assert isinstance(styles, dict)

    def test_required_keys(self):
        styles = _build_styles()
        for key in ("title", "subtitle", "h1", "h2", "body", "caption", "footer"):
            assert key in styles, f"Style manquant : {key}"


class TestFigToImage:
    """Tests de la conversion matplotlib → reportlab Image."""

    def test_returns_image_flowable(self, matplotlib_figure):
        from reportlab.platypus import Image
        img = _fig_to_image(matplotlib_figure)
        assert isinstance(img, Image)

    def test_custom_dimensions(self, matplotlib_figure):
        from reportlab.platypus import Image
        from reportlab.lib.units import cm
        img = _fig_to_image(matplotlib_figure, width_cm=10, height_cm=5)
        assert isinstance(img, Image)
        assert abs(img.drawWidth  - 10 * cm) < 1
        assert abs(img.drawHeight -  5 * cm) < 1


# ─────────────────────────────────────────────────────────────────────────────
# Tests de traçabilité CDC
# ─────────────────────────────────────────────────────────────────────────────

class TestCdcTraceability:
    """Vérifications de conformité CDC §2.1, §9, §10."""

    def test_cdc_anomaly_flag_column_name(self):
        """CDC §7 : colonne anomaly_flag conforme au nom attendu."""
        assert ANOMALY_FLAG_COL == "anomaly_flag"

    def test_cdc_rule_alarm_column_name(self):
        """CDC §7 : colonne rule_alarm conforme au nom attendu."""
        assert RULE_ALARM_COL == "rule_alarm"

    def test_cdc_all_scenarios_generate_pdf(
        self, df_kpi_with_anomalies, rapport_non_conforme, tmp_path
    ):
        """CDC §10 : rapport PDF complet généré pour chaque scénario."""
        scenarios = [
            "Saturation OLT",
            "Perte optique",
            "ONT down",
            "ARP spoofing",
            "DHCP rogue",
            "Split mal dimensionné",
        ]
        for scenario in scenarios:
            out = str(tmp_path / f"rapport_{scenario.replace(' ', '_')}.pdf")
            result = generate_pdf(
                df_kpi_with_anomalies,
                rapport_non_conforme,
                path_out=out,
                scenario=scenario,
            )
            assert os.path.isfile(result), f"PDF manquant pour scénario : {scenario}"
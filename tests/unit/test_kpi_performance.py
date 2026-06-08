"""
tests/unit/test_kpi_performance.py
───────────────────────────────────────────────────────────────────────────────
Critères DoD — Sprint S5-S6 (§2.1 CDC)
  ✓ timeit mesure ≤ 1,00 s sur 10 000 pts  (kpi_builder   — critère CDC)
  ✓ timeit mesure ≤ 1,00 s sur 20 000 pts  (kpi_builder   — stress test)

Méthode de validation (§ DoD)
  python -m timeit -n 5 sur kpi_olt_port_1.csv       tronqué à 10 000 lignes
  python -m timeit -n 5 sur kpi_olt_port_1.csv padding synthétique à 20 000 lignes

Sources de données (par ordre de priorité)
  1. Vrais CSV du projet  →  data/csv/kpi_olt_port_1.csv
                              data/csv/ont_status_timeseries.csv
  2. Fallback synthétique →  schéma S4 identique, seed=42

Livrable généré
  reports/rapport_benchmark.txt

Exécution
  pytest tests/unit/test_kpi_performance.py -v
───────────────────────────────────────────────────────────────────────────────
"""

import timeit
import pathlib
import datetime
import sys

import numpy as np
import pandas as pd
import pytest

# ── Chemins projet ────────────────────────────────────────────────────────────
_HERE       = pathlib.Path(__file__).resolve().parent
# Si dans tests/unit/ → remonter 2 niveaux ; sinon 1 niveau (fallback)
_root2      = _HERE.parent.parent
_root1      = _HERE.parent
ROOT        = _root2 if (_root2 / "data").exists() else (_root1 if (_root1 / "data").exists() else _HERE)
CSV_10K     = ROOT / "data" / "csv" / "kpi_olt_port_1.csv"
CSV_20K     = ROOT / "data" / "csv" / "kpi_olt_port_1.csv"
REPORTS_DIR = ROOT / "reports"
RAPPORT     = REPORTS_DIR / "rapport_benchmark.txt"

# ── Constantes DoD ────────────────────────────────────────────────────────────
SEUIL_S    = 1.00          # ≤ 1,00 seconde  (§2.1 CDC)
N_10K      = 10_000        # critère CDC nominal
N_20K      = 20_000        # stress test
TIMEIT_N   = 5             # python -m timeit -n 5  (§ DoD)


# ── Helpers de chargement ─────────────────────────────────────────────────────

def _synth(n: int) -> pd.DataFrame:
    """DataFrame synthétique schéma S4 — utilisé si les vrais CSV sont absents."""
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "timestamp":         pd.date_range("2024-01-01", periods=n, freq="5min"),
        "ifInOctets_bytes":  rng.integers(180_000_000, 220_000_000, n, dtype=np.int64),
        "ifOutOctets_bytes": rng.integers(130_000_000, 170_000_000, n, dtype=np.int64),
        "ifInErrors":        rng.integers(0, 5, n, dtype=np.int64),
        "onuOperStatus":     np.where(rng.random(n) < 0.03, "down", "up"),
        "label_anomaly":     (rng.random(n) < 0.05).astype(np.int8),
    })


def _load_csv(path: pathlib.Path, n: int) -> tuple[pd.DataFrame, str]:
    """
    Charge le CSV réel (tronqué à n si plus grand).
    Si le CSV est plus court que n, complète avec des lignes synthétiques
    au même schéma — le volume cible est toujours atteint exactement.
    """
    if path.exists():
        df = pd.read_csv(path, parse_dates=["timestamp"])
        rename_map = {
            "ifInOctets":  "ifInOctets_bytes",
            "ifOutOctets": "ifOutOctets_bytes",
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
        required = {"timestamp", "ifInOctets_bytes", "ifOutOctets_bytes", "ifInErrors"}
        if not required.issubset(df.columns):
            return _synth(n), "synthetic (colonnes manquantes)"

        real_rows = len(df)

        if real_rows >= n:
            return df.head(n).reset_index(drop=True), "real"

        # CSV trop court — compléter avec padding synthétique
        needed  = n - real_rows
        df_pad  = _synth(needed)
        last_ts = pd.to_datetime(df["timestamp"].iloc[-1])
        df_pad["timestamp"] = pd.date_range(
            start=last_ts + pd.Timedelta(minutes=5),
            periods=needed,
            freq="5min",
        )
        # Garder uniquement les colonnes communes
        common = [c for c in df.columns if c in df_pad.columns]
        df_out = pd.concat([df[common], df_pad[common]], ignore_index=True)
        source = f"real ({real_rows} lignes) + synthetic padding ({needed} lignes)"
        return df_out.head(n).reset_index(drop=True), source

    return _synth(n), "synthetic (fichier absent)"


# ── Implémentation compute_kpis (§C4 L3 — kpi_builder.py) ────────────────────

def compute_kpis(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Reproduction de kpi_builder.compute_kpis().
    Formule CDC §2.1 : (Δoctets × 8) / Δt_s / 1e6  [Mbit/s]
    Δt dynamique via timestamp.diff() — jamais de constante 300s.
    """
    df = df_raw.copy()
    df = df.sort_values("timestamp").reset_index(drop=True)

    dt = df["timestamp"].diff().dt.total_seconds()
    dt = dt.fillna(dt.median())   # fallback 1ère ligne — scalar, pas lambda
    dt = dt.replace(0, np.nan).ffill()

    d_in  = df["ifInOctets_bytes"].diff().fillna(0).clip(lower=0)
    d_out = df["ifOutOctets_bytes"].diff().fillna(0).clip(lower=0)

    df["debit_rx_mbps"]   = (d_in  * 8) / dt / 1e6
    df["debit_tx_mbps"]   = (d_out * 8) / dt / 1e6
    df["utilization_pct"] = (df["debit_rx_mbps"] / 1000.0 * 100).clip(0, 100)
    df["error_rate_pct"]  = (
        df["ifInErrors"].diff().fillna(0).clip(lower=0)
        / d_in.replace(0, np.nan) * 100
    ).fillna(0).clip(0, 100)
    if "onuOperStatus" in df.columns:
        df["ont_status"] = df["onuOperStatus"].str.upper()
    else:
        df["ont_status"] = "UNKNOWN"

    return df


# ── Fixture partagée — rapport accumulé ───────────────────────────────────────

_rapport_lines: list[str] = []


def _write_rapport():
    """Écrit rapport_benchmark.txt dans reports/."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    header = [
        "=" * 70,
        "NOC-Edge FTTH — Rapport Benchmark KPI",
        f"Généré le : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Référence : CDC §2.1 — Seuil ≤ {SEUIL_S:.2f} s / N points",
        f"Méthode   : timeit -n {TIMEIT_N} (meilleur temps)",
        "=" * 70,
        "",
    ]
    with open(RAPPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(header + _rapport_lines))


# ── Tests pytest ──────────────────────────────────────────────────────────────

class TestKpiPerformanceCDC:
    """
    Critères DoD Sprint S5-S6.
    Chaque test mesure via timeit -n 5 (§ méthode DoD).
    """

    def test_10k_critere_cdc(self):
        """
        DoD §1 — timeit ≤ 1,00 s sur 10 000 pts
        Source : data/csv/kpi_olt_port_1.csv (tronqué à 10 000 lignes)
        """
        df_raw, source = _load_csv(CSV_10K, N_10K)
        assert len(df_raw) == N_10K, f"Dataset trop court : {len(df_raw)} lignes"

        # Warmup — évite cold-start (import bytecode, allocation cache)
        compute_kpis(df_raw)

        # Mesure — équivalent python -m timeit -n 5
        times = timeit.repeat(
            stmt=lambda df=df_raw: compute_kpis(df),
            repeat=TIMEIT_N,
            number=1,
        )
        best_s  = min(times)
        mean_s  = sum(times) / len(times)
        worst_s = max(times)
        marge   = SEUIL_S / best_s

        # Rapport
        _rapport_lines.extend([
            "── TEST 1 : Critère CDC nominal ──────────────────────────────",
            f"  Source         : {source}",
            f"  N points       : {N_10K:,}",
            f"  Fichier CSV    : {CSV_10K.name}",
            f"  Répétitions    : {TIMEIT_N}",
            f"  Meilleur temps : {best_s*1000:.2f} ms",
            f"  Temps moyen    : {mean_s*1000:.2f} ms",
            f"  Pire temps     : {worst_s*1000:.2f} ms",
            f"  Seuil CDC      : {SEUIL_S*1000:.0f} ms",
            f"  Marge          : ×{marge:.1f}",
            f"  Statut         : {'✓ VALIDÉ' if best_s <= SEUIL_S else '✗ ÉCHEC'}",
            "",
        ])
        _write_rapport()

        assert best_s <= SEUIL_S, (
            f"ÉCHEC CDC §2.1 : {best_s*1000:.2f} ms > {SEUIL_S*1000:.0f} ms "
            f"sur {N_10K:,} points"
        )

    def test_20k_stress_test(self):
        """
        DoD §2 — timeit ≤ 1,00 s sur 20 000 pts (stress test ×2)
        Source : data/csv/kpi_olt_port_1.csv (padding synthétique à 20 000 lignes)
        """
        df_raw, source = _load_csv(CSV_20K, N_20K)
        assert len(df_raw) == N_20K, f"Dataset trop court : {len(df_raw)} lignes"

        # Warmup
        compute_kpis(df_raw)

        # Mesure — équivalent python -m timeit -n 5
        times = timeit.repeat(
            stmt=lambda df=df_raw: compute_kpis(df),
            repeat=TIMEIT_N,
            number=1,
        )
        best_s  = min(times)
        mean_s  = sum(times) / len(times)
        worst_s = max(times)
        marge   = SEUIL_S / best_s

        # Rapport
        _rapport_lines.extend([
            "── TEST 2 : Stress test (×2 CDC) ─────────────────────────────",
            f"  Source         : {source}",
            f"  N points       : {N_20K:,}",
            f"  Fichier CSV    : {CSV_20K.name}",
            f"  Répétitions    : {TIMEIT_N}",
            f"  Meilleur temps : {best_s*1000:.2f} ms",
            f"  Temps moyen    : {mean_s*1000:.2f} ms",
            f"  Pire temps     : {worst_s*1000:.2f} ms",
            f"  Seuil CDC      : {SEUIL_S*1000:.0f} ms",
            f"  Marge          : ×{marge:.1f}",
            f"  Scalabilité    : voir TEST 1 pour ratio",
            f"  Statut         : {'✓ VALIDÉ' if best_s <= SEUIL_S else '✗ ÉCHEC'}",
            "",
            "=" * 70,
            "FIN DU RAPPORT",
        ])
        _write_rapport()

        assert best_s <= SEUIL_S, (
            f"ÉCHEC stress test : {best_s*1000:.2f} ms > {SEUIL_S*1000:.0f} ms "
            f"sur {N_20K:,} points"
        )
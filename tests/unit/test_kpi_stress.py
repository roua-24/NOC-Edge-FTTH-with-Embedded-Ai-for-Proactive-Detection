"""
tests/unit/test_kpi_stress.py
───────────────────────────────────────────────────────────────────────────────
Sprint S5-S6 — Stress Test uniquement
CDC §2.1 : timeit ≤ 1,00 s sur 20 000 pts (marge x2 du critere nominal)

NB : le critere nominal 10 000 pts est deja valide dans kpi_builder.py (S4).
     Ce fichier couvre uniquement le stress test supplementaire S5-S6.

Source  : data/csv/kpi_olt_port_1.csv — padding synthetique si < 20 000 lignes
Livrable: reports/rapport_benchmark.txt

Execution
  pytest tests/unit/test_kpi_stress.py -v
───────────────────────────────────────────────────────────────────────────────
"""

import timeit
import pathlib
import datetime

import numpy as np
import pandas as pd
import pytest

# ── Chemins projet ────────────────────────────────────────────────────────────
_HERE = pathlib.Path(__file__).resolve().parent
_root2 = _HERE.parent.parent
_root1 = _HERE.parent
ROOT = (
    _root2 if (_root2 / "data").exists()
    else _root1 if (_root1 / "data").exists()
    else _HERE
)
CSV_KPI     = ROOT / "data" / "csv" / "kpi_olt_port_1.csv"
REPORTS_DIR = ROOT / "reports"
RAPPORT     = REPORTS_DIR / "rapport_benchmark.txt"

# ── Constantes DoD ────────────────────────────────────────────────────────────
SEUIL_S  = 1.00       # <= 1,00 s  (CDC §2.1)
N_20K    = 20_000     # stress test x2 du critere nominal
TIMEIT_N = 5          # python -m timeit -n 5  (methode DoD)


# ── Chargement kpi_olt_port_1.csv — padding si < 20 000 lignes ───────────────

def _load_20k() -> tuple[pd.DataFrame, str]:
    """
    Charge kpi_olt_port_1.csv (8 640 lignes reelles).
    Complete avec padding synthetique au meme schema jusqu'a 20 000 lignes.
    """
    if not CSV_KPI.exists():
        return _synth(N_20K), "synthetic (fichier absent)"

    df = pd.read_csv(CSV_KPI, parse_dates=["timestamp"])
    real = len(df)

    if real >= N_20K:
        return df.head(N_20K).reset_index(drop=True), f"real ({real} lignes)"

    needed  = N_20K - real
    pad     = _synth(needed)
    last_ts = pd.to_datetime(df["timestamp"].iloc[-1])
    pad["timestamp"] = pd.date_range(
        start=last_ts + pd.Timedelta(minutes=5),
        periods=needed,
        freq="5min",
    )
    common = [c for c in df.columns if c in pad.columns]
    df_out = pd.concat([df[common], pad[common]], ignore_index=True)
    source = f"real ({real}) + synthetic padding ({needed})"
    return df_out.head(N_20K).reset_index(drop=True), source


def _synth(n: int) -> pd.DataFrame:
    """Donnees synthetiques schema S4 — colonnes identiques a kpi_olt_port_1.csv."""
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "timestamp":         pd.date_range("2024-01-01", periods=n, freq="5min"),
        "ifInOctets_bytes":  rng.integers(180_000_000, 220_000_000, n, dtype=np.int64),
        "ifOutOctets_bytes": rng.integers(130_000_000, 170_000_000, n, dtype=np.int64),
        "ifInErrors":        rng.integers(0, 5, n, dtype=np.int64),
        "ifOutErrors":       rng.integers(0, 3, n, dtype=np.int64),
        "utilization_pct":   rng.uniform(5, 95, n),
        "label_anomaly":     (rng.random(n) < 0.05).astype(np.int8),
    })


# ── compute_kpis — appel au module reel si disponible, sinon reproduction ─────

def _get_compute_kpis():
    """
    Utilise kpi_builder.compute_kpis() si le module est importable.
    Sinon utilise la reproduction locale (meme formule CDC §2.1).
    """
    try:
        import sys
        sys.path.insert(0, str(ROOT / "src"))
        from kpi.kpi_builder import compute_kpis
        return compute_kpis, "kpi_builder.compute_kpis() (module reel)"
    except ImportError:
        return _compute_kpis_local, "_compute_kpis_local (reproduction)"


def _compute_kpis_local(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Reproduction de kpi_builder.compute_kpis().
    Formule CDC §2.1 : (Delta_octets x 8) / Delta_t_s / 1e6  [Mbit/s]
    Delta_t dynamique via timestamp.diff() — jamais de constante codee en dur.
    """
    df = df_raw.copy()
    df = df.sort_values("timestamp").reset_index(drop=True)

    dt = df["timestamp"].diff().dt.total_seconds()
    dt = dt.fillna(dt.median())
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

    return df


# ── Rapport ───────────────────────────────────────────────────────────────────

def _write_rapport(source: str, best_s: float, mean_s: float,
                   worst_s: float, impl: str) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "=" * 70,
        "NOC-Edge FTTH — Rapport Stress Test KPI (S5-S6)",
        f"Genere le : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Reference : CDC §2.1 — Seuil <= {SEUIL_S:.2f} s / {N_20K:,} pts",
        f"Methode   : timeit -n {TIMEIT_N} (meilleur temps)",
        "=" * 70,
        "",
        "── Stress Test : 20 000 pts (x2 critere CDC nominal) ─────────────",
        f"  Implementation : {impl}",
        f"  Source         : {source}",
        f"  N points       : {N_20K:,}",
        f"  Fichier CSV    : {CSV_KPI.name}",
        f"  Repetitions    : {TIMEIT_N}",
        f"  Meilleur temps : {best_s*1000:.2f} ms",
        f"  Temps moyen    : {mean_s*1000:.2f} ms",
        f"  Pire temps     : {worst_s*1000:.2f} ms",
        f"  Seuil CDC      : {SEUIL_S*1000:.0f} ms",
        f"  Marge          : x{SEUIL_S/best_s:.1f}",
        f"  Statut         : {'OK VALIDE' if best_s <= SEUIL_S else 'ECHEC'}",
        "",
        "=" * 70,
        "FIN DU RAPPORT",
    ]
    with open(RAPPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ── Test ──────────────────────────────────────────────────────────────────────

class TestKpiStress:
    """
    Stress test S5-S6 : timeit <= 1,00 s sur 20 000 pts.
    Le critere nominal 10 000 pts est deja couvert par test_kpi_builder.py (S4).
    """

    def test_stress_20k(self):
        """
        CDC §2.1 stress test — 20 000 pts (x2 du critere nominal).
        Source : kpi_olt_port_1.csv + padding synthetique jusqu'a 20 000 lignes.
        """
        compute_kpis, impl = _get_compute_kpis()
        df_raw, source = _load_20k()

        assert len(df_raw) == N_20K, (
            f"Volume incorrect : {len(df_raw)} lignes au lieu de {N_20K}"
        )

        # Warmup — evite cold-start
        compute_kpis(df_raw)

        # Mesure — python -m timeit -n 5
        times = timeit.repeat(
            stmt=lambda df=df_raw: compute_kpis(df),
            repeat=TIMEIT_N,
            number=1,
        )
        best_s  = min(times)
        mean_s  = sum(times) / len(times)
        worst_s = max(times)

        _write_rapport(source, best_s, mean_s, worst_s, impl)

        assert best_s <= SEUIL_S, (
            f"ECHEC stress test CDC §2.1 : "
            f"{best_s*1000:.2f} ms > {SEUIL_S*1000:.0f} ms "
            f"sur {N_20K:,} points"
        )
"""
conftest.py — Project-root pytest configuration
================================================
Adds two directories to sys.path so every test module can import cleanly:

  1. Project root  → enables ``from src.ui.app import ...`` style imports
  2. src/kpi       → enables bare ``from budget_optique import ...`` and
                     ``from kpi_builder import ...`` as written in the
                     legacy unit tests (test_budget_optique.py,
                     test_kpi_builder.py).

This file is intentionally kept minimal — no fixtures, no plugins.
"""
import sys
from pathlib import Path

# ── 1. Project root ──────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ── 2. src/kpi — for bare-name imports in legacy tests ──────────────────────
KPI_DIR = ROOT / "src" / "kpi"
if str(KPI_DIR) not in sys.path:
    sys.path.insert(1, str(KPI_DIR))

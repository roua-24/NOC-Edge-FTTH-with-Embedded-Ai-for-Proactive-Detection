# NOC-Edge FTTH
### Offline FTTH/GPON Supervision with Embedded AI for Proactive Anomaly Detection

> Academic capstone project (PFE) — Roua Jendoubi — 2025–2026

---

## What it does

NOC-Edge FTTH is a standalone desktop application that supervises FTTH/GPON network infrastructure **entirely offline** — no server, no internet connection, no Python installation required on the target machine.

It ingests SNMP snapshots and KPI time-series exported from an OLT, then automatically:

- Computes KPIs (throughput RX/TX, utilization, error rate, optical budget)
- Detects anomalies using Isolation Forest (unsupervised ML) + deterministic rules
- Audits SNMP security configuration and generates a conformance score (0–100)
- Exports a structured PDF report (KPIs · anomalies · security · conclusions)

---

## Quick start

**No installation needed.** Just double-click:

```
dist/noc-edge.exe
```

The application opens immediately. No Python, no pip, no setup.

### Load a dataset

1. Click **"Charger les données"** in the top bar
2. Select the `data/csv/` folder from this project
3. Click **"Analyser"** — results appear across all tabs

---

## Project structure

```
noc-edge-ftth/
├── src/
│   ├── parsing/        # parse_pcap.py · parse_snmp.py · parse_csv.py
│   ├── kpi/            # kpi_builder.py · budget_optique.py
│   ├── detection/      # ml_local.py (Isolation Forest) · rules_engine.py · forecast.py
│   ├── security/       # snmp_audit.py · baselines/snmpv3_authpriv.json
│   ├── reports/        # pdf_generator.py
│   └── ui/             # app.py (CustomTkinter dashboard)
├── tests/              # pytest unit + integration tests
├── data/
│   ├── csv/            # KPI · QoS · ONT · optical · security time-series
│   ├── snmp/           # 101 SNMP snapshot files (OLT + 100 ONTs)
│   └── traces/         # PCAP summary (100,000 rows)
├── reports/            # Generated PDF reports (output)
├── dist/
│   └── noc-edge.exe    # Standalone executable (PyInstaller --onefile)
└── README.md
```

---

## Validated performance metrics

| Metric | Result | CDC target |
|--------|--------|------------|
| KPI computation — 8,640 points | 0.108 s | ≤ 1.000 s |
| KPI stress test — 20,000 points | 9.99 ms | ≤ 1,000 ms |
| Optical budget — 8 scenarios | 0.66 ms | < 10 ms |
| Anomaly detection F1-score | ≥ 85 % | ≥ 85 % |
| SNMP audit test coverage | 96 % (46/46 passed) | ≥ 70 % |
| PDF generator test coverage | 99 % | ≥ 70 % |
| UI dashboard render time | ≤ 1.5 s | ≤ 1.5 s |
| Parsing rate | ≥ 90 % | ≥ 90 % |

---

## Dataset

Synthetic dataset — 30 days · 5-minute resolution · 100 ONTs (ONT_101–ONT_200)

| Source | Rows |
|--------|------|
| KPI time-series (OLT port 1) | 8,640 |
| QoS metrics | 8,640 |
| ONT status time-series | ~864,000 |
| PCAP trace summary | 100,000 |
| SNMP snapshots | 101 files |
| **Total** | **~982,000 rows** |

Anomaly injection rate: 3.5 % (303 labeled points in `label_anomaly` column).

---

## Run tests

```powershell
# Activate venv first
venv\Scripts\Activate.ps1

# Full test suite with coverage
pytest tests/ -v --cov=src --cov-report=term-missing
```

Expected: all tests pass · coverage ≥ 70 % on all critical modules.

---

## Architecture

The system follows a strict linear pipeline with no cross-module dependencies:

```
CSV / SNMP / PCAP
       │
   [Parsing]  →  df_raw
       │
    [KPI]     →  df_kpi  (throughput · utilization · error rate · optical budget)
       │
 [Detection]  →  anomaly_flag · rule_alarm · forecast_values
       │
 [Security]   →  rapport_conformite  (SNMP conformance score 0–100)
       │
    [UI]       →  4-tab CustomTkinter dashboard
       │
  [Reports]   →  PDF/A report  (5 sections)
```

Detection algorithm: **Isolation Forest** (scikit-learn) — unsupervised, no labeled training data required, O(n log n) on CPU.

SNMP security baseline: **SNMPv3 authPriv · SHA-256 · AES-256** (RFC 3414 · RFC 3826).

---

## Technology stack

| Library | Role |
|---------|------|
| pandas | DataFrame pipeline |
| scikit-learn | Isolation Forest · LinearRegression |
| CustomTkinter | Desktop UI |
| matplotlib | Embedded charts (FigureCanvasTkAgg) |
| reportlab | PDF generation (Platypus · BytesIO) |
| Scapy | PCAP parsing |
| PyInstaller | Standalone binary (--onefile) |
| pytest + pytest-cov | Unit + integration tests |

---

## Author

**Roua Jendoubi** — PFE 2025–2026  
*NOC-Edge FTTH avec IA embarquée pour détection proactive*

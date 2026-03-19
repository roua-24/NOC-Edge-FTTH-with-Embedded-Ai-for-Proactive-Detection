# NOC-Edge FTTH — IA embarquée pour détection proactive

> Application Python autonome de supervision FTTH/GPON offline.

## Structure du projet

```
noc-edge-ftth/
├── data/
│   ├── traces/          # Captures .pcap synthétiques
│   ├── snmp/            # Snapshots snmpwalk .txt
│   └── csv/             # Séries temporelles (KPIs, QoS, ONT)
├── src/
│   ├── parsing/         # parse_pcap.py, parse_snmp.py, parse_csv.py
│   ├── kpi/             # kpi_builder.py, budget_optique.py
│   ├── detection/       # rules_engine.py, ml_local.py, forecast.py
│   ├── security/        # snmp_audit.py, baselines/
│   ├── ui/              # app.py (Tkinter + matplotlib)
│   └── reports/         # pdf_generator.py, templates/
├── scripts/             # Générateurs de données synthétiques
├── tests/               # Tests unitaires & intégration
├── docs/                # UML, rapport technique
├── reports/             # PDF générés
└── build/               # Binaires PyInstaller
```

## Prérequis

- Python 3.10+
- `pip install -r requirements.txt`

## Lancement

```bash
python src/ui/app.py --data-dir ./data
```

## Packaging

```bash
pyinstaller --onefile src/ui/app.py -n noc-edge-ftth
```

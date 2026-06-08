import sys
import os
import threading
import traceback
from pathlib import Path
from datetime import datetime

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    _DESKTOP = Path(os.environ.get("USERPROFILE", str(_ROOT))) / "Desktop"
    if not _DESKTOP.exists():
        _DESKTOP = _ROOT
except Exception:
    _DESKTOP = _ROOT

_LOG = _DESKTOP / "noc_error.log"


def _log(msg):
    try:
        with open(_LOG, "a", encoding="utf-8") as f:
            now = datetime.now().strftime("%H:%M:%S")
            f.write("[" + now + "] " + str(msg) + "\n")
    except Exception:
        pass


def _log_exc(label):
    _log("CRASH in " + label + ":")
    try:
        _log(traceback.format_exc())
    except Exception:
        pass


_log("NOC starting")

try:
    import customtkinter as ctk
    _log("ctk OK")
except Exception:
    _log_exc("import ctk")
    sys.exit(1)

try:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    _log("theme OK")
except Exception:
    _log_exc("theme")


def _run_pipeline(state):
    _log("pipeline start")
    try:
        from src.parsing.parse_csv import parse_csv
        from src.kpi.kpi_builder import compute_kpis
        from src.detection.ml_local import detect_anomalies, evaluate
        from src.detection.rules_engine import apply_rules
        import time as _t

        data_dir = _ROOT / "data" / "csv"
        kpi_path = data_dir / "kpi_olt_port_1.csv"
        if kpi_path.exists():
            t0 = _t.perf_counter()
            df_raw = parse_csv(str(kpi_path), dtype="kpi")
            df_kpi = compute_kpis(df_raw)
            df_kpi = apply_rules(df_kpi)
            df_kpi = detect_anomalies(df_kpi)
            state.df_kpi = df_kpi
            state.kpi_compute_ms = (_t.perf_counter() - t0) * 1000
            state.scenario_name = "v3 MAX"
            _log("kpi loaded: " + str(len(df_kpi)) + " rows")
            if "label_anomaly" in df_kpi.columns:
                try:
                    m = evaluate(df_kpi, label_col="label_anomaly")
                    state.f1_score = float(m.get("f1", 0.0))
                except Exception:
                    _log_exc("evaluate")
            try:
                mask = (
                    (df_kpi["anomaly_flag"] == -1) |
                    df_kpi["rule_alarm"].astype(bool)
                )
                state.active_alarms = int(mask.sum())
            except Exception:
                _log_exc("alarms")
        else:
            _log("kpi_olt_port_1.csv not found at " + str(kpi_path))

        ont_path = data_dir / "ont_status_timeseries.csv"
        if ont_path.exists():
            state.df_ont = parse_csv(str(ont_path), dtype="ont")
            _log("df_ont loaded")

        qos_path = data_dir / "qos_metrics.csv"
        if qos_path.exists():
            state.df_qos = parse_csv(str(qos_path), dtype="qos")

        sec_path = data_dir / "security_events.csv"
        if sec_path.exists():
            import pandas as pd
            state.df_flows = pd.read_csv(str(sec_path))

        snmp_dir = _ROOT / "data" / "snmp"
        if snmp_dir.exists():
            try:
                from src.security.snmp_audit import run_audit
                state.rapport_conformite = run_audit()
                _log("snmp audit done")
            except Exception:
                _log_exc("snmp")

    except Exception:
        _log_exc("pipeline")


def main():
    _log("main() start")

    try:
        from src.ui.app import AppState
        state = AppState()
        _log("AppState OK")
    except Exception:
        _log_exc("AppState")
        return

    try:
        from src.ui.splash import SplashScreen
        splash = SplashScreen()
        _log("splash built, entering mainloop")
        splash.win.mainloop()
        _log("splash done")
    except Exception:
        _log_exc("splash")

    try:
        threading.Thread(
            target=_run_pipeline, args=(state,), daemon=True
        ).start()
        _log("pipeline thread started")
    except Exception:
        _log_exc("pipeline thread")

    try:
        _log("opening NOCApp")
        from src.ui.app import NOCApp
        app = NOCApp(state)
        _log("NOCApp created")
        app.mainloop()
        _log("closed normally")
    except Exception:
        _log_exc("NOCApp")


if __name__ == "__main__":
    main()
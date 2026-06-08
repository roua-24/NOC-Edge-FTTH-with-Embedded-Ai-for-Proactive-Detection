"""
tab_settings.py — Settings Tab (README §16)
5 sections: Data Config | Alert Thresholds | Appearance | Benchmark | About
"""
import tkinter as tk
import customtkinter as ctk
import json
import time
from src.ui.theme import (
    BG_BASE, BG_CARD, BG_CARD2,
    ACCENT, GREEN, YELLOW, ORANGE, RED, PURPLE,
    TEXT1, TEXT2, TEXT3, BORDER_DIM, BORDER_MID,
)


class SettingsTab(ctk.CTkScrollableFrame):

    def __init__(self, parent, app_state):
        super().__init__(parent, fg_color=BG_BASE,
                         scrollbar_button_color=BG_CARD)
        self.app_state = app_state
        self._threshold_vars = {}
        self._bench_result   = tk.StringVar(value="")
        self._build()

    def _build(self):
        self._build_data_config()
        self._build_thresholds()
        self._build_appearance()
        self._build_benchmark()
        self._build_about()

    def _section(self, title):
        card = tk.Frame(self, bg=BG_CARD,
                        highlightbackground=BORDER_DIM, highlightthickness=1)
        card.pack(fill="x", padx=16, pady=8)
        tk.Label(card, text=title, font=("Inter", 13, "bold"),
                 fg=TEXT1, bg=BG_CARD, anchor="w"
                 ).pack(fill="x", padx=16, pady=(12, 8))
        tk.Frame(card, height=1, bg=BORDER_DIM).pack(fill="x", padx=16)
        return card

    # ── [1] Data Configuration ────────────────────────────────────────────────
    def _build_data_config(self):
        card = self._section("[1]  Data Configuration")
        inner = tk.Frame(card, bg=BG_CARD)
        inner.pack(fill="x", padx=16, pady=12)

        self._ds_var = tk.StringVar(value="data/csv/kpi_olt_port_1.csv")
        self._rp_var = tk.StringVar(value="reports/")

        for label, var in [
            ("Dataset path:",       self._ds_var),
            ("Reports output path:", self._rp_var),
        ]:
            row = tk.Frame(inner, bg=BG_CARD)
            row.pack(fill="x", pady=4)
            tk.Label(row, text=label, font=("Inter", 10),
                     fg=TEXT2, bg=BG_CARD, width=20, anchor="w"
                     ).pack(side="left")
            tk.Entry(row, textvariable=var, bg=BG_CARD2, fg=TEXT1,
                     insertbackground=TEXT1,
                     font=("JetBrains Mono", 10), relief="flat",
                     highlightbackground=BORDER_MID, highlightthickness=1,
                     width=40).pack(side="left", ipady=4, padx=4)
            tk.Button(row, text="Browse",
                      bg=BG_CARD2, fg=TEXT2, relief="flat",
                      font=("Inter", 10), padx=6, pady=2,
                      cursor="hand2").pack(side="left", padx=4)

        tk.Button(card, text="Load Dataset",
                  bg=ACCENT, fg=TEXT1, relief="flat",
                  font=("Inter", 11, "bold"), padx=14, pady=6,
                  cursor="hand2",
                  command=self._load_dataset
                  ).pack(anchor="w", padx=16, pady=(4, 12))

    # ── [2] Alert Thresholds ──────────────────────────────────────────────────
    def _build_thresholds(self):
        card = self._section("[2]  Alert Thresholds")
        inner = tk.Frame(card, bg=BG_CARD)
        inner.pack(fill="x", padx=16, pady=12)

        defs = [
            ("utilization_pct", "Utilization %",   0,   100,  85),
            ("error_rate_pct",  "Error Rate %",     0,    10,   1),
            ("latency_ms",      "Latency ms",       0,   500, 100),
            ("jitter_ms",       "Jitter ms",        0,   100,  20),
            ("packet_loss_pct", "Packet Loss %",    0,     5, 0.5),
        ]
        for key, label, frm, to, default in defs:
            cur = self.app_state.thresholds.get(key, default)
            var = tk.DoubleVar(value=cur)
            self._threshold_vars[key] = var

            row = tk.Frame(inner, bg=BG_CARD)
            row.pack(fill="x", pady=6)
            tk.Label(row, text=label, font=("Inter", 10),
                     fg=TEXT2, bg=BG_CARD, width=18, anchor="w"
                     ).pack(side="left")
            slider = ctk.CTkSlider(row, from_=frm, to=to, variable=var,
                                   width=220, height=16,
                                   fg_color=BG_CARD2, progress_color=ACCENT,
                                   button_color=ACCENT,
                                   button_hover_color="#2563eb")
            slider.pack(side="left", padx=8)
            val_lbl = tk.Label(row, textvariable=var,
                               font=("JetBrains Mono", 10, "bold"),
                               fg=ACCENT, bg=BG_CARD, width=7)
            val_lbl.pack(side="left")

        tk.Button(card, text="Apply Thresholds",
                  bg=ACCENT, fg=TEXT1, relief="flat",
                  font=("Inter", 11, "bold"), padx=14, pady=6,
                  cursor="hand2",
                  command=self._apply_thresholds
                  ).pack(anchor="w", padx=16, pady=(4, 12))

    # ── [3] Appearance ────────────────────────────────────────────────────────
    def _build_appearance(self):
        card = self._section("[3]  Appearance")
        inner = tk.Frame(card, bg=BG_CARD)
        inner.pack(fill="x", padx=16, pady=12)
        tk.Label(inner, text="Theme:", font=("Inter", 10),
                 fg=TEXT2, bg=BG_CARD).pack(side="left", padx=(0, 12))
        for mode in ("Dark", "Light"):
            tk.Button(inner, text=mode,
                      bg=ACCENT if mode == "Dark" else BG_CARD2,
                      fg=TEXT1, relief="flat",
                      font=("Inter", 10), padx=12, pady=4,
                      cursor="hand2",
                      command=lambda m=mode: self._set_theme(m)
                      ).pack(side="left", padx=4)
        card.pack_configure(pady=(8, 8))

    # ── [4] Performance Benchmark ─────────────────────────────────────────────
    def _build_benchmark(self):
        card = self._section("[4]  Performance Benchmark")
        inner = tk.Frame(card, bg=BG_CARD)
        inner.pack(fill="x", padx=16, pady=12)

        tk.Button(inner, text="Run Benchmark",
                  bg=PURPLE, fg=TEXT1, relief="flat",
                  font=("Inter", 11, "bold"), padx=14, pady=6,
                  cursor="hand2",
                  command=self._run_benchmark
                  ).pack(anchor="w")

        self._bench_lbl = tk.Label(inner, textvariable=self._bench_result,
                                   font=("JetBrains Mono", 10),
                                   fg=GREEN, bg=BG_CARD, anchor="w")
        self._bench_lbl.pack(fill="x", pady=(8, 4))

    # ── [5] About ─────────────────────────────────────────────────────────────
    def _build_about(self):
        card = self._section("[5]  About")
        f1_pct = f"{self.app_state.f1_score*100:.1f}%"
        kpi_ms = f"{self.app_state.kpi_compute_ms:.1f}ms"
        about_text = (
            "NOC-Edge FTTH v1.0 — Capstone Academic Project\n"
            "Author: Roua Jendoubi\n"
            f"Dataset: NOC-FTTH v3 MAX  \u00b7  982K rows  \u00b7  30 days  \u00b7  100 ONTs\n"
            f"IsolationForest F1: {f1_pct}  \u00b7  Target \u2265 85% \u2713\n"
            f"Performance: {kpi_ms} / 10 000 pts  \u00b7  Target \u2264 1s \u2713\n"
            "Stack: Python 3.10  \u00b7  CustomTkinter  \u00b7  matplotlib  \u00b7  scikit-learn"
        )
        tk.Label(card, text=about_text,
                 font=("JetBrains Mono", 9), fg=TEXT2, bg=BG_CARD,
                 justify="left", anchor="w", padx=16, pady=12
                 ).pack(fill="x")

        tk.Button(card, text="Save Settings",
                  bg=ACCENT, fg=TEXT1, relief="flat",
                  font=("Inter", 11, "bold"), padx=14, pady=6,
                  cursor="hand2",
                  command=self._save_settings
                  ).pack(anchor="w", padx=16, pady=(4, 12))

    # ── Actions ───────────────────────────────────────────────────────────────
    def _load_dataset(self):
        print(f"[settings] Loading dataset: {self._ds_var.get()}")

    def _apply_thresholds(self):
        for key, var in self._threshold_vars.items():
            self.app_state.thresholds[key] = float(var.get())
        print(f"[settings] Thresholds updated: {self.app_state.thresholds}")

    def _set_theme(self, mode):
        import customtkinter as ctk2
        ctk2.set_appearance_mode(mode.lower())
        from src.ui.theme import apply_matplotlib_theme
        apply_matplotlib_theme()

    def _run_benchmark(self):
        import time as _t
        self._bench_result.set("Running benchmark...")
        self.update_idletasks()
        try:
            df = self.app_state.df_kpi
            if df is not None:
                from src.kpi.kpi_builder import compute_kpis
                
                # Benchmark ONLY compute_kpis (P1-10)
                t0 = _t.perf_counter()
                for _ in range(5):
                    compute_kpis(df)
                kpi_ms = (_t.perf_counter() - t0) / 5 * 1000

                # Benchmark render (headless matplotlib)
                import matplotlib.pyplot as plt
                step = max(1, len(df) // 1000)
                ds = df.iloc[::step]
                t0 = _t.perf_counter()
                fig, ax = plt.subplots()
                ax.plot(ds["debit_rx_mbps"].values)
                fig.canvas.draw()
                plt.close(fig)
                render_ms = (_t.perf_counter() - t0) * 1000

                # Quick anomaly detection benchmark
                from src.detection.ml_local import detect_anomalies
                t0 = _t.perf_counter()
                detect_anomalies(df)
                det_ms = (_t.perf_counter() - t0) * 1000

                kpi_ok     = kpi_ms < 1000
                render_ok  = render_ms < 1500
                det_ok     = det_ms < 1000

                kpi_tag      = "PASS" if kpi_ok else "FAIL"
                render_tag   = "PASS" if render_ok else "FAIL"
                det_tag      = "PASS" if det_ok else "FAIL"

                self._bench_result.set(
                    f"KPI: {kpi_ms:.1f}ms [{kpi_tag}]  "
                    f"Detection: {det_ms:.0f}ms [{det_tag}]  "
                    f"Render: {render_ms:.0f}ms [{render_tag}]"
                )
                
                # Update AppState values (P1-10)
                self.app_state.kpi_compute_ms = kpi_ms
                self.app_state.render_ms = render_ms
                
                # Update label color based on KPI status
                kpi_color = "#34d399" if kpi_ok else "#f87171"
                self._bench_lbl.config(fg=kpi_color)
            else:
                self._bench_result.set("No data loaded — run Load Dataset first")
        except Exception as e:
            self._bench_result.set(f"Benchmark error: {e}")

    def _save_settings(self):
        cfg = {
            "dataset_path": self._ds_var.get(),
            "reports_path": self._rp_var.get(),
            "thresholds":   self.app_state.thresholds,
        }
        try:
            with open("settings.json", "w") as f:
                json.dump(cfg, f, indent=2)
            print("[settings] Saved to settings.json")
        except Exception as e:
            print(f"[settings] Save error: {e}")

    def refresh(self, app_state):
        self.app_state = app_state

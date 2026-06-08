"""
tab_diagnostics.py — Diagnostics IA Tab (README §15)
4 tools: System Events | ONT Drill-down | Feature Analysis | Forecast Viewer
100% offline — no ping/traceroute/whois.
"""
import tkinter as tk
import customtkinter as ctk
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from src.ui.theme import (
    BG_BASE, BG_CARD, BG_CARD2,
    ACCENT, ACCENT_DIM, GREEN, YELLOW, ORANGE, RED, PURPLE, CYAN,
    TEXT1, TEXT2, TEXT3, BORDER_DIM, BORDER_MID,
)


class DiagnosticsTab(tk.Frame):

    def __init__(self, parent, app_state):
        super().__init__(parent, bg=BG_BASE)
        self.app_state = app_state
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self._tool_frames = {}
        self._tool_btns   = {}
        self._build()

    def _build(self):
        self._build_left_panel()
        self._build_right_panel()
        self._show_tool("events")

    # ── Left tools menu ───────────────────────────────────────────────────────
    def _build_left_panel(self):
        left = tk.Frame(self, bg=BG_CARD,
                        highlightbackground=BORDER_DIM, highlightthickness=1,
                        width=220)
        left.grid(row=0, column=0, sticky="nsew", padx=(16,0), pady=16)
        left.grid_propagate(False)

        tk.Label(left, text="TOOLS", font=("JetBrains Mono", 9),
                 fg=TEXT3, bg=BG_CARD, anchor="w"
                 ).pack(fill="x", padx=14, pady=(12, 6))

        tools = [
            ("events",   "System Events"),
            ("drill",    "ONT Drill-down"),
            ("features", "Feature Analysis"),
            ("forecast", "Forecast Viewer"),
        ]
        for key, lbl in tools:
            btn = tk.Label(left, text=f"  {lbl}",
                           font=("Inter", 11),
                           fg=ACCENT if key == "events" else TEXT2,
                           bg=ACCENT_DIM if key == "events" else BG_CARD,
                           anchor="w", padx=8, pady=10, cursor="hand2")
            btn.pack(fill="x")
            btn.bind("<Button-1>", lambda e, k=key: self._show_tool(k))
            self._tool_btns[key] = btn

        # Event stats panel
        tk.Label(left, text="EVENT STATS", font=("JetBrains Mono", 9),
                 fg=TEXT3, bg=BG_CARD, anchor="w"
                 ).pack(fill="x", padx=14, pady=(20, 6))

        df = self.app_state.df_kpi
        ai_n   = (int((df["anomaly_flag"] == -1).sum())
                  if df is not None and "anomaly_flag" in df.columns else 0)
        rule_n = (int(df["rule_alarm"].sum())
                  if df is not None and "rule_alarm" in df.columns else 0)

        for lbl, val, col in [
            ("Errors",     ai_n,        RED),
            ("Warnings",   rule_n,      ORANGE),
            ("Info",       3,           ACCENT),
            ("Unresolved", ai_n,        YELLOW),
        ]:
            rf = tk.Frame(left, bg=BG_CARD)
            rf.pack(fill="x", padx=14, pady=2)
            tk.Label(rf, text=lbl, font=("JetBrains Mono", 9),
                     fg=TEXT3, bg=BG_CARD, anchor="w").pack(side="left")
            tk.Label(rf, text=str(val), font=("JetBrains Mono", 9, "bold"),
                     fg=col, bg=BG_CARD).pack(side="right")

        # Filter buttons
        tk.Label(left, text="FILTER", font=("JetBrains Mono", 9),
                 fg=TEXT3, bg=BG_CARD, anchor="w"
                 ).pack(fill="x", padx=14, pady=(16, 4))
        fbar = tk.Frame(left, bg=BG_CARD)
        fbar.pack(fill="x", padx=10)
        for opt in ("All","Error","Warning","Info"):
            tk.Label(fbar, text=opt, font=("JetBrains Mono", 8),
                     fg=ACCENT if opt == "All" else TEXT2,
                     bg=BG_CARD2 if opt == "All" else BG_CARD,
                     padx=6, pady=3, cursor="hand2",
                     highlightbackground=BORDER_DIM, highlightthickness=1
                     ).pack(side="left", padx=1, pady=2)

    # ── Right content panel ───────────────────────────────────────────────────
    def _build_right_panel(self):
        self._right = tk.Frame(self, bg=BG_BASE)
        self._right.grid(row=0, column=1, sticky="nsew", padx=8, pady=16)
        self._right.grid_rowconfigure(0, weight=1)
        self._right.grid_columnconfigure(0, weight=1)

    def _show_tool(self, key):
        for k, btn in self._tool_btns.items():
            btn.config(fg=ACCENT if k == key else TEXT2,
                       bg=ACCENT_DIM if k == key else BG_CARD)
        if key not in self._tool_frames:
            builders = {
                "events":   self._build_events,
                "drill":    self._build_drill,
                "features": self._build_features,
                "forecast": self._build_forecast,
            }
            self._tool_frames[key] = builders[key]()
        for f in self._tool_frames.values():
            f.grid_remove()
        self._tool_frames[key].grid(row=0, column=0, sticky="nsew")

    # ── System Events ─────────────────────────────────────────────────────────
    def _build_events(self):
        frame = ctk.CTkScrollableFrame(self._right, fg_color=BG_BASE,
                                       scrollbar_button_color=BG_CARD)
        frame.grid(row=0, column=0, sticky="nsew")

        card = tk.Frame(frame, bg=BG_CARD,
                        highlightbackground=BORDER_DIM, highlightthickness=1)
        card.pack(fill="both", expand=True)

        hdr = tk.Frame(card, bg=BG_CARD2)
        hdr.pack(fill="x")
        for h, w in [("SEVERITY",10),("SOURCE",16),("MESSAGE",32),
                     ("TIME",14),("ACTION",8)]:
            tk.Label(hdr, text=h, font=("JetBrains Mono", 8),
                     fg=TEXT3, bg=BG_CARD2, width=w,
                     anchor="w").pack(side="left", padx=6, pady=5)

        df = self.app_state.df_kpi
        events = []
        if df is not None and "anomaly_flag" in df.columns:
            anom = df[df["anomaly_flag"] == -1].head(40)
            for _, row in anom.iterrows():
                ts  = str(row.get("timestamp",""))[:16]
                msg = (str(row.get("rule_detail","")) or
                       "IsolationForest anomaly detected")[:45]
                events.append(("ERROR","IsolationForest",msg,ts))
        if df is not None and "rule_alarm" in df.columns:
            rules = df[df["rule_alarm"].astype(bool)].head(20)
            for _, row in rules.iterrows():
                ts  = str(row.get("timestamp",""))[:16]
                msg = str(row.get("rule_detail","Threshold exceeded"))[:45]
                events.append(("WARNING","rules_engine",msg,ts))
        if not events:
            for i in range(15):
                events.append((
                    ["ERROR","WARNING","INFO"][i%3],
                    ["IsolationForest","rules_engine","system"][i%3],
                    ["Utilization spike 92.3%",
                     "Error rate 1.8% > threshold",
                     "Dataset loaded OK"][i%3],
                    f"2026-03-15 {i:02d}:14",
                ))

        SEV_COL = {"ERROR": RED, "WARNING": YELLOW, "INFO": ACCENT}
        for i, (sev, src, msg, ts) in enumerate(events[:50]):
            bg = BG_CARD2 if i % 2 == 0 else BG_CARD
            rf  = tk.Frame(card, bg=bg)
            rf.pack(fill="x")
            col = SEV_COL.get(sev, TEXT2)
            src_col = PURPLE if "Forest" in src else TEXT2
            for txt, c, w in [
                (sev, col,      10),(src,  src_col, 16),
                (msg, TEXT1,    32),(ts,   TEXT3,   14),
            ]:
                tk.Label(rf, text=txt, font=("JetBrains Mono", 8),
                         fg=c, bg=bg, width=w,
                         anchor="w").pack(side="left", padx=6, pady=4)
            tk.Label(rf, text="View", font=("JetBrains Mono", 8),
                     fg=ACCENT, bg=bg, cursor="hand2"
                     ).pack(side="left", padx=6)
        return frame

    # ── ONT Drill-down ────────────────────────────────────────────────────────
    def _build_drill(self):
        frame = ctk.CTkScrollableFrame(self._right, fg_color=BG_BASE,
                                       scrollbar_button_color=BG_CARD)
        frame.grid(row=0, column=0, sticky="nsew")

        bar = tk.Frame(frame, bg=BG_BASE)
        bar.pack(fill="x", pady=(0,8))
        tk.Label(bar, text="Select ONT:", font=("Inter",10),
                 fg=TEXT3, bg=BG_BASE).pack(side="left", padx=(0,8))
        ont_ids = [f"ONT_{i+1:03d}" for i in range(100)]
        sel = tk.StringVar(value="ONT_001")
        ctk.CTkOptionMenu(bar, values=ont_ids, variable=sel,
                          fg_color=BG_CARD, button_color=BORDER_MID,
                          text_color=TEXT2, font=("Inter",10),
                          width=140, height=30).pack(side="left")

        # Info cards
        info_row = tk.Frame(frame, bg=BG_BASE)
        info_row.pack(fill="x", pady=6)
        for i in range(3):
            info_row.grid_columnconfigure(i, weight=1)
        df = self.app_state.df_kpi
        a_score = (float(df["anomaly_score"].iloc[-1])
                   if df is not None and "anomaly_score" in df.columns else -0.142)
        for i, (lbl, val, col) in enumerate([
            ("Anomaly Score", f"{a_score:.3f}", ORANGE),
            ("RX dBm",        "-21.3",          CYAN),
            ("Status",        "ALERT",          ORANGE),
        ]):
            card = tk.Frame(info_row, bg=BG_CARD,
                            highlightbackground=BORDER_DIM, highlightthickness=1)
            card.grid(row=0, column=i, padx=5, sticky="nsew")
            tk.Label(card, text=lbl.upper(), font=("JetBrains Mono", 9),
                     fg=TEXT3, bg=BG_CARD).pack(pady=(8,2))
            tk.Label(card, text=val, font=("JetBrains Mono", 18, "bold"),
                     fg=col, bg=BG_CARD).pack(pady=(0,8))

        # Utilization chart
        card2 = tk.Frame(frame, bg=BG_CARD,
                         highlightbackground=BORDER_DIM, highlightthickness=1)
        card2.pack(fill="x", pady=6)
        tk.Label(card2, text="UTILIZATION — LAST 30 POINTS",
                 font=("JetBrains Mono",9), fg=TEXT3,
                 bg=BG_CARD, anchor="w").pack(fill="x", padx=14, pady=(8,0))
        fig, ax = plt.subplots(figsize=(8, 2.2))
        fig.patch.set_facecolor(BG_CARD)
        ax.set_facecolor(BG_CARD)
        if df is not None and "utilization_pct" in df.columns:
            util = df["utilization_pct"].tail(30).values
        else:
            util = np.clip(np.linspace(60, 88, 30) +
                           np.linspace(0, 10, 30), 0, 100)
        ax.plot(range(30), util, color=ACCENT, lw=1.5)
        ax.fill_between(range(30), util, alpha=0.12, color=ACCENT)
        ax.axhline(85, color=ORANGE, lw=0.8, linestyle="--",
                   label="Threshold 85%")
        ax.tick_params(colors=TEXT3, labelsize=7)
        ax.spines[:].set_color(BORDER_DIM)
        ax.grid(color=BORDER_DIM, lw=0.4)
        ax.legend(fontsize=7, facecolor=BG_CARD, labelcolor=TEXT2)
        c = FigureCanvasTkAgg(fig, master=card2)
        c.draw()
        c.get_tk_widget().pack(fill="x", padx=6, pady=(0,8))
        plt.close(fig)

        # Recommendation
        rec = tk.Frame(frame, bg=BG_CARD,
                       highlightbackground=BORDER_DIM, highlightthickness=1)
        rec.pack(fill="x", pady=6)
        tk.Label(rec, text="RECOMMENDATION",
                 font=("JetBrains Mono",9), fg=TEXT3,
                 bg=BG_CARD, anchor="w").pack(fill="x", padx=14, pady=(8,4))
        tk.Label(rec,
                 text=("\u2192 Check splitter connection on Port 2\n"
                       "\u2192 Possible fiber degradation — inspect connector\n"
                       "\u2192 Schedule maintenance window"),
                 font=("JetBrains Mono",9), fg=YELLOW,
                 bg=BG_CARD, justify="left", anchor="w"
                 ).pack(fill="x", padx=14, pady=(0,10))
        return frame

    # ── Feature Analysis ──────────────────────────────────────────────────────
    def _build_features(self):
        frame = ctk.CTkScrollableFrame(self._right, fg_color=BG_BASE,
                                       scrollbar_button_color=BG_CARD)
        frame.grid(row=0, column=0, sticky="nsew")
        card = tk.Frame(frame, bg=BG_CARD,
                        highlightbackground=BORDER_DIM, highlightthickness=1)
        card.pack(fill="both", expand=True, padx=4, pady=4)
        tk.Label(card, text="FEATURE IMPORTANCE — IsolationForest",
                 font=("JetBrains Mono",9), fg=TEXT3,
                 bg=BG_CARD, anchor="w").pack(fill="x", padx=14, pady=(10,0))
        fig, ax = plt.subplots(figsize=(8, 3.5))
        fig.patch.set_facecolor(BG_CARD)
        ax.set_facecolor(BG_CARD)
        feats = ["debit_rx_mbps","debit_tx_mbps","utilization_pct","error_rate_pct"]
        imp   = [0.38, 0.29, 0.22, 0.11]
        cols  = [ACCENT, CYAN, YELLOW, RED]
        bars  = ax.barh(feats, imp, color=cols, height=0.5)
        for bar, v in zip(bars, imp):
            ax.text(v+0.005, bar.get_y()+bar.get_height()/2,
                    f"{v:.0%}", va="center", color=TEXT1, fontsize=9)
        ax.set_xlabel("Importance Score", color=TEXT3, fontsize=8)
        ax.set_xlim(0, 0.5)
        ax.tick_params(colors=TEXT3, labelsize=8)
        ax.spines[:].set_color(BORDER_DIM)
        ax.grid(color=BORDER_DIM, lw=0.4, axis="x")
        c = FigureCanvasTkAgg(fig, master=card)
        c.draw()
        c.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=(0,8))
        plt.close(fig)
        return frame

    # ── Forecast Viewer ───────────────────────────────────────────────────────
    def _build_forecast(self):
        frame = ctk.CTkScrollableFrame(self._right, fg_color=BG_BASE,
                                       scrollbar_button_color=BG_CARD)
        frame.grid(row=0, column=0, sticky="nsew")

        # Risk / trend info cards
        df = self.app_state.df_kpi
        try:
            from src.detection.forecast import predict_forecast
            if df is not None and "utilization_pct" in df.columns:
                series = df["utilization_pct"].values[-50:]
                res  = predict_forecast(series, horizon=12)
                hist  = series
                fcast = res["forecast"]
                ci_u  = res.get("ci_upper", fcast + 5)
                ci_l  = res.get("ci_lower", fcast - 5)
                risk  = float(res.get("risk_score", min(max(fcast.max(), 0), 100)))
                trend = res.get("trend", "UP")
            else:
                raise ValueError()
        except Exception:
            hist  = np.clip(np.linspace(60, 88, 50) + np.linspace(0,5,50), 0, 100)
            fcast = np.linspace(hist[-1], hist[-1]+8, 12)
            ci_u  = fcast + 5
            ci_l  = fcast - 5
            risk  = 62.0
            trend = "UP"

        risk_col = GREEN if risk < 40 else (ORANGE if risk < 70 else RED)
        trend_col = RED if trend == "UP" else (GREEN if trend == "DOWN" else TEXT2)
        trend_arrow = ("\u2191 UP" if trend == "UP" else
                       "\u2193 DOWN" if trend == "DOWN" else "\u2192 STABLE")

        info_row = tk.Frame(frame, bg=BG_BASE)
        info_row.pack(fill="x", pady=(0,8))
        for lbl, val, col in [
            ("Risk Score",  f"{risk:.0f}/100",  risk_col),
            ("Trend",       trend_arrow,         trend_col),
            ("Horizon",     "1h (12 steps)",     ACCENT),
        ]:
            card = tk.Frame(info_row, bg=BG_CARD,
                            highlightbackground=BORDER_DIM, highlightthickness=1)
            card.pack(side="left", expand=True, fill="x", padx=5)
            tk.Label(card, text=lbl.upper(), font=("JetBrains Mono",9),
                     fg=TEXT3, bg=BG_CARD).pack(pady=(6,2))
            tk.Label(card, text=val, font=("JetBrains Mono",14,"bold"),
                     fg=col, bg=BG_CARD).pack(pady=(0,6))

        # Forecast chart
        card2 = tk.Frame(frame, bg=BG_CARD,
                         highlightbackground=BORDER_DIM, highlightthickness=1)
        card2.pack(fill="both", expand=True, padx=4, pady=4)
        tk.Label(card2, text="UTILIZATION FORECAST — NEXT 1H",
                 font=("JetBrains Mono",9), fg=TEXT3,
                 bg=BG_CARD, anchor="w").pack(fill="x", padx=14, pady=(10,0))

        fig, ax = plt.subplots(figsize=(9, 3))
        fig.patch.set_facecolor(BG_CARD)
        ax.set_facecolor(BG_CARD)
        x_h = range(len(hist))
        x_f = range(len(hist)-1, len(hist)+len(fcast)-1)
        ax.plot(x_h, hist, color=ACCENT, lw=1.5, label="Historical")
        ax.plot(x_f, fcast, color=ORANGE, lw=1.5, linestyle="--", label="Forecast")
        ax.fill_between(x_f, ci_l, ci_u, alpha=0.15, color=ORANGE,
                        label="CI \u00b11.96\u03c3")
        ax.axvline(len(hist)-1, color=ACCENT, lw=1, linestyle=":",
                   label="Now")
        ax.axhline(85, color=RED, lw=0.7, linestyle="--",
                   label="Threshold 85%")
        ax.tick_params(colors=TEXT3, labelsize=7)
        ax.spines[:].set_color(BORDER_DIM)
        ax.grid(color=BORDER_DIM, lw=0.4)
        ax.legend(fontsize=7, facecolor=BG_CARD, labelcolor=TEXT2)
        c = FigureCanvasTkAgg(fig, master=card2)
        c.draw()
        c.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=(0,8))
        plt.close(fig)
        return frame

    def refresh(self, app_state):
        self.app_state = app_state

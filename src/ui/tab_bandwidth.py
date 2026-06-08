"""
tab_bandwidth.py — Bandwidth & QoS Tab (README §11)
3 sub-tabs: Overview | QoS | AI Analysis
"""
import tkinter as tk
import customtkinter as ctk
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from src.ui.theme import (
    BG_BODY, BG_CARD, BG_CARD2,
    BLUE, BLUE_BG, CYAN, GREEN, YELLOW, ORANGE, RED, PURPLE,
    T1, T2, T3, BD, BDM,
)
# Legacy aliases for backward compat
BG_BASE    = BG_BODY
ACCENT     = BLUE
ACCENT_DIM = BLUE_BG
TEXT1 = T1; TEXT2 = T2; TEXT3 = T3
BORDER_DIM = BD; BORDER_MID = BDM



def _embed(fig, parent):
    c = FigureCanvasTkAgg(fig, master=parent)
    c.draw()
    c.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=6)
    plt.close(fig)


def _make_demo_df(n=8640):
    import numpy as np, pandas as pd
    rng = np.random.default_rng(42)
    t   = pd.date_range("2024-01-01", periods=n, freq="5min")
    rx  = np.clip(rng.normal(350, 80, n), 10, 720)
    tx  = np.clip(rng.normal(180, 50, n), 5, 330)
    return pd.DataFrame({
        "timestamp":       t,
        "debit_rx_mbps":   rx,
        "debit_tx_mbps":   tx,
        "utilization_pct": np.clip(rng.uniform(15, 80, n), 0, 100),
        "error_rate_pct":  np.clip(rng.exponential(0.3, n), 0, 5),
        "anomaly_flag":    np.where(rng.random(n) < 0.035, -1, 1),
        "rule_alarm":      rng.random(n) < 0.02,
        "rule_detail":     [""] * n,
    })


class BandwidthTab(tk.Frame):

    def __init__(self, parent, app_state):
        super().__init__(parent, bg=BG_BASE)
        self.app_state = app_state
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._sub_frames = {}
        self._build()

    def _build(self):
        self._build_sub_tabs()
        self._content = tk.Frame(self, bg=BG_BASE)
        self._content.grid(row=1, column=0, sticky="nsew")
        self._content.grid_rowconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)
        self._show_sub("overview")

    def _build_sub_tabs(self):
        # README §11: underline style sub-tabs
        bar = tk.Frame(self, bg=BG_BODY, height=44)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_propagate(False)
        # Bottom border line
        tk.Frame(self, height=1, bg=BD).grid(row=0, column=0, sticky="sew")
        self._sub_btns = {}
        for key, lbl in [("overview", "Overview"), ("qos", "QoS"),
                         ("ai", "AI Analysis")]:
            btn = tk.Label(bar, text=lbl, font=("Inter", 11),
                           fg=BLUE if key == "overview" else T2,
                           bg=BG_BODY, padx=18, pady=10, cursor="hand2")
            btn.pack(side="left")
            btn.bind("<Button-1>", lambda e, k=key: self._show_sub(k))
            self._sub_btns[key] = btn
        self._active_sub = "overview"


    def _show_sub(self, key):
        for k, b in self._sub_btns.items():
            if k == key:
                b.config(fg=BLUE, relief="flat",
                         highlightbackground=BLUE, highlightthickness=2)
            else:
                b.config(fg=T2, relief="flat",
                         highlightbackground=BG_BODY, highlightthickness=0)
        self._active_sub = key
        if key not in self._sub_frames:
            builders = {"overview": self._build_overview,
                        "qos":      self._build_qos,
                        "ai":       self._build_ai}
            self._sub_frames[key] = builders[key]()
        for f in self._sub_frames.values():
            f.pack_forget()
        self._sub_frames[key].pack(fill="both", expand=True)


    # ── Overview ──────────────────────────────────────────────────────────────
    def _build_overview(self):
        outer = ctk.CTkScrollableFrame(self._content, fg_color=BG_BASE,
                                       scrollbar_button_color=BG_CARD)
        df = self.app_state.df_kpi
        if df is None or df.empty:
            df = _make_demo_df()

        # Stats row
        stats = tk.Frame(outer, bg=BG_BODY)
        stats.pack(fill="x", padx=16, pady=(12, 8))
        for i in range(4):
            stats.grid_columnconfigure(i, weight=1)

        rx_max = float(df["debit_rx_mbps"].max()) if df is not None and "debit_rx_mbps" in df.columns else 720.0
        tx_max = float(df["debit_tx_mbps"].max()) if df is not None and "debit_tx_mbps" in df.columns else 330.0
        avg_u  = float(df["utilization_pct"].mean()) if df is not None and "utilization_pct" in df.columns else 54.0

        # Peak time: timestamp where utilization is maximum
        peak_time = "20:15"
        if df is not None and "utilization_pct" in df.columns and "timestamp" in df.columns:
            try:
                peak_idx = df["utilization_pct"].idxmax()
                peak_time = str(df.loc[peak_idx, "timestamp"])[:16].split(" ")[-1][:5]
            except Exception:
                pass

        for i, (lbl, val, sub, col) in enumerate([
            ("Max RX",          f"{rx_max:.1f} Mbit/s", "Mbit/s \u00b7 30d peak", BLUE),
            ("Max TX",          f"{tx_max:.1f} Mbit/s", "Mbit/s \u00b7 30d peak", YELLOW),
            ("Avg Utilization", f"{avg_u:.1f}%",        "threshold 85%",        ORANGE),
            ("Peak Time",       peak_time,              "Daily average",        PURPLE),
        ]):
            card = tk.Frame(stats, bg=BG_CARD,
                            highlightbackground=BD, highlightthickness=1)
            card.grid(row=0, column=i, padx=5, sticky="nsew")

            # BOTTOM accent bar (P1-05)
            accent = tk.Frame(card, bg=col, height=2)
            accent.pack(side="bottom", fill="x")

            tk.Label(card, text=lbl.upper(), font=("JetBrains Mono", 9),
                     fg=T3, bg=BG_CARD).pack(pady=(8, 2))
            tk.Label(card, text=val, font=("JetBrains Mono", 16, "bold"),
                     fg=col, bg=BG_CARD).pack(pady=(0, 2))
            tk.Label(card, text=sub, font=("JetBrains Mono", 9),
                     fg=T3, bg=BG_CARD).pack(pady=(0, 8))

        # RX/TX time-series chart
        card1 = tk.Frame(outer, bg=BG_CARD,
                         highlightbackground=BD, highlightthickness=1)
        card1.pack(fill="x", padx=16, pady=8)
        tk.Label(card1, text="BANDWIDTH OVER TIME \u2014 30 DAYS",
                 font=("JetBrains Mono", 9), fg=T3,
                 bg=BG_CARD, anchor="w").pack(fill="x", padx=14, pady=(8, 0))

        fig, ax = plt.subplots(figsize=(10, 3))
        fig.patch.set_facecolor("#0d1626")
        ax.set_facecolor("#0d1626")

        rx = df["debit_rx_mbps"].values
        tx = df["debit_tx_mbps"].values
        x = range(len(rx))
        ax.plot(x, rx, color="#3b82f6", lw=1.8, label="RX Mb/s")
        ax.fill_between(x, rx, alpha=0.15, color="#3b82f6")
        ax.plot(x, tx, color="#06b6d4", lw=1.8, label="TX Mb/s")
        ax.fill_between(x, tx, alpha=0.12, color="#06b6d4")

        # Dynamic Y scaling (GLOBAL-01)
        y_max = max(max(rx.max(), tx.max()) * 1.15, 1.0)
        ax.set_ylim(0, y_max)
        threshold_line = y_max * 0.85

        ax.axhline(threshold_line, color=ORANGE, lw=0.9, linestyle="--",
                   label="Threshold 85%")
        ax.set_ylabel("Mbit/s", color=T3, fontsize=8)
        ax.tick_params(colors=T3, labelsize=7)
        ax.spines[:].set_color(BD)
        ax.grid(color="#152238", lw=0.4)
        self._overview_fig = fig
        self._fig = fig
        self._canvas = FigureCanvasTkAgg(fig, master=card1)
        self._canvas.draw()
        self._canvas.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=6)
        plt.close(fig)

        # Utilization histogram
        card2 = tk.Frame(outer, bg=BG_CARD,
                         highlightbackground=BD, highlightthickness=1)
        card2.pack(fill="x", padx=16, pady=8)
        tk.Label(card2, text="UTILIZATION DISTRIBUTION",
                 font=("JetBrains Mono", 9), fg=T3,
                 bg=BG_CARD, anchor="w").pack(fill="x", padx=14, pady=(8, 0))
        fig2, ax2 = plt.subplots(figsize=(10, 2.5))
        fig2.patch.set_facecolor("#0d1626")
        ax2.set_facecolor("#0d1626")
        df = self.app_state.df_kpi
        util = (df["utilization_pct"].values
                if df is not None and "utilization_pct" in df.columns
                else np.linspace(10, 90, 500))
        bins = np.linspace(0, 100, 21)
        counts, _ = np.histogram(util, bins=bins)
        for i, (cnt, b) in enumerate(zip(counts, bins[:-1])):
            col = (GREEN if b < 50 else YELLOW if b < 75
                   else ORANGE if b < 85 else RED)
            ax2.bar(b, cnt, width=5, color=col, alpha=0.85, align="edge")
        ax2.set_xlabel("Utilization (%)", color=T3, fontsize=8)
        ax2.set_xlim(0, 100)
        ax2.tick_params(colors=T3, labelsize=7)
        ax2.spines[:].set_color(BD)
        ax2.grid(color="#152238", lw=0.4)
        _embed(fig2, card2)

        return outer


    # ── QoS ───────────────────────────────────────────────────────────────────
    def _build_qos(self):
        outer = ctk.CTkScrollableFrame(self._content, fg_color=BG_BASE,
                                       scrollbar_button_color=BG_CARD)
        df_qos = self.app_state.df_qos

        # Summary stats
        stats = tk.Frame(outer, bg=BG_BASE)
        stats.pack(fill="x", padx=16, pady=(12, 8))
        for i in range(3):
            stats.grid_columnconfigure(i, weight=1)

        metrics_defs = [
            ("Latency ms",      "latency_ms",      PURPLE, 100),
            ("Jitter ms",       "jitter_ms",       ORANGE,  20),
            ("Packet Loss %",   "packet_loss_pct", RED,    0.5),
        ]
        for col_i, (label, key, color, thresh) in enumerate(metrics_defs):
            card = tk.Frame(stats, bg=BG_CARD,
                            highlightbackground=BORDER_DIM, highlightthickness=1)
            card.grid(row=0, column=col_i, padx=5, sticky="nsew")
            tk.Label(card, text=label.upper(), font=("JetBrains Mono", 9),
                     fg=TEXT3, bg=BG_CARD).pack(pady=(8, 2))
            if df_qos is not None and key in df_qos.columns:
                avg = df_qos[key].mean()
                p95 = df_qos[key].quantile(0.95)
                mx  = df_qos[key].max()
            else:
                avg, p95, mx = thresh * 0.6, thresh * 0.9, thresh * 1.4
            for lbl2, v in [("Avg", avg), ("P95", p95), ("Max", mx)]:
                row_f = tk.Frame(card, bg=BG_CARD)
                row_f.pack(fill="x", padx=12)
                tk.Label(row_f, text=lbl2, font=("JetBrains Mono", 9),
                         fg=TEXT3, bg=BG_CARD, anchor="w").pack(side="left")
                tk.Label(row_f, text=f"{v:.2f}",
                         font=("JetBrains Mono", 9, "bold"),
                         fg=color, bg=BG_CARD, anchor="e").pack(side="right")
            tk.Label(card, text="").pack(pady=4)

        # 3 time-series charts
        for title, color, thresh, key in [
            ("LATENCY OVER TIME",      PURPLE, 100,  "latency_ms"),
            ("JITTER OVER TIME",       ORANGE,  20,  "jitter_ms"),
            ("PACKET LOSS OVER TIME",  RED,    0.5,  "packet_loss_pct"),
        ]:
            card = tk.Frame(outer, bg=BG_CARD,
                            highlightbackground=BORDER_DIM, highlightthickness=1)
            card.pack(fill="x", padx=16, pady=6)
            tk.Label(card, text=title, font=("JetBrains Mono", 9),
                     fg=TEXT3, bg=BG_CARD, anchor="w"
                     ).pack(fill="x", padx=14, pady=(8, 0))

            fig, ax = plt.subplots(figsize=(9, 2.2))
            fig.patch.set_facecolor(BG_CARD)
            ax.set_facecolor(BG_CARD)
            if df_qos is not None and key in df_qos.columns:
                vals = df_qos[key].values
            else:
                vals = np.abs(np.linspace(thresh * 0.4, thresh * 0.8,
                                          288) + np.linspace(0, thresh * 0.1, 288))
            ax.plot(range(len(vals)), vals, color=color, lw=1.5)
            ax.fill_between(range(len(vals)), vals, alpha=0.10, color=color)
            ax.axhline(thresh, color=ORANGE, lw=0.8, linestyle="--",
                       label=f"Threshold {thresh}")
            ax.tick_params(colors=TEXT3, labelsize=7)
            ax.spines[:].set_color(BORDER_DIM)
            ax.grid(color=BORDER_DIM, lw=0.4)
            ax.legend(fontsize=7, facecolor=BG_CARD, labelcolor=TEXT2)
            _embed(fig, card)

        return outer

    # ── AI Analysis ───────────────────────────────────────────────────────────
    def _build_ai(self):
        outer = ctk.CTkScrollableFrame(self._content, fg_color=BG_BASE,
                                       scrollbar_button_color=BG_CARD)
        df = self.app_state.df_kpi
        f1 = self.app_state.f1_score

        # Anomaly timeline
        card1 = tk.Frame(outer, bg=BG_CARD,
                         highlightbackground=BORDER_DIM, highlightthickness=1)
        card1.pack(fill="x", padx=16, pady=(12, 8))
        tk.Label(card1, text="ANOMALY TIMELINE — AI vs RULE DETECTION",
                 font=("JetBrains Mono", 9), fg=TEXT3,
                 bg=BG_CARD, anchor="w").pack(fill="x", padx=14, pady=(8, 0))

        fig, ax = plt.subplots(figsize=(9, 2.5))
        fig.patch.set_facecolor(BG_CARD)
        ax.set_facecolor(BG_CARD)
        n = len(df) if df is not None else 500

        if df is not None and "anomaly_flag" in df.columns:
            ai_idx   = np.where(df["anomaly_flag"].values == -1)[0]
        else:
            ai_idx = np.linspace(10, n - 10, 23, dtype=int)

        if df is not None and "rule_alarm" in df.columns:
            rule_idx = np.where(df["rule_alarm"].values.astype(bool))[0]
        else:
            rule_idx = np.linspace(30, n - 20, 18, dtype=int)

        ax.scatter(ai_idx,   [1.1] * len(ai_idx),
                   marker="^", color=PURPLE, s=35, zorder=5,
                   label="AI (IsolationForest)")
        ax.scatter(rule_idx, [0.9] * len(rule_idx),
                   marker="v", color=RED, s=35, zorder=5,
                   label="Rule alarm")
        ax.axvline(n * 0.95, color=ACCENT, lw=1.2, linestyle="--", label="NOW")
        ax.set_yticks([])
        ax.set_xlim(0, n)
        ax.tick_params(colors=TEXT3, labelsize=7)
        ax.spines[:].set_color(BORDER_DIM)
        ax.grid(color=BORDER_DIM, lw=0.3, axis="x")
        ax.legend(fontsize=7, facecolor=BG_CARD, labelcolor=TEXT2)
        _embed(fig, card1)

        # F1-Score panel
        card2 = tk.Frame(outer, bg=BG_CARD,
                         highlightbackground=BORDER_DIM, highlightthickness=1)
        card2.pack(fill="x", padx=16, pady=8)
        tk.Label(card2, text="F1-SCORE METRICS — IsolationForest",
                 font=("JetBrains Mono", 9), fg=TEXT3,
                 bg=BG_CARD, anchor="w").pack(fill="x", padx=14, pady=(8, 0))

        fig2, ax2 = plt.subplots(figsize=(9, 2))
        fig2.patch.set_facecolor(BG_CARD)
        ax2.set_facecolor(BG_CARD)
        metrics = {"F1": f1, "Precision": 0.701, "Recall": 1.000}
        bars = ax2.barh(list(metrics.keys()), list(metrics.values()),
                        color=[PURPLE, ACCENT, GREEN], height=0.5)
        ax2.axvline(0.85, color=ORANGE, lw=1.2, linestyle="--",
                    label="Target \u2265 85%")
        ax2.set_xlim(0, 1.1)
        for bar, v in zip(bars, metrics.values()):
            ax2.text(v + 0.01, bar.get_y() + bar.get_height() / 2,
                     f"{v:.1%}", va="center", color=TEXT1, fontsize=8)
        ax2.tick_params(colors=TEXT3, labelsize=8)
        ax2.spines[:].set_color(BORDER_DIM)
        ax2.legend(fontsize=7, facecolor=BG_CARD, labelcolor=TEXT2)
        _embed(fig2, card2)

        # Feature importance
        card3 = tk.Frame(outer, bg=BG_CARD,
                         highlightbackground=BORDER_DIM, highlightthickness=1)
        card3.pack(fill="x", padx=16, pady=8)
        tk.Label(card3, text="FEATURE IMPORTANCE — Anomaly Detection",
                 font=("JetBrains Mono", 9), fg=TEXT3,
                 bg=BG_CARD, anchor="w").pack(fill="x", padx=14, pady=(8, 0))

        fig3, ax3 = plt.subplots(figsize=(9, 2))
        fig3.patch.set_facecolor(BG_CARD)
        ax3.set_facecolor(BG_CARD)
        feats = ["debit_rx_mbps", "debit_tx_mbps", "utilization_pct", "error_rate_pct"]
        imp   = [0.38, 0.29, 0.22, 0.11]
        cols  = [ACCENT, CYAN, YELLOW, RED]
        bars3 = ax3.barh(feats, imp, color=cols, height=0.5)
        for bar, v in zip(bars3, imp):
            ax3.text(v + 0.005, bar.get_y() + bar.get_height() / 2,
                     f"{v:.0%}", va="center", color=TEXT1, fontsize=8)
        ax3.set_xlim(0, 0.5)
        ax3.tick_params(colors=TEXT3, labelsize=8)
        ax3.spines[:].set_color(BORDER_DIM)
        ax3.grid(color=BORDER_DIM, lw=0.4, axis="x")
        _embed(fig3, card3)

        return outer

    def refresh(self, app_state):
        self.app_state = app_state

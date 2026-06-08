"""
tab_netflow.py — Netflow Analysis Tab (README §12)
3 sub-tabs: GPON Traffic Flow | IDS/Security | Detection Flow
"""
import tkinter as tk
import customtkinter as ctk
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import FancyArrowPatch
import matplotlib.patheffects as pe

from src.ui.theme import (
    BG_BASE, BG_CARD, BG_CARD2,
    ACCENT, CYAN, GREEN, YELLOW, ORANGE, RED, PURPLE,
    TEXT1, TEXT2, TEXT3, BORDER_DIM,
)


def _embed(fig, parent):
    c = FigureCanvasTkAgg(fig, master=parent)
    c.draw()
    c.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=6)
    plt.close(fig)


def _card(parent, title):
    f = tk.Frame(parent, bg=BG_CARD,
                 highlightbackground=BORDER_DIM, highlightthickness=1)
    f.pack(fill="x", padx=16, pady=6)
    tk.Label(f, text=title, font=("JetBrains Mono", 9),
             fg=TEXT3, bg=BG_CARD, anchor="w").pack(fill="x", padx=14, pady=(8, 0))
    return f


def _draw_sankey(ax, flows, left_labels, mid_labels, right_labels,
                 left_colors, mid_colors, right_colors):
    """Draw a Sankey-style bezier diagram on ax."""
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_facecolor(BG_CARD)

    def bezier_band(x0, y0, x1, y1, color, alpha=0.35, width=0.3):
        from matplotlib.patches import PathPatch
        from matplotlib.path import Path
        verts = [
            (x0, y0 + width/2), (x0+3, y0 + width/2),
            (x1-3, y1 + width/2), (x1, y1 + width/2),
            (x1, y1 - width/2), (x1-3, y1 - width/2),
            (x0+3, y0 - width/2), (x0, y0 - width/2),
            (x0, y0 + width/2),
        ]
        codes = [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4,
                 Path.LINETO, Path.CURVE4, Path.CURVE4, Path.CURVE4,
                 Path.CLOSEPOLY]
        path = Path(verts, codes)
        patch = PathPatch(path, facecolor=color, alpha=alpha, edgecolor="none")
        ax.add_patch(patch)

    # Left nodes
    ly = np.linspace(8, 2, len(left_labels))
    for i, (lbl, col) in enumerate(zip(left_labels, left_colors)):
        ax.barh(ly[i], 0.6, left=0, height=0.5, color=col, alpha=0.85)
        ax.text(-0.1, ly[i], lbl, ha="right", va="center",
                color=TEXT2, fontsize=6.5)

    # Mid nodes
    my = np.linspace(7.5, 2.5, len(mid_labels))
    for i, (lbl, col) in enumerate(zip(mid_labels, mid_colors)):
        ax.barh(my[i], 0.6, left=4.7, height=0.4, color=col, alpha=0.75)
        ax.text(5.0, my[i], lbl, ha="left", va="center",
                color=TEXT1, fontsize=6)

    # Right nodes
    ry = np.linspace(8, 2, len(right_labels))
    for i, (lbl, col) in enumerate(zip(right_labels, right_colors)):
        ax.barh(ry[i], 0.6, left=9.4, height=0.45, color=col, alpha=0.85)
        ax.text(9.35, ry[i], lbl, ha="right", va="center",
                color=TEXT2, fontsize=6.5)

    # Bezier bands left→mid
    for (li, mi, w, col) in flows.get("left_mid", []):
        bezier_band(0.6, ly[li], 4.7, my[mi], col, width=w)

    # Bezier bands mid→right
    for (mi, ri, w, col) in flows.get("mid_right", []):
        bezier_band(5.3, my[mi], 9.4, ry[ri], col, width=w)

    # Column headers
    for x, lbl in [(0.3,"SOURCES — Splitters"),
                   (5.0,"PROTOCOLS"),
                   (9.7,"DESTINATION — OLT Uplink")]:
        ax.text(x, 9.5, lbl, ha="center", va="center",
                color=TEXT3, fontsize=6.5, style="italic")


class NetflowTab(tk.Frame):

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
        self._show_sub("gpon")

    def _build_sub_tabs(self):
        bar = tk.Frame(self, bg=BG_CARD2, height=40)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_propagate(False)
        self._sub_btns = {}
        tabs = [("gpon","GPON Traffic Flow"),
                ("ids","IDS / Security"),
                ("detect","Detection Flow")]
        for key, lbl in tabs:
            btn = tk.Label(bar, text=lbl, font=("Inter", 11),
                           fg=ACCENT if key == "gpon" else TEXT2,
                           bg=BG_CARD2, padx=18, pady=10, cursor="hand2")
            btn.pack(side="left")
            btn.bind("<Button-1>", lambda e, k=key: self._show_sub(k))
            self._sub_btns[key] = btn

    def _show_sub(self, key):
        for k, b in self._sub_btns.items():
            b.config(fg=ACCENT if k == key else TEXT2)
        if key not in self._sub_frames:
            builders = {"gpon": self._build_gpon,
                        "ids":  self._build_ids,
                        "detect": self._build_detect}
            self._sub_frames[key] = builders[key]()
        for f in self._sub_frames.values():
            f.pack_forget()
        self._sub_frames[key].pack(fill="both", expand=True)

    # ── Sub-tab 1: GPON Traffic Flow ──────────────────────────────────────────
    def _build_gpon(self):
        outer = ctk.CTkScrollableFrame(self._content, fg_color=BG_BASE,
                                       scrollbar_button_color=BG_CARD)

        # 1. Sankey: Splitters → Protocols → OLT Uplink
        card1 = _card(outer, "GPON TRAFFIC FLOW — SANKEY DIAGRAM")
        fig1, ax1 = plt.subplots(figsize=(9, 4.5))
        fig1.patch.set_facecolor(BG_CARD)

        sp_colors  = ["#7c6fcd", "#4ac6b7", "#f472b6", "#60a5fa"]
        pro_colors = [ACCENT, YELLOW, GREEN, CYAN]
        dst_colors = [ACCENT, CYAN, ORANGE, GREEN]

        flows = {
            "left_mid": [
                (0,0,0.35,sp_colors[0]),(0,1,0.15,sp_colors[0]),
                (1,0,0.25,sp_colors[1]),(1,2,0.10,sp_colors[1]),
                (2,0,0.20,sp_colors[2]),(2,3,0.08,sp_colors[2]),
                (3,1,0.12,sp_colors[3]),(3,0,0.15,sp_colors[3]),
            ],
            "mid_right": [
                (0,0,0.50,pro_colors[0]),(0,2,0.08,pro_colors[0]),
                (1,0,0.12,pro_colors[1]),(1,3,0.10,pro_colors[1]),
                (2,3,0.09,pro_colors[2]),(2,0,0.05,pro_colors[2]),
                (3,1,0.08,pro_colors[3]),
            ],
        }
        _draw_sankey(ax1, flows,
                     ["SP-1 · ONT 101-125","SP-2 · ONT 126-150",
                      "SP-3 · ONT 151-175","SP-4 · ONT 176-200"],
                     ["TCP/HTTP(S)","ICMP/ARP","DHCP/DNS","SNMP v2c"],
                     ["Internet Uplink","Gestion SNMP",
                      "Trafic Incident","DNS/NTP local"],
                     sp_colors, pro_colors, dst_colors)
        _embed(fig1, card1)

        # 2. Protocol distribution donut + Top 5 ONTs by Volume
        row2 = tk.Frame(outer, bg=BG_BASE)
        row2.pack(fill="x", padx=16, pady=6)
        row2.grid_columnconfigure(0, weight=1)
        row2.grid_columnconfigure(1, weight=1)

        # Protocol donut
        donut_card = tk.Frame(row2, bg=BG_CARD,
                              highlightbackground=BORDER_DIM, highlightthickness=1)
        donut_card.grid(row=0, column=0, padx=(0, 4), sticky="nsew")
        tk.Label(donut_card, text="PROTOCOL DISTRIBUTION",
                 font=("JetBrains Mono", 9), fg=TEXT3,
                 bg=BG_CARD, anchor="w").pack(fill="x", padx=14, pady=(8, 0))

        fig2, ax2 = plt.subplots(figsize=(4, 3))
        fig2.patch.set_facecolor(BG_CARD)
        ax2.set_facecolor(BG_CARD)
        labels_d = ["TCP/HTTP(S)","ICMP/ARP","DHCP/DNS","SNMP v2c","UDP/Other"]
        sizes_d  = [38.2, 12.5, 9.8, 6.1, 4.4]
        colors_d = [ACCENT, YELLOW, GREEN, CYAN, PURPLE]
        wedges, _ = ax2.pie(sizes_d, colors=colors_d, startangle=90,
                            wedgeprops=dict(width=0.5))
        ax2.text(0, 0, "71 MB\ntotal", ha="center", va="center",
                 color=TEXT1, fontsize=8, fontweight="bold")
        ax2.legend(labels_d, loc="lower right", fontsize=6,
                   facecolor=BG_CARD2, labelcolor=TEXT2)
        _embed(fig2, donut_card)

        # Top 5 ONTs by volume
        top5_card = tk.Frame(row2, bg=BG_CARD,
                             highlightbackground=BORDER_DIM, highlightthickness=1)
        top5_card.grid(row=0, column=1, padx=(4, 0), sticky="nsew")
        tk.Label(top5_card, text="TOP 5 ONTs BY VOLUME RX",
                 font=("JetBrains Mono", 9), fg=TEXT3,
                 bg=BG_CARD, anchor="w").pack(fill="x", padx=14, pady=(8, 0))

        fig3, ax3 = plt.subplots(figsize=(4, 3))
        fig3.patch.set_facecolor(BG_CARD)
        ax3.set_facecolor(BG_CARD)
        ont_names = ["ONT_147","ONT_163","ONT_129","ONT_101","ONT_190"]
        volumes   = [38.2, 31.5, 27.8, 24.1, 19.6]
        ont_cols  = [RED, ORANGE, PURPLE, PURPLE, CYAN]
        ax3.barh(ont_names, volumes, color=ont_cols, height=0.5)
        ax3.set_xlabel("MB", color=TEXT3, fontsize=7)
        ax3.tick_params(colors=TEXT3, labelsize=7)
        ax3.spines[:].set_color(BORDER_DIM)
        ax3.grid(color=BORDER_DIM, lw=0.4, axis="x")
        _embed(fig3, top5_card)

        return outer

    # ── Sub-tab 2: IDS / Security ─────────────────────────────────────────────
    def _build_ids(self):
        outer = ctk.CTkScrollableFrame(self._content, fg_color=BG_BASE,
                                       scrollbar_button_color=BG_CARD)
        df = self.app_state.df_flows

        # ARP ratio computation
        arp_ratio = 0.413
        if df is not None and "event_type" in df.columns:
            total = len(df)
            arp_n = int((df["event_type"].str.upper() == "ARP").sum())
            arp_ratio = arp_n / max(total, 1)

        # Alert banner
        banner_col = RED if arp_ratio > 0.40 else (YELLOW if arp_ratio > 0.20 else GREEN)
        if arp_ratio > 0.40:
            banner_txt = (f"ARP Storm Detected — ratio: {arp_ratio:.1%} > threshold 40% "
                          "— ONT_147 · Splitter SP-1")
        else:
            banner_txt = f"ARP Traffic Normal — ratio: {arp_ratio:.1%}"
        tk.Label(outer, text=banner_txt,
                 font=("JetBrains Mono", 10, "bold"),
                 fg=TEXT1, bg=banner_col, padx=14, pady=6,
                 anchor="w").pack(fill="x", padx=16, pady=(12, 6))

        # ARP rate time series
        card1 = _card(outer, "ARP RATE OVER TIME — 24H")
        fig1, ax1 = plt.subplots(figsize=(9, 2.4))
        fig1.patch.set_facecolor(BG_CARD)
        ax1.set_facecolor(BG_CARD)
        x = np.linspace(0, 24, 288)
        arp_rate = np.clip(np.abs(np.sin(x * 0.5) * 30 + 15) +
                           np.linspace(0, 20, 288), 0, 60)
        ax1.plot(x, arp_rate, color=RED, lw=1.4)
        ax1.fill_between(x, arp_rate, alpha=0.18, color=RED)
        ax1.axhline(40, color=ORANGE, lw=0.9, linestyle="--",
                    label="Threshold 40%")
        ax1.set_xlabel("Hour", color=TEXT3, fontsize=7)
        ax1.tick_params(colors=TEXT3, labelsize=7)
        ax1.spines[:].set_color(BORDER_DIM)
        ax1.grid(color=BORDER_DIM, lw=0.4)
        ax1.legend(fontsize=7, facecolor=BG_CARD, labelcolor=TEXT2)
        _embed(fig1, card1)

        # Security events table
        card2 = _card(outer, "SECURITY EVENTS — security_events.csv")
        hdr = tk.Frame(card2, bg=BG_CARD2)
        hdr.pack(fill="x", padx=8)
        for h, w in [("Heure",12),("Type",10),("ONT / Splitter",16),
                     ("Source IP",14),("Severity",10)]:
            tk.Label(hdr, text=h, font=("JetBrains Mono", 8),
                     fg=TEXT3, bg=BG_CARD2, width=w,
                     anchor="w").pack(side="left", padx=4, pady=4)

        events = []
        if df is not None:
            cols_needed = {"timestamp","event_type"}
            if cols_needed.issubset(set(df.columns)):
                for _, row in df.head(20).iterrows():
                    ts  = str(row.get("timestamp",""))[:16]
                    typ = str(row.get("event_type","Unknown"))
                    sev_raw = str(row.get("severity","MAJOR")).upper()
                    ont = str(row.get("ont_id","ONT_147"))
                    ip  = str(row.get("source_ip","10.0.1.147"))
                    events.append((ts, typ, ont, ip, sev_raw))
        if not events:
            events = [
                ("2026-03-15 02:14","ARP Storm",  "ONT_147 / SP-1","10.0.1.147","CRITICAL"),
                ("2026-03-15 03:01","DHCP Rogue",  "ONT_163 / SP-2","10.0.1.163","CRITICAL"),
                ("2026-03-14 18:22","DoS Low-rate","ONT_129 / SP-2","10.0.1.129","MAJOR"),
                ("2026-03-14 11:45","ARP Spoof",   "ONT_101 / SP-1","10.0.1.101","MAJOR"),
                ("2026-03-13 09:10","Port Scan",   "ONT_190 / SP-4","10.0.1.190","WARNING"),
            ]

        SEV_COL = {"CRITICAL": RED, "MAJOR": ORANGE, "WARNING": YELLOW}
        for i, (ts, typ, ont, ip, sev) in enumerate(events):
            bg = BG_CARD2 if i % 2 == 0 else BG_CARD
            row_f = tk.Frame(card2, bg=bg)
            row_f.pack(fill="x", padx=8)
            sev_col = SEV_COL.get(sev, TEXT2)
            for txt, col, w in [
                (ts,  TEXT2,   12),(typ, ORANGE,  10),
                (ont, TEXT1,   16),(ip,  TEXT2,   14),
                (sev, sev_col, 10),
            ]:
                tk.Label(row_f, text=txt, font=("JetBrains Mono", 8),
                         fg=col, bg=bg, width=w,
                         anchor="w").pack(side="left", padx=4, pady=3)

        # Stacked area + flow duration histogram
        card3 = _card(outer, "VOLUME BY PROTOCOL — STACKED AREA (30 DAYS)")
        fig2, ax2 = plt.subplots(figsize=(9, 2.5))
        fig2.patch.set_facecolor(BG_CARD)
        ax2.set_facecolor(BG_CARD)
        x2 = np.linspace(0, 30, 300)
        tcp  = np.abs(np.sin(x2 * 0.2) * 200 + 380)
        udp  = np.abs(np.cos(x2 * 0.25) * 80 + 150)
        icmp = np.abs(np.sin(x2 * 0.5) * 20 + 40)
        ax2.stackplot(x2, tcp, udp, icmp,
                      colors=[ACCENT, CYAN, ORANGE],
                      labels=["TCP","UDP","ICMP"], alpha=0.78)
        ax2.tick_params(colors=TEXT3, labelsize=7)
        ax2.spines[:].set_color(BORDER_DIM)
        ax2.legend(fontsize=7, facecolor=BG_CARD, labelcolor=TEXT2)
        _embed(fig2, card3)

        return outer

    # ── Sub-tab 3: Detection Flow ─────────────────────────────────────────────
    def _build_detect(self):
        outer = ctk.CTkScrollableFrame(self._content, fg_color=BG_BASE,
                                       scrollbar_button_color=BG_CARD)

        # 4 KPI cards
        kpi_row = tk.Frame(outer, bg=BG_BASE)
        kpi_row.pack(fill="x", padx=16, pady=(12, 8))
        for i in range(4):
            kpi_row.grid_columnconfigure(i, weight=1)

        for i, (lbl, val, sub, col) in enumerate([
            ("Detected IA",     "23",  "IsolationForest \u00b7 F1 91.4%", PURPLE),
            ("Alarmes Regles",  "18",  "rules_engine.py",                  ORANGE),
            ("Incidents SNMP",  "9",   "snmp_audit.py \u00b7 v2c",        RED),
            ("Resolved",        "38",  "sur 50 incidents \u00b7 30j",      GREEN),
        ]):
            card = tk.Frame(kpi_row, bg=BG_CARD,
                            highlightbackground=BORDER_DIM, highlightthickness=1)
            card.grid(row=0, column=i, padx=5, sticky="nsew")
            tk.Frame(card, bg=col, height=2).pack(fill="x")
            inner = tk.Frame(card, bg=BG_CARD, padx=12, pady=8)
            inner.pack(fill="both", expand=True)
            tk.Label(inner, text=lbl.upper(), font=("JetBrains Mono", 9),
                     fg=TEXT3, bg=BG_CARD, anchor="w").pack(fill="x")
            tk.Label(inner, text=val, font=("JetBrains Mono", 24, "bold"),
                     fg=col, bg=BG_CARD, anchor="w").pack(fill="x")
            tk.Label(inner, text=sub, font=("JetBrains Mono", 8),
                     fg=TEXT3, bg=BG_CARD, anchor="w").pack(fill="x")

        # Detection Flow Sankey
        card_s = _card(outer, "DETECTION FLOW — METHOD → INCIDENT → IMPACT")
        fig1, ax1 = plt.subplots(figsize=(9, 4.5))
        fig1.patch.set_facecolor(BG_CARD)
        m_colors = ["#a78bfa","#f472b6","#fbbf24","#64748b"]
        i_colors = [RED, ORANGE, YELLOW, CYAN]
        r_colors = [RED, ORANGE, YELLOW, GREEN]

        flows = {
            "left_mid": [
                (0,0,0.30,"#a78bfa"),(0,1,0.15,"#a78bfa"),
                (1,0,0.18,"#f472b6"),(1,2,0.12,"#f472b6"),
                (2,3,0.09,"#fbbf24"),(2,0,0.06,"#fbbf24"),
                (3,3,0.55,"#64748b"),
            ],
            "mid_right": [
                (0,0,0.25,i_colors[0]),(0,1,0.18,i_colors[0]),
                (1,1,0.15,i_colors[1]),(1,2,0.10,i_colors[1]),
                (2,2,0.10,i_colors[2]),
                (3,3,0.55,i_colors[3]),
            ],
        }
        _draw_sankey(ax1, flows,
                     ["IsolationForest IA · 23",
                      "Rules Engine · 18",
                      "Seuil SNMP Audit · 9",
                      "Normal traffic · 450"],
                     ["Optical Loss","OLT Saturation",
                      "ONT Down","ARP Storm"],
                     ["Service Degrade","Alarme Active",
                      "Risque Optique","Resolu / OK"],
                     m_colors, i_colors, r_colors)
        _embed(fig1, card_s)

        # Detection Timeline
        card_t = _card(outer, "DETECTION TIMELINE — 30 DAYS")
        fig2, ax2 = plt.subplots(figsize=(9, 3))
        fig2.patch.set_facecolor(BG_CARD)
        ax2.set_facecolor(BG_CARD)
        days = np.arange(1, 31)
        np.random.seed(42)
        ai_days   = np.sort(np.random.choice(days, 23, replace=True))
        rule_days = np.sort(np.random.choice(days, 18, replace=True))
        snmp_days = np.sort(np.random.choice(days, 9,  replace=True))
        norm_days = np.sort(np.random.choice(days, 50, replace=True))

        ax2.scatter(norm_days, np.ones(len(norm_days)) * 0.5,
                    s=8, color=CYAN, alpha=0.5, label="Normal", zorder=2)
        ax2.scatter(snmp_days, np.ones(len(snmp_days)) * 1.5,
                    marker="s", s=35, color=YELLOW, label="SNMP Threshold", zorder=3)
        ax2.scatter(rule_days, np.ones(len(rule_days)) * 2.5,
                    marker="D", s=35, color=ORANGE, label="Rules Engine", zorder=3)
        ax2.scatter(ai_days,   np.ones(len(ai_days)) * 3.5,
                    marker="^", s=40, color=PURPLE, label="IsolationForest IA", zorder=4)

        ax2.set_yticks([0.5, 1.5, 2.5, 3.5])
        ax2.set_yticklabels(["Normal","SNMP","Rules","AI"],
                            color=TEXT2, fontsize=7)
        ax2.set_xticks([1, 7, 13, 19, 25, 31])
        ax2.set_xticklabels(["J1","J7","J13","J19","J25","J31"],
                            color=TEXT3, fontsize=7)
        ax2.spines[:].set_color(BORDER_DIM)
        ax2.grid(color=BORDER_DIM, lw=0.3, axis="x")
        ax2.legend(fontsize=7, facecolor=BG_CARD, labelcolor=TEXT2,
                   loc="upper left")
        _embed(fig2, card_t)

        # Precision bars
        card_p = _card(outer, "DETECTION PRECISION METRICS")
        fig3, ax3 = plt.subplots(figsize=(9, 2.2))
        fig3.patch.set_facecolor(BG_CARD)
        ax3.set_facecolor(BG_CARD)
        metrics = [
            ("IsolationForest F1-Score", 0.914, PURPLE),
            ("Rules Engine Precision",   0.887, ORANGE),
            ("SNMP Audit Score",         0.62,  RED),
            ("Taux Resolution Global",   0.76,  GREEN),
        ]
        names = [m[0] for m in metrics]
        vals  = [m[1] for m in metrics]
        cols  = [m[2] for m in metrics]
        bars3 = ax3.barh(names, vals, color=cols, height=0.5)
        ax3.axvline(0.85, color=ORANGE, lw=1, linestyle="--",
                    label="Target \u2265 85%")
        ax3.set_xlim(0, 1.1)
        for bar, v in zip(bars3, vals):
            ax3.text(v + 0.01, bar.get_y() + bar.get_height() / 2,
                     f"{v:.1%}", va="center", color=TEXT1, fontsize=8)
        ax3.tick_params(colors=TEXT3, labelsize=7)
        ax3.spines[:].set_color(BORDER_DIM)
        ax3.legend(fontsize=7, facecolor=BG_CARD, labelcolor=TEXT2)
        _embed(fig3, card_p)

        return outer

    def refresh(self, app_state):
        self.app_state = app_state

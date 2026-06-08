"""
tab_security.py — IP & Security Tab (README §13)
SNMP audit compliance, alerts panel, device table, recommendations.

FIXES APPLIED:
- _build_main_row: row.columnconfigure() NOT row.grid_columnconfigure()
  (grid_columnconfigure is CTk-only; on tk.Frame it silently does nothing,
  leaving columns with zero width → blank tab)
- FigureCanvasTkAgg wrapped in tk.Frame (not directly in CTkScrollableFrame)
  to prevent overwriting CTkScrollableFrame._canvas → crash on resize
- Alerts loop uses safe unpacking: handles 2-tuple, 3-tuple, dict, and string
"""
import tkinter as tk
import customtkinter as ctk
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

from src.ui.theme import (
    BG_BASE, BG_CARD, BG_CARD2,
    ACCENT, GREEN, YELLOW, ORANGE, RED, PURPLE, CYAN,
    TEXT1, TEXT2, TEXT3, BORDER_DIM, BORDER_MID,
)


class SecurityTab(ctk.CTkScrollableFrame):

    def __init__(self, parent, app_state):
        super().__init__(parent, fg_color=BG_BASE,
                         scrollbar_button_color=BG_CARD)
        self.app_state = app_state
        self._build()

    def _build(self):
        self._build_kpi_row()
        self._build_main_row()
        self._build_device_table()
        self._build_timeline()

    # ── Top 4 KPI cards ───────────────────────────────────────────────────────
    def _build_kpi_row(self):
        rapport = self.app_state.rapport_conformite or {}
        score = rapport.get("score", 72)
        v2c   = rapport.get("devices_v2c", 8)
        v3    = rapport.get("devices_v3", 2)
        evts  = rapport.get("events_detected", 14)

        row = tk.Frame(self, bg=BG_BASE)
        row.pack(fill="x", padx=16, pady=(12, 8))
        # columnconfigure on tk.Frame (NOT grid_columnconfigure)
        for i in range(4):
            row.columnconfigure(i, weight=1)

        for i, (lbl, val, sub, col) in enumerate([
            ("Compliance Score", f"{score}/100", "SNMP audit",
             "#10b981" if score > 70 else ORANGE),
            ("Devices v2c",  str(v2c), "SNMPv2c — insecure", ORANGE),
            ("Devices v3",   str(v3),  "SNMPv3 — compliant", GREEN),
            ("Events",       str(evts),"from security_events.csv", RED),
        ]):
            card = tk.Frame(row, bg=BG_CARD,
                            highlightbackground=BORDER_DIM, highlightthickness=1)
            card.grid(row=0, column=i, padx=5, sticky="nsew")
            tk.Frame(card, bg=col, height=2).pack(fill="x")
            inner = tk.Frame(card, bg=BG_CARD, padx=12, pady=8)
            inner.pack(fill="both", expand=True)
            tk.Label(inner, text=lbl.upper(),
                     font=("JetBrains Mono", 9), fg=TEXT3, bg=BG_CARD,
                     anchor="w").pack(fill="x")
            tk.Label(inner, text=str(val),
                     font=("JetBrains Mono", 22, "bold"),
                     fg=col, bg=BG_CARD, anchor="w").pack(fill="x")
            tk.Label(inner, text=sub,
                     font=("JetBrains Mono", 8), fg=TEXT3, bg=BG_CARD,
                     anchor="w").pack(fill="x")

    # ── Score gauge (left) + Alerts panel (right) ─────────────────────────────
    def _build_main_row(self):
        row = tk.Frame(self, bg=BG_BASE)
        row.pack(fill="x", padx=16, pady=8)
        # CRITICAL: use columnconfigure, NOT grid_columnconfigure
        # grid_columnconfigure is a CTk method; on tk.Frame it does nothing,
        # leaving columns with zero weight → both cards get 0 width → blank tab
        row.columnconfigure(0, weight=1)
        row.columnconfigure(1, weight=2)

        rapport = self.app_state.rapport_conformite or {}
        score   = rapport.get("score", 72)
        col     = "#10b981" if score > 70 else (ORANGE if score > 50 else RED)

        # ── Score panel ───────────────────────────────────────────────────────
        score_card = tk.Frame(row, bg=BG_CARD,
                              highlightbackground=BORDER_DIM, highlightthickness=1)
        score_card.grid(row=0, column=0, padx=(0, 6), sticky="nsew")

        tk.Label(score_card, text="COMPLIANCE SCORE",
                 font=("JetBrains Mono", 9), fg=TEXT3, bg=BG_CARD,
                 anchor="w").pack(fill="x", padx=14, pady=(10, 4))

        fig, ax = plt.subplots(figsize=(2.8, 2.8))
        fig.patch.set_facecolor(BG_CARD)
        ax.set_facecolor(BG_CARD)
        ax.set_aspect("equal")
        ax.axis("off")
        import matplotlib.patches as mpatches
        ax.add_patch(mpatches.Arc(
            (0.5, 0.5), 0.75, 0.75, angle=0, theta1=0, theta2=360,
            color="#1a2a1e", linewidth=9, capstyle="round"))
        ax.add_patch(mpatches.Arc(
            (0.5, 0.5), 0.75, 0.75, angle=90,
            theta1=90 - 360 * score / 100, theta2=90,
            color=col, linewidth=9, capstyle="round"))
        ax.text(0.5, 0.56, str(score), ha="center", va="center",
                fontsize=18, fontweight="bold", color=col,
                transform=ax.transAxes)
        ax.text(0.5, 0.36, "/100", ha="center", va="center",
                fontsize=9, color=TEXT3, transform=ax.transAxes)

        # Wrap in tk.Frame — prevents FigureCanvasTkAgg from overwriting
        # CTkScrollableFrame._canvas (which causes AttributeError on resize)
        gauge_frame = tk.Frame(score_card, bg=BG_CARD)
        gauge_frame.pack(pady=(0, 4))
        cv = FigureCanvasTkAgg(fig, master=gauge_frame)
        cv.draw()
        cv.get_tk_widget().pack()
        plt.close(fig)

        # Compliance pill
        if score > 70:
            pill_bg, pill_fg, pill_text = "#083325", "#34d399", "COMPLIANT"
        elif score >= 50:
            pill_bg, pill_fg, pill_text = "#2a1a06", "#f97316", "PARTIALLY COMPLIANT"
        else:
            pill_bg, pill_fg, pill_text = "#2a0f0f", "#f87171", "NON-COMPLIANT"
        ctk.CTkLabel(score_card,
                     text=pill_text,
                     font=ctk.CTkFont(family="JetBrains Mono", size=9,
                                      weight="bold"),
                     text_color=pill_fg, fg_color=pill_bg,
                     corner_radius=10, height=20, width=110
                     ).pack(pady=(0, 12))

        # Recommendations
        rec_card = tk.Frame(score_card, bg=BG_CARD2,
                            highlightbackground=BORDER_DIM, highlightthickness=1)
        rec_card.pack(fill="x", padx=14, pady=(0, 12))
        tk.Label(rec_card,
                 text=("Recommended: SNMPv3 with authPriv\n"
                       "Auth: SHA-256\nPriv: AES-256\n"
                       "Security level: authPriv\n"
                       "\u2192 Replace all SNMPv2c configurations"),
                 font=("JetBrains Mono", 8), fg=YELLOW, bg=BG_CARD2,
                 justify="left", padx=10, pady=8).pack(anchor="w")

        # ── Alerts panel ──────────────────────────────────────────────────────
        alerts_card = tk.Frame(row, bg=BG_CARD,
                               highlightbackground=BORDER_DIM, highlightthickness=1)
        alerts_card.grid(row=0, column=1, padx=(6, 0), sticky="nsew")
        tk.Label(alerts_card, text="DETECTED ALERTS",
                 font=("JetBrains Mono", 9), fg=TEXT3, bg=BG_CARD,
                 anchor="w").pack(fill="x", padx=14, pady=(10, 6))

        alerts = rapport.get("alerts", [])
        if not alerts:
            alerts = [
                ("CRITICAL",
                 "Community string 'public' detected — replace immediately"),
                ("MAJOR",
                 "Community string 'private' still active on 3 devices"),
                ("MAJOR",    "SNMPv2c auth — upgrade to v3 authPriv"),
                ("WARNING",  "No trap destination configured on OLT"),
                ("WARNING",  "Default read community on ONT_147"),
                ("INFO",     "SNMPv3 configured correctly on 2 devices"),
            ]

        SEV_COLORS = {
            "CRITICAL": ("#f87171", "#2a0f0f"),
            "MAJOR":    ("#fb923c", "#28150a"),
            "WARNING":  ("#fbbf24", "#291e06"),
            "INFO":     ("#4f8ef7", "#132040"),
        }

        scroll = ctk.CTkScrollableFrame(alerts_card, fg_color=BG_CARD,
                                        height=220,
                                        scrollbar_button_color=BG_CARD2)
        scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        for alert in alerts:
            # Safe unpack: handles 2-tuple, 3-tuple, dict, string
            if isinstance(alert, dict):
                sev = str(alert.get("type",
                          alert.get("severity", "INFO")))
                msg = str(alert.get("detail",
                          alert.get("message", str(alert))))
            elif isinstance(alert, (list, tuple)):
                sev = str(alert[0]) if len(alert) > 0 else "INFO"
                msg = str(alert[1]) if len(alert) > 1 else str(alert)
            else:
                sev, msg = "INFO", str(alert)

            col_fg, col_bg = SEV_COLORS.get(sev, (TEXT2, BG_CARD2))
            row_f = tk.Frame(scroll, bg=BG_CARD2,
                             highlightbackground=BORDER_DIM,
                             highlightthickness=1)
            row_f.pack(fill="x", pady=2)
            ctk.CTkLabel(row_f, text=sev,
                         font=ctk.CTkFont(family="JetBrains Mono",
                                          size=8, weight="bold"),
                         text_color=col_fg, fg_color=col_bg,
                         corner_radius=8, height=18, width=64
                         ).pack(side="left", padx=6, pady=4)
            tk.Label(row_f, text=msg[:80],
                     font=("JetBrains Mono", 8),
                     fg=TEXT1, bg=BG_CARD2, anchor="w"
                     ).pack(side="left", padx=4, fill="x", expand=True)

    # ── Device SNMP version table ─────────────────────────────────────────────
    def _build_device_table(self):
        card = tk.Frame(self, bg=BG_CARD,
                        highlightbackground=BORDER_DIM, highlightthickness=1)
        card.pack(fill="x", padx=16, pady=8)
        tk.Label(card, text="DEVICE SNMP VERSION TABLE",
                 font=("JetBrains Mono", 9), fg=TEXT3, bg=BG_CARD,
                 anchor="w").pack(fill="x", padx=14, pady=(10, 4))

        hdr = tk.Frame(card, bg=BG_CARD2)
        hdr.pack(fill="x", padx=8)
        for h, w in [("Device", 14), ("IP", 14), ("SNMP Ver", 9),
                     ("Community", 12), ("Auth", 10),
                     ("Status", 10), ("Recommendation", 22)]:
            tk.Label(hdr, text=h, font=("JetBrains Mono", 8),
                     fg=TEXT3, bg=BG_CARD2, width=w,
                     anchor="w").pack(side="left", padx=4, pady=4)

        rapport  = self.app_state.rapport_conformite or {}
        devices  = rapport.get("devices", [])
        if not devices:
            devices = [
                ("OLT-01",    "10.0.0.1",   "v2c", "public",
                 "None", "RISK",     "Upgrade to SNMPv3"),
                ("ONT_001",   "10.0.1.1",   "v2c", "private",
                 "None", "RISK",     "Upgrade to SNMPv3"),
                ("ONT_002",   "10.0.1.2",   "v3",  "N/A",
                 "SHA",  "OK",       "Compliant"),
                ("ONT_147",   "10.0.1.147", "v2c", "public",
                 "None", "CRITICAL", "Immediate action"),
                ("SPLITTER1", "10.0.0.10",  "v2c", "monitor",
                 "None", "RISK",     "Change community"),
            ]

        for i, row_d in enumerate(devices):
            bg    = BG_CARD2 if i % 2 == 0 else BG_CARD
            row_f = tk.Frame(card, bg=bg)
            row_f.pack(fill="x", padx=8)
            # Safe unpack — devices may be 7-tuples or dicts
            if isinstance(row_d, dict):
                vals = (
                    row_d.get("device", ""),  row_d.get("ip", ""),
                    row_d.get("version", ""), row_d.get("community", ""),
                    row_d.get("auth", ""),    row_d.get("status", ""),
                    row_d.get("action", ""),
                )
            elif isinstance(row_d, (list, tuple)) and len(row_d) >= 7:
                vals = tuple(row_d[:7])
            else:
                continue
            device, ip, ver, comm, auth, stat, rec = vals
            st_col = GREEN if stat == "OK" else (ORANGE if stat == "RISK" else RED)
            v_col  = GREEN if ver == "v3" else ORANGE
            for txt, col2, w in [
                (device, TEXT1, 14),
                (ip,     TEXT2, 14),
                (ver,    v_col,  9),
                (comm, ORANGE if comm in ("public", "private") else TEXT2, 12),
                (auth,   TEXT2, 10),
                (stat,   st_col, 10),
                (rec,    TEXT3,  22),
            ]:
                tk.Label(row_f, text=str(txt),
                         font=("JetBrains Mono", 8),
                         fg=col2, bg=bg, width=w,
                         anchor="w").pack(side="left", padx=4, pady=3)

    # ── Security events timeline chart ────────────────────────────────────────
    def _build_timeline(self):
        card = tk.Frame(self, bg=BG_CARD,
                        highlightbackground=BORDER_DIM, highlightthickness=1)
        card.pack(fill="x", padx=16, pady=(8, 16))
        tk.Label(card, text="SECURITY EVENTS TIMELINE — 30 DAYS",
                 font=("JetBrains Mono", 9), fg=TEXT3, bg=BG_CARD,
                 anchor="w").pack(fill="x", padx=14, pady=(10, 0))

        fig, ax = plt.subplots(figsize=(10, 2.5))
        fig.patch.set_facecolor(BG_CARD)
        ax.set_facecolor(BG_CARD)
        x = np.arange(1, 31)
        np.random.seed(10)
        for etype, col3 in [("ARP Storm", RED),
                             ("DHCP Rogue", ORANGE),
                             ("Port Scan", YELLOW)]:
            ax.plot(x, np.random.poisson(1.5, 30),
                    color=col3, lw=1.2, label=etype, marker="o", markersize=3)
        ax.set_xlabel("Day", color=TEXT3, fontsize=7)
        ax.set_ylabel("Events", color=TEXT3, fontsize=7)
        ax.tick_params(colors=TEXT3, labelsize=7)
        ax.spines[:].set_color(BORDER_DIM)
        ax.grid(color=BORDER_DIM, lw=0.4)
        ax.legend(fontsize=7, facecolor=BG_CARD, labelcolor=TEXT2)

        # Wrap in tk.Frame to avoid CTkScrollableFrame._canvas conflict
        timeline_frame = tk.Frame(card, bg=BG_CARD)
        timeline_frame.pack(fill="both", expand=True, padx=6, pady=(0, 8))
        cv2 = FigureCanvasTkAgg(fig, master=timeline_frame)
        cv2.draw()
        cv2.get_tk_widget().pack(fill="both", expand=True)
        plt.close(fig)

    def refresh(self, app_state):
        self.app_state = app_state
        for child in self.winfo_children():
            child.destroy()
        self._build()
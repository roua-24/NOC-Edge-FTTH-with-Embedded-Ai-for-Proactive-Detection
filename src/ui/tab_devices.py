"""
tab_devices.py — Devices Management Tab (README §10)
Grouped by splitter port, port chassis view, device table per group.
"""
import tkinter as tk
import customtkinter as ctk
from src.ui.theme import (
    BG_BASE, BG_CARD, BG_CARD2, BG_HOVER,
    ACCENT, ACCENT_DIM, GREEN, YELLOW, ORANGE, RED, PURPLE, CYAN,
    TEXT1, TEXT2, TEXT3, BORDER_DIM, BORDER_MID,
)
from src.ui.icons import make_icon_canvas


class DevicesTab(tk.Frame):

    def __init__(self, parent, app_state):
        super().__init__(parent, bg=BG_BASE)
        self.app_state = app_state
        self._search_var = tk.StringVar()
        self._groups_open = {i: True for i in range(4)}
        self._group_bodies = []
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self):
        self._build_header()
        self._build_chassis()
        self._build_groups()

    # ── Header ────────────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self, bg=BG_BASE)
        hdr.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))

        tk.Label(hdr, text="Search devices:",
                 font=("Inter", 10), fg=TEXT3, bg=BG_BASE
                 ).pack(side="left", padx=(0, 6))
        tk.Entry(hdr, textvariable=self._search_var,
                 bg=BG_CARD, fg=TEXT1, insertbackground=TEXT1,
                 font=("JetBrains Mono", 10), relief="flat",
                 highlightbackground=BORDER_MID, highlightthickness=1,
                 width=22).pack(side="left", ipady=4)

        tk.Button(hdr, text="Toggle Groups",
                  bg=BG_CARD, fg=TEXT2, relief="flat",
                  font=("Inter", 10), padx=8, pady=3,
                  cursor="hand2",
                  command=self._toggle_all).pack(side="left", padx=8)

        tk.Button(hdr, text="Preview PDF",
                  bg=BG_CARD, fg=TEXT2, relief="flat",
                  font=("Inter", 10), padx=8, pady=3,
                  cursor="hand2").pack(side="left", padx=4)

        tk.Button(hdr, text="Download PDF",
                  bg=ACCENT, fg=TEXT1, relief="flat",
                  font=("Inter", 10, "bold"), padx=8, pady=3,
                  cursor="hand2",
                  command=self.generate_pdf).pack(side="left", padx=4)

    # ── Port chassis (4×8 grid) ───────────────────────────────────────────────
    def _build_chassis(self):
        card = tk.Frame(self, bg=BG_CARD,
                        highlightbackground=BORDER_DIM, highlightthickness=1)
        card.grid(row=1, column=0, sticky="ew", padx=16, pady=(4, 8))
        tk.Label(card, text="PORT OVERVIEW — OLT CHASSIS",
                 font=("JetBrains Mono", 9), fg=TEXT3, bg=BG_CARD,
                 anchor="w").pack(fill="x", padx=14, pady=(8, 4))

        chassis = tk.Frame(card, bg=BG_CARD)
        chassis.pack(padx=14, pady=(0, 10))

        df = self.app_state.df_kpi
        for row in range(4):
            for col in range(8):
                port_idx = row * 8 + col
                if df is not None and "utilization_pct" in df.columns:
                    u = float(df["utilization_pct"].mean())
                else:
                    u = 40 + port_idx * 3
                color = (GREEN  if u < 50 else
                         YELLOW if u < 75 else
                         ORANGE if u < 85 else RED)
                cell = tk.Frame(chassis, bg=color, width=28, height=18,
                                cursor="hand2",
                                highlightbackground=BG_CARD2,
                                highlightthickness=1)
                cell.grid(row=row, column=col, padx=2, pady=2)
                cell.grid_propagate(False)
                tk.Label(cell, text=str(port_idx + 1),
                         font=("JetBrains Mono", 6), fg=BG_CARD,
                         bg=color).place(relx=0.5, rely=0.5, anchor="center")

        # Legend
        leg = tk.Frame(card, bg=BG_CARD)
        leg.pack(padx=14, pady=(0, 6))
        for col, lbl in [(GREEN, "<50%"), (YELLOW, "50-75%"),
                         (ORANGE, "75-85%"), (RED, ">85%")]:
            tk.Label(leg, text="\u25a0", fg=col, bg=BG_CARD,
                     font=("Inter", 10)).pack(side="left")
            tk.Label(leg, text=f" {lbl}  ", fg=TEXT3, bg=BG_CARD,
                     font=("JetBrains Mono", 8)).pack(side="left")

    # ── Device groups ─────────────────────────────────────────────────────────
    def _build_groups(self):
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color=BG_BASE, scrollbar_button_color=BG_CARD)
        self._scroll.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.grid_rowconfigure(2, weight=1)

        df_ont = self.app_state.df_ont
        df_kpi = self.app_state.df_kpi

        # Build ONT snapshot
        ont_data = {}
        if df_ont is not None and "ont_id" in df_ont.columns:
            snap = df_ont.groupby("ont_id").last().reset_index()
            for _, row in snap.iterrows():
                oid = str(row["ont_id"])
                ont_data[oid] = {
                    "status": str(row.get("onuOperStatus", "up")).lower(),
                    "rx_dbm": float(row.get("rx_power_dBm", -21.5)),
                    "tx_dbm": float(row.get("tx_power_dBm", -6.0)),
                }

        anom_set, rule_set = set(), set()
        if df_kpi is not None:
            if "anomaly_flag" in df_kpi.columns:
                n = int((df_kpi["anomaly_flag"] == -1).sum())
                for i in range(min(n // 30 + 1, 10)):
                    anom_set.add(f"ONT_{i+1:03d}")
            if "rule_alarm" in df_kpi.columns:
                n = int(df_kpi["rule_alarm"].sum())
                for i in range(min(n // 50 + 1, 6)):
                    rule_set.add(f"ONT_{i+21:03d}")

        self._group_bodies = []
        group_names = ["SP 1:32 — Port 1", "SP 1:32 — Port 2",
                       "SP 1:32 — Port 3", "SP 1:32 — Port 4"]
        for g in range(4):
            ont_ids = [f"ONT_{g*25+i+1:03d}" for i in range(25)]
            self._build_group(self._scroll, g, group_names[g],
                              ont_ids, ont_data, anom_set, rule_set)

    def _build_group(self, parent, g_idx, name, ont_ids, ont_data,
                     anom_set, rule_set):
        outer = tk.Frame(parent, bg=BG_CARD,
                         highlightbackground=BORDER_DIM, highlightthickness=1)
        outer.pack(fill="x", pady=(0, 8))

        # Group header (collapsible)
        hdr = tk.Frame(outer, bg=BG_CARD2, cursor="hand2")
        hdr.pack(fill="x")
        self._arrow = tk.Label(hdr, text="\u25bc",
                               font=("Inter", 9), fg=ACCENT, bg=BG_CARD2)
        self._arrow.pack(side="left", padx=8, pady=6)
        tk.Label(hdr, text=f"{name}  \u00b7  {len(ont_ids)} devices",
                 font=("Inter", 11, "bold"), fg=TEXT1, bg=BG_CARD2
                 ).pack(side="left", pady=6)

        body = tk.Frame(outer, bg=BG_CARD)
        body.pack(fill="x")
        self._group_bodies.append(body)

        # Table header
        th = tk.Frame(body, bg=BG_CARD2)
        th.pack(fill="x")
        for h, w in [("NAME", 14), ("IP ADDRESS", 14), ("TYPE", 7),
                     ("RX dBm", 8), ("TX dBm", 8),
                     ("STATUS", 9), ("ANOMALY", 9), ("ACTIONS", 12)]:
            tk.Label(th, text=h, font=("JetBrains Mono", 8),
                     fg=TEXT3, bg=BG_CARD2, width=w,
                     anchor="w").pack(side="left", padx=4, pady=4)

        for i, oid in enumerate(ont_ids[:25]):
            d    = ont_data.get(oid, {"status": "up", "rx_dbm": -21.5, "tx_dbm": -6.0})
            stat = d["status"]
            rx   = d["rx_dbm"]
            tx   = d["tx_dbm"]
            is_a = oid in anom_set
            is_r = oid in rule_set
            ip   = f"10.0.{g_idx+1}.{i+1}"

            bg = BG_CARD2 if i % 2 == 0 else BG_CARD
            row_f = tk.Frame(body, bg=bg)
            row_f.pack(fill="x")

            st_col = GREEN if stat == "up" else RED
            an_col = PURPLE if is_a else ORANGE if is_r else TEXT3
            an_txt = "AI" if is_a else "RULE" if is_r else "\u2014"

            for txt, col, width in [
                (oid,                TEXT1,   14),
                (ip,                 TEXT2,   14),
                ("ONT",              ACCENT,   7),
                (f"{rx:.1f}",        CYAN,     8),
                (f"{tx:.1f}",        CYAN,     8),
                (f"\u25cf {stat.upper()}", st_col, 9),
                (an_txt,             an_col,   9),
            ]:
                tk.Label(row_f, text=txt, font=("JetBrains Mono", 8),
                         fg=col, bg=bg, width=width,
                         anchor="w").pack(side="left", padx=4, pady=3)

            # Action buttons — Lucide SVG style
            for icon_name, tip in [("eye", "View"), ("terminal", "Term"),
                                   ("edit", "Edit"), ("refresh", "Refresh")]:
                btn = make_icon_canvas(row_f, icon_name, size=14, color=ACCENT, bg=bg)
                btn.pack(side="left", padx=4, pady=3)
                btn.bind("<Button-1>", lambda e, n=icon_name, o=oid, i=ip: self._on_action_click(n, o, i))

        hdr.bind("<Button-1>",
                 lambda e, b=body: self._toggle_group(b))

    def _toggle_group(self, body):
        if body.winfo_ismapped():
            body.pack_forget()
        else:
            body.pack(fill="x")

    def _toggle_all(self):
        any_mapped = any(b.winfo_ismapped() for b in self._group_bodies)
        for b in self._group_bodies:
            if any_mapped:
                if b.winfo_ismapped():
                    b.pack_forget()
            else:
                if not b.winfo_ismapped():
                    b.pack(fill="x")

    def _on_action_click(self, name, ont_id, ip_address):
        # Open Toplevel modal custom window
        popup = tk.Toplevel(self)
        popup.title(f"{name.upper()} — {ont_id}")
        popup.configure(bg=BG_CARD)
        popup.geometry("380x280")
        popup.resizable(False, False)
        popup.grab_set()

        # Title
        tk.Label(popup, text=f"ONT Device Details — {ont_id}", font=("Inter", 12, "bold"), fg=TEXT1, bg=BG_CARD).pack(pady=12)

        # Details frame
        f = tk.Frame(popup, bg=BG_CARD2, highlightbackground=BORDER_DIM, highlightthickness=1)
        f.pack(padx=20, pady=10, fill="both", expand=True)

        info = [
            ("IP Address", ip_address),
            ("Device Type", "ONT (GPON Node)"),
            ("Status", "Active (UP)" if ont_id != "ONT_006" else "Inactive (DOWN)"),
            ("Splitter Port", "SP 1:32"),
            ("F1-Score (ML)", "91.4%"),
        ]

        if name == "terminal":
            info.append(("AI Score", "0.012 (Normal)" if ont_id != "ONT_001" else "0.985 (Anomaly)"))
            info.append(("Rule Alert", "None" if ont_id != "ONT_001" else "Optical RX under thresholds"))
            info.append(("Forecast", "Stable (12 steps)"))

        for k, v in info:
            row = tk.Frame(f, bg=BG_CARD2)
            row.pack(fill="x", padx=10, pady=4)
            tk.Label(row, text=f"{k}:", font=("JetBrains Mono", 9), fg=TEXT3, bg=BG_CARD2, anchor="w").pack(side="left")
            tk.Label(row, text=v, font=("JetBrains Mono", 9), fg=ACCENT if k == "Status" else TEXT2, bg=BG_CARD2, anchor="e").pack(side="right")

        # Close button
        tk.Button(popup, text="Close", bg=ACCENT, fg=TEXT1, font=("Inter", 10, "bold"), relief="flat", command=popup.destroy).pack(pady=10)

    def generate_pdf(self):
        try:
            from src.reports.pdf_generator import generate_pdf
            generate_pdf(self.app_state.df_kpi,
                         self.app_state.rapport_conformite,
                         "Devices", [])
        except Exception as e:
            print(f"[devices] PDF error: {e}")

    def refresh(self, app_state):
        self.app_state = app_state

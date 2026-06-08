"""
tab_activity.py — Activity History Tab (README §8)
Scrollable event log of anomalies and rule alarms.
"""
import tkinter as tk
import customtkinter as ctk
import datetime
import pandas as pd
from src.ui.theme import (
    BG_BASE, BG_CARD, BG_CARD2, BG_HOVER,
    ACCENT, GREEN, YELLOW, ORANGE, RED, PURPLE, CYAN,
    TEXT1, TEXT2, TEXT3, BORDER_DIM, BORDER_MID,
)


class ActivityTab(tk.Frame):

    def __init__(self, parent, app_state):
        super().__init__(parent, bg=BG_BASE)
        self.app_state = app_state
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._filter_var = tk.StringVar(value="All")
        self._search_var = tk.StringVar()
        self._events = []
        self._build()

    def _build(self):
        self._build_header()
        self._build_stats_row()
        self._build_table_area()
        self._load_events()

    # ── Header ────────────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self, bg=BG_BASE)
        hdr.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))

        tk.Label(hdr, text="Search events:",
                 font=("Inter", 10), fg=TEXT3, bg=BG_BASE
                 ).pack(side="left", padx=(0, 6))

        entry = tk.Entry(hdr, textvariable=self._search_var,
                         bg=BG_CARD, fg=TEXT1, insertbackground=TEXT1,
                         font=("JetBrains Mono", 10), relief="flat",
                         highlightbackground=BORDER_MID, highlightthickness=1,
                         width=24)
        entry.pack(side="left", padx=4, ipady=4)
        entry.bind("<KeyRelease>", lambda e: self._apply_filter())

        tk.Label(hdr, text="Filter:", font=("Inter", 10),
                 fg=TEXT3, bg=BG_BASE).pack(side="left", padx=(12, 4))
        for opt in ("All", "AI", "Rule", "Critical"):
            btn = tk.Label(hdr, text=opt, font=("JetBrains Mono", 9),
                           fg=ACCENT if opt == "All" else TEXT2,
                           bg=BG_CARD if opt == "All" else BG_BASE,
                           padx=10, pady=4, cursor="hand2",
                           highlightbackground=BORDER_DIM, highlightthickness=1)
            btn.pack(side="left", padx=2)
            btn.bind("<Button-1>",
                     lambda e, o=opt, b=btn: self._set_filter(o))

        tk.Button(hdr, text="Export CSV",
                  bg=BG_CARD, fg=TEXT2, relief="flat",
                  font=("Inter", 10), padx=8, pady=3,
                  cursor="hand2",
                  command=self._export_csv
                  ).pack(side="right", padx=4)

    # ── Stats row ─────────────────────────────────────────────────────────────
    def _build_stats_row(self):
        self._stats_frame = tk.Frame(self, bg=BG_BASE)
        self._stats_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=4)
        for i in range(4):
            self._stats_frame.grid_columnconfigure(i, weight=1)
        self._stats_labels = {}
        for i, (k, v, col) in enumerate([
            ("Total Events", "0",    ACCENT),
            ("Open",         "0",    RED),
            ("Resolved",     "0",    GREEN),
            ("Avg Duration", "5m",   CYAN if True else YELLOW),
        ]):
            card = tk.Frame(self._stats_frame, bg=BG_CARD,
                            highlightbackground=BORDER_DIM, highlightthickness=1)
            card.grid(row=0, column=i, padx=5, sticky="nsew")
            tk.Label(card, text=k.upper(), font=("JetBrains Mono", 9),
                     fg=TEXT3, bg=BG_CARD).pack(pady=(8, 2))
            lbl = tk.Label(card, text=v, font=("JetBrains Mono", 18, "bold"),
                           fg=col, bg=BG_CARD)
            lbl.pack(pady=(0, 8))
            self._stats_labels[k] = lbl

    # ── Table ─────────────────────────────────────────────────────────────────
    def _build_table_area(self):
        wrapper = tk.Frame(self, bg=BG_BASE)
        wrapper.grid(row=2, column=0, sticky="nsew", padx=16, pady=(4, 16))
        self.grid_rowconfigure(2, weight=1)
        wrapper.grid_rowconfigure(1, weight=1)
        wrapper.grid_columnconfigure(0, weight=1)

        # Header row
        hdr = tk.Frame(wrapper, bg=BG_CARD2,
                       highlightbackground=BORDER_DIM, highlightthickness=1)
        hdr.grid(row=0, column=0, sticky="ew")
        cols = [("Timestamp",11),("Type",6),("ONT ID",9),
                ("KPI",10),("Value",8),("Source",7),
                ("Severity",9),("Message",26),("Action",7)]
        for h, w in cols:
            tk.Label(hdr, text=h, font=("JetBrains Mono", 8),
                     fg=TEXT3, bg=BG_CARD2, width=w,
                     anchor="w").pack(side="left", padx=4, pady=5)

        self._table_frame = ctk.CTkScrollableFrame(
            wrapper, fg_color=BG_BASE,
            scrollbar_button_color=BG_CARD)
        self._table_frame.grid(row=1, column=0, sticky="nsew")

    def _load_events(self):
        df = self.app_state.df_kpi
        events = []
        if df is not None:
            df = df.copy()
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                now = df["timestamp"].max()
                cutoff = now - pd.Timedelta(hours=24)
            else:
                now = pd.Timestamp.now()
                cutoff = now - pd.Timedelta(hours=24)

            # Assign round-robin ONT IDs based on row index (P2-02)
            n_onts = 100
            df["ont_id"] = [f"ONT_{(i % n_onts) + 1:03d}" for i in range(len(df))]

            mask = pd.Series([False] * len(df))
            if "rule_alarm" in df.columns:
                mask = mask | df["rule_alarm"].astype(bool)
            if "anomaly_flag" in df.columns:
                mask = mask | (df["anomaly_flag"] == -1)
            evdf = df[mask].copy()
            if "timestamp" in evdf.columns:
                evdf = evdf.sort_values("timestamp", ascending=False)

            KPI_LABELS = {
                "anomaly_score":   "Anomaly Score",
                "utilization_pct": "Utilization %",
                "debit_rx_mbps":   "RX Mbit/s",
                "debit_tx_mbps":   "TX Mbit/s",
                "error_rate_pct":  "Error Rate %",
                "rule_alarm":      "Rule Alarm",
            }

            for _, row in evdf.head(200).iterrows():
                t_val = row.get("timestamp")
                ts = str(t_val)[:16]
                is_ai   = row.get("anomaly_flag", 1) == -1
                is_rule = bool(row.get("rule_alarm", False))
                typ  = "AI" if is_ai else "RULE"
                
                # Human-readable KPI label (P2-03)
                raw_kpi = "utilization_pct" if is_rule else "anomaly_score"
                kpi = KPI_LABELS.get(raw_kpi, raw_kpi)

                val  = (f"{row.get('utilization_pct', 0):.1f}%"
                        if is_rule else
                        f"{row.get('anomaly_score', 0):.3f}")
                src  = "IsolationForest" if is_ai else "rules_engine"
                sev  = ("CRITICAL" if is_ai and is_rule else
                        "MAJOR"    if is_ai else "WARNING")
                msg  = (row.get("rule_detail", "") or
                        "Anomaly detected by IsolationForest")[:40]
                
                # Open / Resolved logic (P2-04)
                status = "Open" if t_val >= cutoff else "Resolved"
                ont = row.get("ont_id", "ONT_001")
                
                events.append((ts, typ, ont, kpi, val, src, sev, msg, status))
        if not events:
            for i in range(20):
                sev = ["CRITICAL","MAJOR","WARNING"][i%3]
                status = "Resolved" if i >= 5 else "Open"
                events.append((
                    f"2026-03-{15+i//10:02d} {i%24:02d}:00",
                    ["AI","RULE"][i%2],
                    f"ONT_{i*7+1:03d}",
                    ["Utilization %","Error Rate %"][i%2],
                    ["92.3%","1.8%"][i%2],
                    ["IsolationForest","rules_engine"][i%2],
                    sev,
                    ["Utilization spike detected","Error rate exceeded threshold"][i%2],
                    status
                ))
        self._events = events
        self._update_stats()
        self._render_table(events)

    def _render_table(self, events):
        for w in self._table_frame.winfo_children():
            w.destroy()

        TYPE_BG  = {"AI": PURPLE,  "RULE": ORANGE}
        SEV_COL  = {"CRITICAL": RED, "MAJOR": ORANGE,
                    "WARNING": YELLOW, "INFO": ACCENT}

        for i, (ts, typ, ont, kpi, val, src, sev, msg, status) in enumerate(events):
            bg = BG_CARD2 if i % 2 == 0 else BG_CARD
            row_f = tk.Frame(self._table_frame, bg=bg)
            row_f.pack(fill="x")

            type_bg  = TYPE_BG.get(typ, ACCENT)
            sev_col  = SEV_COL.get(sev, TEXT2)

            for txt, col, width, bold in [
                (ts,   TEXT2,    11, False),
                (typ,  TEXT1,     6, True),
                (ont,  TEXT1,     9, False),
                (kpi,  TEXT2,    10, False),
                (val,  ACCENT,    8, False),
                (src,  PURPLE if typ=="AI" else ORANGE, 7, False),
                (sev,  sev_col,   9, True),
                (msg,  TEXT1,    26, False),
            ]:
                font = ("JetBrains Mono", 8, "bold" if bold else "normal")
                tk.Label(row_f, text=txt, font=font,
                         fg=col, bg=bg, width=width,
                         anchor="w").pack(side="left", padx=4, pady=3)

            tk.Label(row_f, text="View", font=("JetBrains Mono", 8),
                     fg=ACCENT, bg=bg, cursor="hand2"
                     ).pack(side="left", padx=6)

    def _update_stats(self):
        total = len(self._events)
        opens = sum(1 for e in self._events if e[8] == "Open")
        resolved = total - opens
        self._stats_labels["Total Events"].config(text=str(total))
        self._stats_labels["Open"].config(text=str(opens))
        self._stats_labels["Resolved"].config(text=str(resolved))

    def _set_filter(self, opt):
        self._filter_var.set(opt)
        self._apply_filter()

    def _apply_filter(self):
        flt = self._filter_var.get()
        srch = self._search_var.get().lower()
        filtered = self._events
        if flt == "AI":
            filtered = [e for e in filtered if e[1] == "AI"]
        elif flt == "Rule":
            filtered = [e for e in filtered if e[1] == "RULE"]
        elif flt == "Critical":
            filtered = [e for e in filtered if e[6] == "CRITICAL"]
        if srch:
            filtered = [e for e in filtered
                        if any(srch in str(v).lower() for v in e)]
        self._render_table(filtered)

    def _export_csv(self):
        try:
            df = self.app_state.df_kpi
            if df is not None:
                cols = [c for c in
                        ["timestamp","ont_id","utilization_pct",
                         "anomaly_flag","rule_alarm","anomaly_score"]
                        if c in df.columns]
                path = f"reports/activity_{datetime.date.today()}.csv"
                df[cols].to_csv(path, index=False)
                print(f"[activity] Exported: {path}")
        except Exception as e:
            print(f"[activity] Export error: {e}")

    def refresh(self, app_state):
        self.app_state = app_state
        self._load_events()

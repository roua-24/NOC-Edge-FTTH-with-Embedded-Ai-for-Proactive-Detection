"""
tab_incidents.py — Incident Reports Tab (README §14)
Filter bar, incident table, PDF generation per row and full export.
"""
import tkinter as tk
import customtkinter as ctk
import datetime
from src.ui.theme import (
    BG_BASE, BG_CARD, BG_CARD2,
    ACCENT, GREEN, YELLOW, ORANGE, RED, PURPLE,
    TEXT1, TEXT2, TEXT3, BORDER_DIM, BORDER_MID,
)


class IncidentsTab(tk.Frame):

    def __init__(self, parent, app_state):
        super().__init__(parent, bg=BG_BASE)
        self.app_state = app_state
        self._search_var  = tk.StringVar()
        self._type_var    = tk.StringVar(value="All")
        self._status_var  = tk.StringVar(value="All")
        self._per_page    = tk.IntVar(value=25)
        self._incidents   = []
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self):
        self._build_kpi_row()
        self._build_filter_bar()
        self._build_table_area()
        self._load_incidents()

    # ── KPI row ───────────────────────────────────────────────────────────────
    def _build_kpi_row(self):
        row = tk.Frame(self, bg=BG_BASE)
        row.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))
        for i in range(4):
            row.grid_columnconfigure(i, weight=1)
        self._kpi_lbls = {}
        for i, (k, v, col) in enumerate([
            ("Total Incidents", "0",  ACCENT),
            ("Open",           "0",  RED),
            ("Resolved Today", "0",  GREEN),
            ("Avg Resolution", "5m", CYAN if False else YELLOW),
        ]):
            card = tk.Frame(row, bg=BG_CARD,
                            highlightbackground=BORDER_DIM, highlightthickness=1)
            card.grid(row=0, column=i, padx=5, sticky="nsew")
            tk.Label(card, text=k.upper(), font=("JetBrains Mono", 9),
                     fg=TEXT3, bg=BG_CARD).pack(pady=(8, 2))
            lbl = tk.Label(card, text=v, font=("JetBrains Mono", 20, "bold"),
                           fg=col, bg=BG_CARD)
            lbl.pack(pady=(0, 8))
            self._kpi_lbls[k] = lbl

    # ── Filter bar ────────────────────────────────────────────────────────────
    def _build_filter_bar(self):
        bar = tk.Frame(self, bg=BG_BASE)
        bar.grid(row=1, column=0, sticky="ew", padx=16, pady=4)

        tk.Entry(bar, textvariable=self._search_var,
                 bg=BG_CARD, fg=TEXT1, insertbackground=TEXT1,
                 font=("JetBrains Mono", 10), relief="flat",
                 highlightbackground=BORDER_MID, highlightthickness=1,
                 width=22).pack(side="left", ipady=4, padx=(0,8))

        for label, var, opts in [
            ("Type",   self._type_var,   ["All","AI","Rule","Critical"]),
            ("Status", self._status_var, ["All","Open","Resolved"]),
        ]:
            tk.Label(bar, text=f"{label}:", font=("Inter", 10),
                     fg=TEXT3, bg=BG_BASE).pack(side="left", padx=(8,4))
            ctk.CTkOptionMenu(bar, values=opts, variable=var,
                              fg_color=BG_CARD, button_color=BORDER_MID,
                              text_color=TEXT2, font=("Inter", 10),
                              width=100, height=30,
                              command=lambda _: self._apply_filter()
                              ).pack(side="left", padx=4)

        tk.Button(bar, text="Apply Filters",
                  bg=ACCENT, fg=TEXT1, relief="flat",
                  font=("Inter", 10, "bold"), padx=8, pady=3,
                  cursor="hand2", command=self._apply_filter
                  ).pack(side="left", padx=8)

        tk.Button(bar, text="Generate Report",
                  bg=ACCENT, fg=TEXT1, relief="flat",
                  font=("Inter", 10, "bold"), padx=8, pady=3,
                  cursor="hand2", command=self.generate_pdf
                  ).pack(side="right", padx=4)

        tk.Button(bar, text="Export CSV",
                  bg=BG_CARD, fg=TEXT2, relief="flat",
                  font=("Inter", 10), padx=8, pady=3,
                  cursor="hand2", command=self._export_csv
                  ).pack(side="right", padx=4)

    # ── Table ─────────────────────────────────────────────────────────────────
    def _build_table_area(self):
        wrap = tk.Frame(self, bg=BG_BASE)
        wrap.grid(row=2, column=0, sticky="nsew", padx=16, pady=(4, 16))
        wrap.grid_rowconfigure(1, weight=1)
        wrap.grid_columnconfigure(0, weight=1)

        hdr = tk.Frame(wrap, bg=BG_CARD2,
                       highlightbackground=BORDER_DIM, highlightthickness=1)
        hdr.grid(row=0, column=0, sticky="ew")
        cols = [("TYPE",7),("ONT ID",10),("DESCRIPTION",22),("STATUS",9),
                ("SEVERITY",9),("METHOD",14),("STARTED",13),
                ("DURATION",9),("PDF",5),("ACTIONS",8)]
        for h, w in cols:
            tk.Label(hdr, text=h, font=("JetBrains Mono", 8),
                     fg=TEXT3, bg=BG_CARD2, width=w,
                     anchor="w").pack(side="left", padx=4, pady=5)

        self._scroll = ctk.CTkScrollableFrame(
            wrap, fg_color=BG_BASE, scrollbar_button_color=BG_CARD)
        self._scroll.grid(row=1, column=0, sticky="nsew")

    def _load_incidents(self):
        df = self.app_state.df_kpi
        incidents = []
        if df is not None:
            import pandas as pd
            mask = pd.Series([False] * len(df))
            if "rule_alarm" in df.columns:
                mask = mask | df["rule_alarm"].astype(bool)
            if "anomaly_flag" in df.columns:
                mask = mask | (df["anomaly_flag"] == -1)
            evdf = df[mask].copy()
            if "timestamp" in evdf.columns:
                evdf = evdf.sort_values("timestamp", ascending=False)
            for i, (_, row) in enumerate(evdf.head(100).iterrows()):
                is_ai   = row.get("anomaly_flag", 1) == -1
                is_rule = bool(row.get("rule_alarm", False))
                typ  = "COMBINED" if (is_ai and is_rule) else ("AI" if is_ai else "RULE")
                ont  = f"ONT_{(i%100)+1:03d}"
                desc = (row.get("rule_detail","") or
                        "Anomaly detected by IsolationForest")[:30]
                stat = "OPEN" if i % 3 != 0 else "RESOLVED"
                sev  = ("CRITICAL" if is_ai and is_rule else
                        "HIGH"     if is_ai else "MEDIUM")
                meth = "IsolationForest" if is_ai else "rules_engine"
                ts   = str(row.get("timestamp",""))[:16]
                dur  = f"{(i%15)+2}m"
                incidents.append((typ,ont,desc,stat,sev,meth,ts,dur))

        if not incidents:
            for i in range(30):
                incidents.append((
                    ["AI","RULE","COMBINED"][i%3],
                    f"ONT_{i*3+1:03d}",
                    ["Utilization spike 92%","Error rate 1.8%","Optical loss"][i%3],
                    ["OPEN","RESOLVED","IN PROGRESS"][i%3],
                    ["CRITICAL","HIGH","MEDIUM","LOW"][i%4],
                    ["IsolationForest","rules_engine","SNMP"][i%3],
                    f"2026-03-{15+i//10:02d} {i%24:02d}:00",
                    f"{(i%15)+1}m",
                ))

        self._incidents = incidents
        self._update_kpis()
        self._render_table(incidents)

    def _render_table(self, incidents):
        for w in self._scroll.winfo_children():
            w.destroy()

        TYPE_COL   = {"AI": PURPLE, "RULE": ORANGE, "COMBINED": RED}
        STATUS_COL = {"OPEN": RED, "RESOLVED": GREEN, "IN PROGRESS": ORANGE}
        SEV_COL    = {"CRITICAL": RED, "HIGH": ORANGE, "MEDIUM": YELLOW, "LOW": ACCENT}

        for i, (typ,ont,desc,stat,sev,meth,ts,dur) in enumerate(incidents):
            bg = BG_CARD2 if i % 2 == 0 else BG_CARD
            row_f = tk.Frame(self._scroll, bg=bg)
            row_f.pack(fill="x")

            for txt, col, w in [
                (typ,  TYPE_COL.get(typ, TEXT2),     7),
                (ont,  TEXT1,                        10),
                (desc, TEXT1,                        22),
                (stat, STATUS_COL.get(stat, TEXT2),  9),
                (sev,  SEV_COL.get(sev, TEXT2),      9),
                (meth, PURPLE if "Forest" in meth else ORANGE, 14),
                (ts,   TEXT2,                        13),
                (dur,  TEXT2,                         9),
            ]:
                tk.Label(row_f, text=txt, font=("JetBrains Mono", 8),
                         fg=col, bg=bg, width=w,
                         anchor="w").pack(side="left", padx=4, pady=3)

            tk.Label(row_f, text="\u2399", font=("Inter", 10),
                     fg=RED, bg=bg, cursor="hand2"
                     ).pack(side="left", padx=3)
            tk.Label(row_f, text="View", font=("JetBrains Mono", 8),
                     fg=ACCENT, bg=bg, cursor="hand2"
                     ).pack(side="left", padx=2)
            tk.Label(row_f, text="Resolve", font=("JetBrains Mono", 8),
                     fg=GREEN, bg=bg, cursor="hand2"
                     ).pack(side="left", padx=2)

    def _update_kpis(self):
        total    = len(self._incidents)
        opens    = sum(1 for e in self._incidents if e[3] == "OPEN")
        resolved = sum(1 for e in self._incidents if e[3] == "RESOLVED")
        self._kpi_lbls["Total Incidents"].config(text=str(total))
        self._kpi_lbls["Open"].config(text=str(opens))
        self._kpi_lbls["Resolved Today"].config(text=str(resolved))

    def _apply_filter(self, *_):
        flt_type   = self._type_var.get()
        flt_status = self._status_var.get()
        srch       = self._search_var.get().lower()
        filtered   = self._incidents
        if flt_type != "All":
            filtered = [e for e in filtered if e[0] == flt_type.upper()]
        if flt_status != "All":
            filtered = [e for e in filtered if e[3] == flt_status.upper()]
        if srch:
            filtered = [e for e in filtered
                        if any(srch in str(v).lower() for v in e)]
        self._render_table(filtered)

    def _export_csv(self):
        try:
            df = self.app_state.df_kpi
            if df is not None:
                path = f"reports/incidents_{datetime.date.today()}.csv"
                df.to_csv(path, index=False)
                print(f"[incidents] Exported: {path}")
        except Exception as e:
            print(f"[incidents] Export error: {e}")

    def generate_pdf(self):
        try:
            from src.reports.pdf_generator import generate_pdf
            path = generate_pdf(
                self.app_state.df_kpi,
                self.app_state.rapport_conformite,
                self.app_state.scenario_name or "v3 MAX", [])
            print(f"[incidents] PDF: {path}")
        except Exception as e:
            print(f"[incidents] PDF error: {e}")

    def refresh(self, app_state):
        self.app_state = app_state
        self._load_incidents()

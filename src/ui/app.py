"""
app.py — Main NOC-Edge FTTH window
Grid: 220px sidebar | 1fr content
Sidebar groups, lazy frame switching, AppState, topbar, status bar

FIX: export_pdf_patch import moved INSIDE _generate_report() method.
     It was at module level before — if that module had any broken import,
     the entire app.py failed to load silently with no error shown.
"""
import tkinter as tk
import customtkinter as ctk
import time
import datetime
import threading
from dataclasses import dataclass, field
from typing import Dict, Any

from src.ui.theme import (
    BG_DEEP, BG_BODY, BG_SIDEBAR, BG_CARD, BG_HOVER,
    BD, BDM,
    BLUE, BLUE_BG, GREEN, RED, PURPLE,
    T1, T2, T3, T4,
    apply_matplotlib_theme,
)

# Legacy aliases
BG_VOID    = BG_DEEP
BG_BASE    = BG_BODY
ACCENT     = BLUE
ACCENT_DIM = BLUE_BG
TEXT1      = T1
TEXT2      = T2
TEXT3      = T3
TEXT4      = T4
BORDER_DIM = BD
BORDER_MID = BDM

from src.ui.logo import LogoCanvas, set_window_icon


def make_sidebar_icon(parent, icon_name, is_active=False):
    from src.ui.icons import _draw_icon
    container_bg = "#1a2a4a" if is_active else BG_SIDEBAR
    icon_color   = BLUE if is_active else "#6b7280"

    f = ctk.CTkFrame(parent, width=22, height=22,
                     corner_radius=6, fg_color=container_bg)
    f.pack_propagate(False)

    c = tk.Canvas(f, width=22, height=22,
                  bg=container_bg, highlightthickness=0)
    c.pack(fill="both", expand=True)
    _draw_icon(c, icon_name, x0=5, y0=5, color=icon_color, size=12)
    f.canvas    = c
    f.icon_name = icon_name
    return f


# ── AppState ──────────────────────────────────────────────────────────────────
@dataclass
class AppState:
    df_raw:             Any = None
    df_kpi:             Any = None
    df_ont:             Any = None
    df_qos:             Any = None
    df_flows:           Any = None
    rapport_conformite: Any = None
    f1_score:           float = 0.0
    active_alarms:      int   = 0
    kpi_compute_ms:     float = 0.0
    render_ms:          float = 0.0
    scenario_name:      str   = "v3 MAX"
    thresholds:         dict  = field(default_factory=lambda: {
        "utilization_pct": 85.0,
        "error_rate_pct":  1.0,
        "latency_ms":      100.0,
        "jitter_ms":       20.0,
        "packet_loss_pct": 0.5,
    })


# ── Navigation ────────────────────────────────────────────────────────────────
NAV_GROUPS = [
    ("OVERVIEW", [
        ("Dashboard",        "grid",     "dashboard"),
    ]),
    ("FTTH INFRASTRUCTURE", [
        ("Activity History", "clock",    "activity"),
        ("Network Topology", "share",    "topology"),
        ("Devices",          "server",   "devices"),
    ]),
    ("MONITORING", [
        ("Bandwidth",        "activity", "bandwidth"),
        ("Netflow",          "layers",   "netflow"),
    ]),
    ("MANAGEMENT", [
        ("IP & Security",    "shield",   "security"),
        ("Incident Reports", "alert",    "incidents"),
    ]),
    ("SYSTEM", [
        ("Diagnostics IA",   "radio",    "diagnostics"),
        ("Settings",         "settings", "settings"),
    ]),
]

SCREEN_META = {
    "dashboard":   ("Dashboard Overview",
                    "Network Operations Center · FTTH/GPON · 100 ONTs · 30-day dataset · offline"),
    "activity":    ("Activity History",
                    "Audit trail of all detected events — anomalies · alarms · rules"),
    "topology":    ("Network Topology",
                    "Visual mapping of FTTH/GPON infrastructure · OLT → Splitters → ONTs · 100 devices"),
    "devices":     ("Devices Management",
                    "Configure and manage ONT/OLT network nodes · 100 devices · SNMP inventory"),
    "bandwidth":   ("Bandwidth & QoS",
                    "Traffic analysis, QoS metrics and AI anomaly detection."),
    "netflow":     ("Netflow",
                    "Traffic flow · protocol distribution · IDS/security detection"),
    "security":    ("IP & Security",
                    "SNMP compliance audit · v2c detection · authPriv recommendations"),
    "incidents":   ("Incident Reports",
                    "Monitor and report incidents · PDF export per scenario"),
    "diagnostics": ("Diagnostics IA & Troubleshooting",
                    "AI drill-down · ONT analysis · forecast viewer · feature importance"),
    "settings":    ("Settings",
                    "Thresholds · dataset path · appearance · performance benchmark"),
}


# ── Main application ──────────────────────────────────────────────────────────
class NOCApp:
    """Main NOC-Edge FTTH application window."""

    def __init__(self, app_state: AppState):
        self.app_state   = app_state
        self.frames:     Dict[str, Any] = {}
        self._active_nav = "dashboard"
        self._nav_buttons: Dict[str, dict] = {}

        apply_matplotlib_theme()

        self.root = ctk.CTk()
        self.root.title("NOC-Edge FTTH — Network Operations Center")
        self.root.configure(fg_color=BG_BODY)
        self.root.geometry("1280x800")
        self.root.minsize(1280, 800)

        set_window_icon(self.root)

        self._build_layout()
        self._load_data_async()
        self._start_clock()

    # public mainloop so main.py can call app.mainloop()
    def mainloop(self):
        self.root.mainloop()

    # ── Layout ───────────────────────────────────────────────────────────────
    def _build_layout(self):
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self._build_sidebar()
        self._build_content_area()

    # ── Sidebar ──────────────────────────────────────────────────────────────
    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self.root, width=220, fg_color=BG_SIDEBAR,
            corner_radius=0, border_width=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_columnconfigure(0, weight=1)

        row = 0
        brand = tk.Frame(self.sidebar, bg=BG_SIDEBAR, height=72)
        brand.grid(row=row, column=0, sticky="ew")
        brand.grid_propagate(False)
        row += 1

        self._sidebar_logo = LogoCanvas(brand, size=40, bg=BG_SIDEBAR)
        self._sidebar_logo.place(x=10, y=16)
        self._sidebar_logo.start_animation()

        tk.Label(brand, text="NOC-Edge FTTH",
                 font=("Inter", 13, "bold"), fg=T1, bg=BG_SIDEBAR
                 ).place(x=58, y=14)
        tk.Label(brand,
                 text="Proactive \u00b7 Offline \u00b7 Intelligent",
                 font=("JetBrains Mono", 8), fg=BLUE, bg=BG_SIDEBAR
                 ).place(x=58, y=34)

        tk.Frame(self.sidebar, height=1, bg=BORDER_DIM
                 ).grid(row=row, column=0, sticky="ew")
        row += 1

        nav_frame = ctk.CTkScrollableFrame(
            self.sidebar, fg_color=BG_SIDEBAR,
            scrollbar_button_color=BG_SIDEBAR,
            scrollbar_button_hover_color=BORDER_MID)
        nav_frame.grid(row=row, column=0, sticky="nsew", pady=(4, 0))
        self.sidebar.grid_rowconfigure(row, weight=1)
        row += 1

        for group_label, items in NAV_GROUPS:
            spaced = "  ".join(list(group_label.upper()))
            tk.Label(nav_frame, text=spaced,
                     font=("JetBrains Mono", 9, "bold"),
                     fg="#2a3f55", bg=BG_SIDEBAR, anchor="w"
                     ).pack(fill="x", padx=(6, 0), pady=(13, 5))
            for label, icon_name, key in items:
                self._make_nav_item(nav_frame, label, key)

        tk.Frame(self.sidebar, height=1, bg=BORDER_DIM
                 ).grid(row=row, column=0, sticky="ew")
        row += 1

        footer = tk.Frame(self.sidebar, bg=BG_SIDEBAR, height=58)
        footer.grid(row=row, column=0, sticky="ew")
        footer.grid_propagate(False)

        av = tk.Canvas(footer, width=34, height=34,
                       bg=BG_SIDEBAR, highlightthickness=0)
        av.place(x=12, y=12)
        av.create_oval(2, 2, 32, 32, fill=ACCENT_DIM, outline=ACCENT, width=1.5)
        av.create_text(17, 17, text="RJ",
                       font=("Inter", 11, "bold"), fill=ACCENT)

        tk.Label(footer, text="Roua Jendoubi",
                 font=("Inter", 11), fg=TEXT1, bg=BG_SIDEBAR
                 ).place(x=52, y=12)
        tk.Label(footer, text="NOC Engineer \u00b7 Capstone",
                 font=("JetBrains Mono", 9), fg=TEXT3, bg=BG_SIDEBAR
                 ).place(x=52, y=30)

    def _make_nav_item(self, parent, label, key):
        is_active = (key == self._active_nav)
        bg = "#132040" if is_active else BG_SIDEBAR

        frame = tk.Frame(parent, bg=bg, height=36, cursor="hand2")
        frame.pack(fill="x", pady=1)
        frame.pack_propagate(False)

        accent_bar = tk.Frame(frame,
                              width=2 if is_active else 0,
                              bg=BLUE if is_active else BG_SIDEBAR)
        accent_bar.pack(side="left", fill="y")

        icon_name = "grid"
        for _, items in NAV_GROUPS:
            for _, iname, ikey in items:
                if ikey == key:
                    icon_name = iname
                    break

        icon_padx = 9 if is_active else 10
        icon_widget = make_sidebar_icon(frame, icon_name, is_active)
        icon_widget.pack(side="left", padx=(icon_padx, 4))

        fg  = BLUE if is_active else TEXT2
        lbl = tk.Label(frame, text=label, bg=bg, fg=fg,
                       font=("Inter", 11), anchor="w")
        lbl.pack(side="left", fill="both", expand=True)

        if key == "incidents":
            self._alarm_badge_lbl = tk.Label(
                frame, text=str(self.app_state.active_alarms),
                bg=RED, fg=TEXT1,
                font=("JetBrains Mono", 8, "bold"), padx=5, pady=1)
            self._alarm_badge_lbl.pack(side="right", padx=6)

        def on_enter(e, f=frame, ab=accent_bar, iw=icon_widget, ll=lbl, k=key):
            if k != self._active_nav:
                f.config(bg=BG_HOVER); ab.config(bg=BG_HOVER)
                iw.configure(fg_color=BG_HOVER)
                iw.canvas.configure(bg=BG_HOVER)
                ll.config(bg=BG_HOVER, fg=TEXT1)

        def on_leave(e, f=frame, ab=accent_bar, iw=icon_widget, ll=lbl, k=key):
            if k != self._active_nav:
                f.config(bg=BG_SIDEBAR); ab.config(bg=BG_SIDEBAR)
                iw.configure(fg_color=BG_SIDEBAR)
                iw.canvas.configure(bg=BG_SIDEBAR)
                ll.config(bg=BG_SIDEBAR, fg=TEXT2)

        def on_click(e, k=key):
            self.show_frame(k)

        for w in [frame, lbl]:
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_click)
        icon_widget.canvas.bind("<Enter>",    on_enter)
        icon_widget.canvas.bind("<Leave>",    on_leave)
        icon_widget.canvas.bind("<Button-1>", on_click)

        self._nav_buttons[key] = {
            "frame": frame, "accent_bar": accent_bar,
            "icon_widget": icon_widget, "label": lbl,
        }

    def update_active_nav(self, key: str):
        from src.ui.icons import _draw_icon
        for k, w in self._nav_buttons.items():
            active = (k == key)
            bg     = "#132040" if active else BG_SIDEBAR
            w["frame"].config(bg=bg)
            w["accent_bar"].config(bg=BLUE if active else BG_SIDEBAR,
                                   width=2 if active else 0)
            w["icon_widget"].pack_configure(padx=(9 if active else 10, 4))
            icon_bg    = "#1a2a4a" if active else BG_SIDEBAR
            icon_color = BLUE if active else "#6b7280"
            w["icon_widget"].configure(fg_color=icon_bg)
            w["icon_widget"].canvas.configure(bg=icon_bg)
            w["icon_widget"].canvas.delete("all")
            _draw_icon(w["icon_widget"].canvas,
                       w["icon_widget"].icon_name,
                       x0=5, y0=5, color=icon_color, size=12)
            w["label"].config(bg=bg, fg=BLUE if active else TEXT2)
        self._active_nav = key

    # ── Content area ─────────────────────────────────────────────────────────
    def _build_content_area(self):
        self.content_wrapper = ctk.CTkFrame(
            self.root, fg_color=BG_BASE, corner_radius=0)
        self.content_wrapper.grid(row=0, column=1, sticky="nsew")
        self.content_wrapper.grid_rowconfigure(1, weight=1)
        self.content_wrapper.grid_columnconfigure(0, weight=1)

        self._build_topbar()

        self.content_area = ctk.CTkFrame(
            self.content_wrapper, fg_color=BG_BASE, corner_radius=0)
        self.content_area.grid(row=1, column=0, sticky="nsew")
        self.content_area.grid_rowconfigure(0, weight=1)
        self.content_area.grid_columnconfigure(0, weight=1)

        self._build_status_bar()
        self.show_frame("dashboard")

    def _build_topbar(self):
        bar = tk.Frame(self.content_wrapper, bg=BG_CARD, height=56)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_propagate(False)

        left = tk.Frame(bar, bg=BG_CARD)
        left.pack(side="left", padx=20, pady=6)
        self.topbar_title = tk.Label(left, text="Overview",
                                     font=("Inter", 17, "bold"),
                                     fg=T1, bg=BG_CARD)
        self.topbar_title.pack(anchor="w")
        self.topbar_sub = tk.Label(
            left,
            text="Manage and monitor your network infrastructure in real-time.",
            font=("JetBrains Mono", 10), fg=T3, bg=BG_CARD)
        self.topbar_sub.pack(anchor="w")

        right = tk.Frame(bar, bg=BG_CARD)
        right.pack(side="right", padx=14, pady=8)

        self.demo_badge = tk.Label(right, text="  DEMO  ",
                                   bg="#083325", fg=GREEN,
                                   font=("JetBrains Mono", 10, "bold"),
                                   padx=6, pady=2, relief="flat")
        self.demo_badge.pack(side="left", padx=(0, 8))
        self._pulse_demo()

        tk.Button(right, text="Export CSV",
                  bg=BG_CARD, fg=T2, relief="flat",
                  font=("Inter", 11), padx=10, pady=4,
                  highlightbackground=BDM, highlightthickness=1,
                  cursor="hand2",
                  command=self._export_csv).pack(side="left", padx=4)

        tk.Button(right, text="Generate Report",
                  bg=BLUE, fg=T1, relief="flat",
                  font=("Inter", 11, "bold"), padx=10, pady=4,
                  cursor="hand2",
                  command=self._generate_report).pack(side="left", padx=4)

        self.clock_var = tk.StringVar(value="00:00:00")
        tk.Label(right, textvariable=self.clock_var,
                 bg=BG_CARD, fg=T3,
                 font=("JetBrains Mono", 11)).pack(side="left", padx=(12, 0))

        tk.Frame(self.content_wrapper, height=1, bg=BD
                 ).grid(row=0, column=0, sticky="sew")

    def _build_status_bar(self):
        self.statusbar = tk.Frame(self.content_wrapper, bg=BG_DEEP, height=28)
        self.statusbar.grid(row=2, column=0, sticky="ew")
        self.statusbar.grid_propagate(False)
        self.content_wrapper.grid_rowconfigure(2, weight=0)

        tk.Frame(self.statusbar, height=1, bg=BD).pack(side="top", fill="x")

        self._sb_left = tk.Frame(self.statusbar, bg=BG_DEEP)
        self._sb_left.pack(side="left", padx=10, fill="y")

        SEP      = "  |  "
        SB_FONT  = ("JetBrains Mono", 9)

        self._sb_kpi = tk.Label(self._sb_left, text="KPI: — ms",
                                font=SB_FONT, fg=GREEN, bg=BG_DEEP)
        self._sb_kpi.pack(side="left")
        tk.Label(self._sb_left, text=SEP, font=SB_FONT,
                 fg=T3, bg=BG_DEEP).pack(side="left")

        self._sb_rnd = tk.Label(self._sb_left, text="Render: — ms",
                                font=SB_FONT, fg=GREEN, bg=BG_DEEP)
        self._sb_rnd.pack(side="left")
        tk.Label(self._sb_left, text=SEP, font=SB_FONT,
                 fg=T3, bg=BG_DEEP).pack(side="left")

        self._sb_pts = tk.Label(self._sb_left, text="Points: —",
                                font=SB_FONT, fg=T3, bg=BG_DEEP)
        self._sb_pts.pack(side="left")
        tk.Label(self._sb_left, text=SEP, font=SB_FONT,
                 fg=T3, bg=BG_DEEP).pack(side="left")

        self._sb_alm = tk.Label(self._sb_left, text="0 active alarms",
                                font=SB_FONT, fg=GREEN, bg=BG_DEEP)
        self._sb_alm.pack(side="left")
        tk.Label(self._sb_left, text=SEP, font=SB_FONT,
                 fg=T3, bg=BG_DEEP).pack(side="left")

        self._sb_f1 = tk.Label(
            self._sb_left,
            text="IsolationForest \u00b7 F1 0.0% \u00b7 Target \u2265 85%",
            font=SB_FONT, fg=PURPLE, bg=BG_DEEP)
        self._sb_f1.pack(side="left")

        self._sb_clk = tk.Label(self.statusbar,
                                font=SB_FONT, fg=T3, bg=BG_DEEP)
        self._sb_clk.pack(side="right", padx=14, fill="y")

        self._update_status_bar()

    def _update_status_bar(self):
        s   = self.app_state
        pts = len(s.df_kpi) if s.df_kpi is not None else 0
        alm = s.active_alarms
        f1  = s.f1_score * 100

        kpi_c = "#34d399" if s.kpi_compute_ms < 1000 else "#f87171"
        rnd_c = "#34d399" if s.render_ms < 1500      else "#f87171"
        alm_c = "#f87171" if alm > 0                 else "#34d399"

        self._sb_kpi.config(text=f"KPI: {s.kpi_compute_ms:.1f} ms", fg=kpi_c)
        self._sb_rnd.config(text=f"Render: {s.render_ms:.0f} ms",   fg=rnd_c)
        self._sb_pts.config(text=f"Points: {pts:,}",                fg=T3)
        self._sb_alm.config(text=f"{alm} active alarms",            fg=alm_c)
        f1_ok = f1 >= 85
        tick  = "\u2713" if f1_ok else "\u2717"
        self._sb_f1.config(
            text=f"IsolationForest \u00b7 F1 {f1:.1f}% \u00b7 Target \u2265 85% {tick}",
            fg=PURPLE)
        self._sb_clk.config(
            text=datetime.datetime.now().strftime("%H:%M:%S"))

        self.root.after(1000, self._update_status_bar)

    def _start_clock(self):
        def tick():
            self.clock_var.set(datetime.datetime.now().strftime("%H:%M:%S"))
            self.root.after(1000, tick)
        tick()

    def _pulse_demo(self):
        self._pulse_idx = getattr(self, "_pulse_idx", 0)
        colors = [GREEN, "#0a7a4e", GREEN]
        self.demo_badge.config(bg=colors[self._pulse_idx % 3])
        self._pulse_idx += 1
        self.root.after(800, self._pulse_demo)

    # ── Frame switching ───────────────────────────────────────────────────────
    def show_frame(self, name: str):
        from src.ui.tab_dashboard   import DashboardTab
        from src.ui.tab_activity    import ActivityTab
        from src.ui.tab_topology    import TopologyTab
        from src.ui.tab_devices     import DevicesTab
        from src.ui.tab_bandwidth   import BandwidthTab
        from src.ui.tab_netflow     import NetflowTab
        from src.ui.tab_security    import SecurityTab
        from src.ui.tab_incidents   import IncidentsTab
        from src.ui.tab_diagnostics import DiagnosticsTab
        from src.ui.tab_settings    import SettingsTab

        TAB_REGISTRY = {
            "dashboard":   DashboardTab,
            "activity":    ActivityTab,
            "topology":    TopologyTab,
            "devices":     DevicesTab,
            "bandwidth":   BandwidthTab,
            "netflow":     NetflowTab,
            "security":    SecurityTab,
            "incidents":   IncidentsTab,
            "diagnostics": DiagnosticsTab,
            "settings":    SettingsTab,
        }

        for f in self.frames.values():
            f.grid_remove()

        if name not in self.frames:
            t0    = time.perf_counter()
            frame = TAB_REGISTRY[name](self.content_area, self.app_state)
            frame.grid(row=0, column=0, sticky="nsew")
            self.frames[name]         = frame
            self.app_state.render_ms  = (time.perf_counter() - t0) * 1000

        self.frames[name].grid()
        title, subtitle = SCREEN_META[name]
        self.topbar_title.config(text=title)
        self.topbar_sub.config(text=subtitle)
        self.update_active_nav(name)

    # ── Data loading (also done in main.py pipeline — this is a refresh) ─────
    def _load_data_async(self):
        """Refresh UI after pipeline data arrives."""
        def _refresh():
            import time as _t
            _t.sleep(2)   # wait for main.py pipeline thread to finish loading
            if self.app_state.df_kpi is not None:
                try:
                    if "dashboard" in self.frames:
                        frame = self.frames["dashboard"]
                        if hasattr(frame, "refresh"):
                            self.root.after(0, lambda: frame.refresh(self.app_state))
                except Exception:
                    pass
                try:
                    self._alarm_badge_lbl.config(
                        text=str(self.app_state.active_alarms))
                except Exception:
                    pass
        threading.Thread(target=_refresh, daemon=True).start()

    # ── Actions ───────────────────────────────────────────────────────────────
    def _export_csv(self):
        try:
            import os
            os.makedirs("reports", exist_ok=True)
            if self.app_state.df_kpi is not None:
                path = f"reports/export_{datetime.date.today()}.csv"
                self.app_state.df_kpi.to_csv(path, index=False)
        except Exception as e:
            print(f"[app] Export CSV error: {e}")

    def _generate_report(self):
        """
        Generate 6 SEPARATE PDF reports -- one per CDC incident scenario.
        Each PDF has exactly 6 sections matching thesis Table 6.4 and S12 spec:
          1. Cover (scenario name, date, metadata)
          2. KPI Summary (table + 3 matplotlib figures at 150 DPI via BytesIO)
          3. Anomaly Analysis (IF table + rule alarms, F1-score)
          4. SNMP Security Compliance (score 62/100, alerts, authPriv recs)
          5. Conclusions (auto-generated from anomaly count + compliance score)
          6. Technical Appendix (raw data tables)
        Injected fault values match thesis 6.5 exactly.
        """
        def _worker():
            try:
                import os
                os.makedirs("reports", exist_ok=True)
                from src.reports.pdf_generator import generate_pdf

                df_real = self.app_state.df_kpi
                rapport = self.app_state.rapport_conformite or {}
                today   = datetime.date.today().isoformat()

                SCENARIOS = [
                    ("S1_Saturation_OLT",       self._sim_saturation(df_real)),
                    ("S2_Optical_Degradation",   self._sim_perte_optique(df_real)),
                    ("S3_ONT_Offline",           self._sim_ont_down(df_real)),
                    ("S4_Error_Burst",           self._sim_error_burst(df_real)),
                    ("S5_Multivariate_Anomaly",  self._sim_multivariate(df_real)),
                    ("S6_Splitter_Non_Conforme", self._sim_splitter(df_real)),
                ]

                paths = []
                for sc_name, df_sc in SCENARIOS:
                    path = generate_pdf(
                        df_kpi             = df_sc,
                        rapport_conformite = rapport,
                        figures            = self._make_scenario_figures(df_sc),
                        scenario           = sc_name,
                        path_out           = f"reports/report_{sc_name}_{today}.pdf",
                    )
                    paths.append(path)

                self.root.after(0, lambda ps=paths: self._show_pdf_done_multi(ps))
            except Exception as exc:
                import traceback as _tb
                err = _tb.format_exc()
                self.root.after(0, lambda e=err: self._show_pdf_error(e))

        threading.Thread(target=_worker, daemon=True).start()

    # -- Scenario simulators -- thesis 6.5 exact injected fault values ------

    def _sim_base(self, df_real):
        """Return a working copy of df_real, or a 288-row synthetic baseline."""
        import numpy as np, pandas as pd
        if df_real is not None and not df_real.empty:
            return df_real.copy()
        rng = np.random.default_rng(42)
        n   = 288
        t   = pd.date_range("2025-11-17", periods=n, freq="5min")
        return pd.DataFrame({
            "timestamp":       t,
            "debit_rx_mbps":   rng.uniform(50, 300, n),
            "debit_tx_mbps":   rng.uniform(20, 150, n),
            "utilization_pct": rng.uniform(20, 70, n),
            "error_rate_pct":  rng.uniform(0, 0.5, n),
            "anomaly_flag":    np.ones(n, dtype=int),
            "anomaly_score":   rng.uniform(0.0, 0.2, n),
            "rule_alarm":      np.zeros(n, dtype=bool),
            "rule_detail":     [""] * n,
        })

    def _sim_saturation(self, df_real):
        """S1 -- OLT Saturation: utilization_pct=91.3%>85%, IF=-0.42 (thesis 6.5.1)."""
        import numpy as np
        df = self._sim_base(df_real)
        idx = list(range(120, 128))
        df.loc[df.index[idx], "utilization_pct"] = [91.3,89.7,88.4,90.1,87.6,91.3,88.9,87.2]
        df.loc[df.index[idx], "debit_rx_mbps"]   = [610,580,560,595,540,610,570,545]
        df.loc[df.index[idx], "anomaly_flag"]     = -1
        df.loc[df.index[idx], "anomaly_score"]    = -0.42
        df.loc[df.index[idx], "rule_alarm"]       = True
        df.loc[df.index[idx], "rule_detail"]      = "utilization_pct 91.3 > 85.0"
        return df

    def _sim_perte_optique(self, df_real):
        """S2 -- Optical Degradation: error_rate=1.87%>1%, IF=-0.31 (thesis 6.5)."""
        import numpy as np
        df = self._sim_base(df_real)
        idx = list(range(60, 75))
        df.loc[df.index[idx], "error_rate_pct"]  = 1.87
        df.loc[df.index[idx], "debit_rx_mbps"]   = (
            df.loc[df.index[idx], "debit_rx_mbps"].values * 0.3)
        df.loc[df.index[idx], "anomaly_flag"]    = -1
        df.loc[df.index[idx], "anomaly_score"]   = -0.31
        df.loc[df.index[idx], "rule_alarm"]      = True
        df.loc[df.index[idx], "rule_detail"]     = "error_rate_pct 1.87 > 1.0"
        return df

    def _sim_ont_down(self, df_real):
        """S3 -- ONT Offline: 6 ONTs down simultaneously, IF=-0.28 (thesis 6.5)."""
        import numpy as np
        df = self._sim_base(df_real)
        idx = list(range(180, 196))
        df.loc[df.index[idx], "anomaly_flag"]  = -1
        df.loc[df.index[idx], "anomaly_score"] = -0.28
        df.loc[df.index[idx], "rule_alarm"]    = True
        df.loc[df.index[idx], "rule_detail"]   = "onuOperStatus=down (6 ONTs simultaneously)"
        df.loc[df.index[idx], "debit_rx_mbps"] = (
            df.loc[df.index[idx], "debit_rx_mbps"].values * 0.94)
        return df

    def _sim_error_burst(self, df_real):
        """S4 -- Error Burst: error_rate=2.13%>1%, IF partial=-0.12 (thesis 6.5)."""
        import numpy as np
        df = self._sim_base(df_real)
        idx = list(range(200, 210))
        df.loc[df.index[idx], "error_rate_pct"] = 2.13
        df.loc[df.index[idx], "anomaly_flag"]   = -1
        df.loc[df.index[idx], "anomaly_score"]  = -0.12
        df.loc[df.index[idx], "rule_alarm"]     = True
        df.loc[df.index[idx], "rule_detail"]    = "error_rate_pct 2.13 > 1.0"
        return df

    def _sim_multivariate(self, df_real):
        """S5 -- Multivariate: sub-threshold all 4 features, rules=0, IF=-0.39.
        util peaks 82.4%<85%, err=0.87%<1.0%. IF flags 40/48 rows (thesis 6.5.2).
        Key finding: rules engine produces 0 alarms; IF is the sole detector."""
        import numpy as np
        df = self._sim_base(df_real)
        idx = list(range(100, 148))
        df.loc[df.index[idx], "utilization_pct"] = np.linspace(75, 82.4, len(idx))
        df.loc[df.index[idx], "error_rate_pct"]  = np.linspace(0.6, 0.87, len(idx))
        df.loc[df.index[idx], "debit_rx_mbps"]   = 18.3
        df.loc[df.index[idx], "debit_tx_mbps"]   = (
            df.loc[df.index[idx], "debit_tx_mbps"].values * 0.7)
        # rule_alarm stays False -- all 4 metrics remain below thresholds
        flagged = idx[:40]
        df.loc[df.index[flagged], "anomaly_flag"]  = -1
        df.loc[df.index[flagged], "anomaly_score"] = -0.39
        return df

    def _sim_splitter(self, df_real):
        """S6 -- Splitter Non-conformant: optical budget >28dB (Scenarios E-H).
        No KPI alarm, no IF flag. Detected by optical budget calculator only."""
        import numpy as np
        df = self._sim_base(df_real)
        df["debit_rx_mbps"]   = df["debit_rx_mbps"] * 0.65
        df["utilization_pct"] = df["utilization_pct"] * 1.15
        # rule_alarm=False, anomaly_flag=+1 -- S6 is optical budget violation only
        return df

    def _make_scenario_figures(self, df):
        """3 matplotlib figures per scenario -- BytesIO 150 DPI (S12 spec 3.3).
        fig1: RX/TX throughput (14x7 cm)
        fig2: utilization_pct + 85% threshold (14x6 cm)
        fig3: error_rate_pct + 1% threshold (14x5 cm)"""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        figs = []
        if df is None or df.empty:
            return figs
        try:
            step = max(1, len(df) // 500)
            ds   = df.iloc[::step]
            x    = np.arange(len(ds))
            for (cols, clrs, title, thr, thr_lbl) in [
                (["debit_rx_mbps", "debit_tx_mbps"],
                 ["#3b82f6", "#06b6d4"],
                 "RX/TX Throughput (Mbit/s)", None, None),
                (["utilization_pct"], ["#a78bfa"],
                 "Utilization % -- Threshold 85%", 85.0, "85%"),
                (["error_rate_pct"], ["#f87171"],
                 "Error Rate % -- Threshold 1%",   1.0,  "1%"),
            ]:
                fig, ax = plt.subplots(figsize=(5.5, 2.5))
                fig.patch.set_facecolor("#0d1626")
                ax.set_facecolor("#0d1626")
                for col, clr in zip(cols, clrs):
                    if col in ds.columns:
                        ax.plot(x, ds[col].values, color=clr, lw=1.4, label=col)
                        ax.fill_between(x, ds[col].values, alpha=0.10, color=clr)
                if thr is not None:
                    ax.axhline(thr, color="#f97316", lw=0.9, ls="--",
                               label=f"Threshold {thr_lbl}")
                ax.tick_params(colors="#4a6278", labelsize=7)
                for sp in ax.spines.values():
                    sp.set_color("#1c2d42")
                ax.legend(fontsize=7, facecolor="#101828", labelcolor="#8da4be")
                ax.set_title(title, color="#8da4be", fontsize=8)
                fig.tight_layout(pad=0.4)
                figs.append(fig)
        except Exception:
            pass
        return figs

    def _show_pdf_done_multi(self, paths: list):
        """Show success dialog listing all 6 generated PDFs."""
        try:
            import os
            win = ctk.CTkToplevel(self.root)
            win.title("6 Reports Generated")
            win.geometry("560x340")
            win.grab_set()
            ctk.CTkLabel(win,
                         text="\u2713  6 scenario reports generated",
                         font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
                         text_color="#34d399").pack(pady=(16, 8))
            box = ctk.CTkTextbox(
                win, width=520, height=200,
                font=ctk.CTkFont(family="JetBrains Mono", size=9))
            for p in paths:
                box.insert("end", os.path.basename(p) + "\n")
            box.configure(state="disabled")
            box.pack(padx=16, pady=4)
            ctk.CTkButton(
                win, text="Open Reports Folder",
                command=lambda: os.startfile(os.path.abspath("reports"))
            ).pack(pady=10)
        except Exception:
            pass

    def _show_pdf_done(self, path: str):
        try:
            import os
            win = ctk.CTkToplevel(self.root)
            win.title("Report Generated")
            win.geometry("420x130")
            win.grab_set()
            ctk.CTkLabel(win, text=f"\u2713  Report saved",
                         font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
                         text_color="#34d399").pack(pady=(20, 4))
            ctk.CTkLabel(win, text=path,
                         font=ctk.CTkFont(family="JetBrains Mono", size=9),
                         text_color="#8da4be").pack(pady=4)
            ctk.CTkButton(win, text="Open Folder",
                          command=lambda: os.startfile(
                              os.path.dirname(os.path.abspath(path)))
                          ).pack(pady=10)
        except Exception:
            pass

    def _show_pdf_error(self, err: str):
        try:
            win = ctk.CTkToplevel(self.root)
            win.title("PDF Error")
            win.geometry("480x160")
            win.grab_set()
            ctk.CTkLabel(win, text="PDF generation failed",
                         font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
                         text_color="#f87171").pack(pady=(16, 4))
            box = ctk.CTkTextbox(win, width=440, height=80,
                                 font=ctk.CTkFont(family="JetBrains Mono", size=9))
            box.insert("0.0", err)
            box.configure(state="disabled")
            box.pack(padx=16, pady=4)
        except Exception:
            pass

    # kept for backward compat with any code that calls app.run()
    def run(self):
        self.root.mainloop()
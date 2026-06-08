"""
tab_topology.py -- Network Topology Tab
Pure tk.Canvas. Core-OLT at centre, 4 splitters in quadrants,
100 ONTs scattered radially. No networkx required.
"""
from __future__ import annotations

import math
import random
import tkinter as tk
from typing import Dict, List, Optional, Tuple

from src.ui.theme import (
    BG_BASE, BG_CARD, ACCENT, CYAN,
    TEXT1, TEXT2, TEXT3, BORDER_DIM,
)

# ── Colour palette ────────────────────────────────────────────────────────────
C_BG        = "#070d1a"
C_GRID      = "#0d1630"
C_OLT_FILL  = "#0a1d50"
C_OLT_BD    = "#4f8ef7"
C_SP_FILL   = "#1a1200"
C_SP_BD     = "#fbbf24"
C_LNK_OS    = "#2a5090"   # OLT→Splitter link
C_LNK_SO    = "#183060"   # Splitter→ONT link
C_LNK_DN    = "#2a1a1a"   # down link
C_UP        = "#10b981"
C_DOWN      = "#ef4444"
C_ANOM      = "#f97316"
C_RULE      = "#a78bfa"
C_T_OLT     = "#93c5fd"
C_T_SP      = "#fde68a"
C_T_LBL     = "#4a6a8a"
C_T_HI      = "#c5d8f0"
C_POPUP     = "#0a1428"


# ── Node factory ─────────────────────────────────────────────────────────────

def _node(x, y, ntype, label, sub="", status="up", anom=False, rule=False):
    return dict(x=float(x), y=float(y), ntype=ntype, label=label, sub=sub,
                status=status, anom=anom, rule=rule)


# ── Tab ───────────────────────────────────────────────────────────────────────

class TopologyTab(tk.Frame):

    def __init__(self, parent, app_state):
        super().__init__(parent, bg=C_BG)
        self.app_state = app_state

        self._filter    = "All"
        self._nodes: Dict[str, dict] = {}
        self._edges: List[Tuple[str, str]] = []
        self._node_ids: List[str] = []
        self._drag      = None
        self._drag_ox   = 0.0
        self._drag_oy   = 0.0
        self._pan_x     = 600.0   # safe default -- updated on first real size
        self._pan_y     = 360.0
        self._pan_sx    = 0
        self._pan_sy    = 0
        self._zoom      = 0.80
        self._anim      = None
        self._popups: List[int] = []
        self._fbtn: Dict[str, tk.Button] = {}

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._make_toolbar()
        self._make_canvas()
        self._make_graph()

        # Start rendering immediately
        self._schedule()

        # Re-centre once the window is fully laid out
        self.after(200, self._fit)

    # ── Toolbar ───────────────────────────────────────────────────────────────

    def _make_toolbar(self):
        bar = tk.Frame(self, bg=BG_BASE, height=44)
        bar.grid(row=0, column=0, sticky="ew")

        def _b(text, cmd):
            b = tk.Button(bar, text=text, command=cmd,
                          bg=BG_CARD, fg=TEXT2, relief="flat",
                          font=("Inter", 9), padx=10, pady=5, bd=0,
                          cursor="hand2",
                          highlightbackground=BORDER_DIM, highlightthickness=1)
            b.pack(side="left", padx=3, pady=8)
            return b

        _b("Save",          self._save)
        _b("Fullscreen",    self._toggle_fs)
        _b("Reset Layout",  self._reset)

        tk.Label(bar, text="Filter:", font=("JetBrains Mono", 8),
                 fg=TEXT3, bg=BG_BASE).pack(side="left", padx=(14, 3))

        for opt in ("All", "Anomaly", "DOWN only"):
            b = tk.Button(bar, text=opt,
                          bg=ACCENT if opt == "All" else BG_CARD,
                          fg=TEXT1 if opt == "All" else TEXT2,
                          relief="flat", font=("JetBrains Mono", 8),
                          padx=8, pady=5, bd=0, cursor="hand2",
                          highlightbackground=BORDER_DIM, highlightthickness=1,
                          command=lambda o=opt: self._set_filter(o))
            b.pack(side="left", padx=2, pady=8)
            self._fbtn[opt] = b

        # Right side: legend + LIVE + count
        leg = tk.Frame(bar, bg=BG_BASE)
        leg.pack(side="right", padx=10)
        for col, lbl in [(C_OLT_BD, "OLT"), (C_SP_BD, "Splitter"),
                          (C_UP, "UP"), (C_DOWN, "DOWN"),
                          (C_ANOM, "Anomaly"), (C_RULE, "Rule")]:
            tk.Label(leg, text="\u25a0", fg=col, bg=BG_BASE,
                     font=("Inter", 9)).pack(side="left")
            tk.Label(leg, text=f" {lbl}  ", fg=TEXT3, bg=BG_BASE,
                     font=("JetBrains Mono", 7)).pack(side="left")

        pill = tk.Frame(bar, bg="#091a09",
                        highlightbackground=C_UP, highlightthickness=1)
        pill.pack(side="right", padx=6, pady=11)
        tk.Label(pill, text="\u25cf LIVE", fg=C_UP, bg="#091a09",
                 font=("JetBrains Mono", 7, "bold")).pack(padx=6, pady=2)

        tk.Label(bar, text="100 devices \u00b7 4 splitters",
                 font=("JetBrains Mono", 8), fg=CYAN, bg=BG_BASE
                 ).pack(side="right", padx=6)

    # ── Canvas ────────────────────────────────────────────────────────────────

    def _make_canvas(self):
        card = tk.Frame(self, bg=BG_CARD,
                        highlightbackground=BORDER_DIM, highlightthickness=1)
        card.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        card.grid_rowconfigure(0, weight=1)
        card.grid_columnconfigure(0, weight=1)

        self._cv = tk.Canvas(card, bg=C_BG, highlightthickness=0,
                             cursor="crosshair")
        self._cv.grid(row=0, column=0, sticky="nsew")

        self._cv.bind("<ButtonPress-1>",   self._press)
        self._cv.bind("<B1-Motion>",       self._drag_move)
        self._cv.bind("<ButtonRelease-1>", self._release)
        self._cv.bind("<MouseWheel>",      self._wheel)

    # ── Graph data ────────────────────────────────────────────────────────────

    def _make_graph(self):
        df_ont = self.app_state.df_ont
        df_kpi = self.app_state.df_kpi

        # ONT id list
        if df_ont is not None and "ont_id" in df_ont.columns:
            oids = [str(x) for x in df_ont["ont_id"].unique()[:100]]
        else:
            oids = [f"ONT_{101+i}" for i in range(100)]

        # Status per ONT
        smap: Dict[str, str] = {}
        if df_ont is not None and "onuOperStatus" in df_ont.columns:
            last = df_ont.sort_values("timestamp").groupby("ont_id").last()
            for oid, row in last.iterrows():
                s = str(row["onuOperStatus"]).strip().lower()
                smap[str(oid)] = "down" if s in ("0","down","inactive","disabled") else "up"

        # Anomaly / rule sets  
        anom: set = set()
        rule: set = set()
        if df_kpi is not None:
            if "anomaly_flag" in df_kpi.columns:
                n = int((df_kpi["anomaly_flag"] == -1).sum())
                for i in range(min(n // 20, 18)):
                    if i < len(oids): anom.add(oids[i])
            if "rule_alarm" in df_kpi.columns:
                n = int(df_kpi["rule_alarm"].sum())
                for i in range(min(n // 35, 8)):
                    if i+20 < len(oids): rule.add(oids[i+20])

        self._nodes = {}
        self._edges = []

        # OLT at world origin (0, 0)
        self._nodes["Core-OLT"] = _node(0, 0, "olt", "Core-OLT", "10.0.0.1")

        # 4 splitters in quadrant positions
        sp_pos = [
            ("SP-1 \u00b7 1:32", -290, -160),
            ("SP-2 \u00b7 1:32",  270, -190),
            ("SP-3 \u00b7 1:32",  380,   90),
            ("SP-4 \u00b7 1:32", -255,  220),
        ]
        for sp_id, sx, sy in sp_pos:
            self._nodes[sp_id] = _node(sx, sy, "splitter", sp_id)
            self._edges.append(("Core-OLT", sp_id))

        # ONTs: 25 per splitter, radially spread away from OLT
        rng = random.Random(42)
        sp_list = [s[0] for s in sp_pos]
        for idx, oid in enumerate(oids[:100]):
            sp_id = sp_list[idx % 4]
            sp    = self._nodes[sp_id]
            sx, sy = sp["x"], sp["y"]

            # Radial direction away from OLT centre
            base_angle = math.atan2(sy, sx)
            spread     = math.radians(195)
            j          = idx // 4          # 0..24 within this splitter
            t          = (j / 24.0) - 0.5  # -0.5 .. +0.5
            angle      = base_angle + t * spread + rng.uniform(-0.10, 0.10)

            # 4 rings of depth
            rings = [145, 210, 275, 335]
            r     = rings[min(j // 7, 3)] + rng.uniform(-18, 18)

            ox = sx + r * math.cos(angle)
            oy = sy + r * math.sin(angle)

            st = smap.get(oid, "up")
            self._nodes[oid] = _node(ox, oy, "ont", oid,
                                     status=st,
                                     anom=oid in anom,
                                     rule=oid in rule)
            self._edges.append((sp_id, oid))

        self._node_ids = list(self._nodes.keys())

    # ── Fit / centre ──────────────────────────────────────────────────────────

    def _fit(self):
        W = self._cv.winfo_width()
        H = self._cv.winfo_height()
        if W < 20:
            # Canvas not ready yet -- try again shortly
            self.after(100, self._fit)
            return
        xs = [nd["x"] for nd in self._nodes.values()]
        ys = [nd["y"] for nd in self._nodes.values()]
        pad = 70
        span_x = max(xs) - min(xs) + pad * 2
        span_y = max(ys) - min(ys) + pad * 2
        self._zoom  = min(W / max(span_x, 1), H / max(span_y, 1))
        # Centre the bounding box
        cx = (max(xs) + min(xs)) / 2
        cy = (max(ys) + min(ys)) / 2
        self._pan_x = W / 2 - cx * self._zoom
        self._pan_y = H / 2 - cy * self._zoom

    # ── Render ────────────────────────────────────────────────────────────────

    def _schedule(self):
        self._render()
        self._anim = self.after(60, self._schedule)

    def _w2s(self, x, y):
        return x * self._zoom + self._pan_x, y * self._zoom + self._pan_y

    def _render(self):
        cv = self._cv
        cv.delete("all")
        W = cv.winfo_width()  or 1
        H = cv.winfo_height() or 1

        # Background dot grid
        step = 38
        for gx in range(0, W + step, step):
            for gy in range(0, H + step, step):
                cv.create_oval(gx-1, gy-1, gx+1, gy+1,
                               fill=C_GRID, outline="")

        # Edges
        for a, b in self._edges:
            if not self._visible(b):
                continue
            na, nb = self._nodes[a], self._nodes[b]
            ax, ay = self._w2s(na["x"], na["y"])
            bx, by = self._w2s(nb["x"], nb["y"])
            olt_sp = na["ntype"] == "olt"
            down   = nb.get("status") == "down"
            col    = C_LNK_DN if down else (C_LNK_OS if olt_sp else C_LNK_SO)
            lw     = 1.4 if olt_sp else 0.7
            kw     = {"fill": col, "width": lw}
            if down:
                kw["dash"] = (3, 4)
            cv.create_line(ax, ay, bx, by, **kw)

        # ONTs (bottom layer)
        for nid in self._node_ids:
            nd = self._nodes[nid]
            if nd["ntype"] != "ont" or not self._visible(nid):
                continue
            x, y = self._w2s(nd["x"], nd["y"])
            self._draw_ont(cv, x, y, nd)

        # Splitters (middle layer)
        for nid in self._node_ids:
            nd = self._nodes[nid]
            if nd["ntype"] != "splitter":
                continue
            x, y = self._w2s(nd["x"], nd["y"])
            self._draw_splitter(cv, x, y, nd)

        # OLT (top layer)
        nd = self._nodes.get("Core-OLT")
        if nd:
            x, y = self._w2s(nd["x"], nd["y"])
            self._draw_olt(cv, x, y)

    def _draw_olt(self, cv, x, y):
        for r, col in [(50, "#091840"), (38, "#0e2260"), (28, "#1a3a8a")]:
            cv.create_oval(x-r, y-r, x+r, y+r, outline=col, fill="", width=1)
        w, h = 82, 34
        cv.create_rectangle(x-w//2, y-h//2, x+w//2, y+h//2,
                             fill=C_OLT_FILL, outline=C_OLT_BD, width=2)
        cv.create_text(x, y-5, text="Core-OLT",
                       fill=C_T_OLT, font=("JetBrains Mono", 9, "bold"))
        cv.create_text(x, y+8, text="10.0.0.1",
                       fill=C_T_LBL, font=("JetBrains Mono", 7))

    def _draw_splitter(self, cv, x, y, nd):
        for r, col in [(28, "#2a1c00"), (20, "#4a3000")]:
            cv.create_oval(x-r, y-r, x+r, y+r, outline=col, fill="", width=1)
        w, h = 74, 26
        cv.create_rectangle(x-w//2, y-h//2, x+w//2, y+h//2,
                             fill=C_SP_FILL, outline=C_SP_BD, width=1.5)
        cv.create_text(x, y, text=nd["label"],
                       fill=C_T_SP, font=("JetBrains Mono", 7, "bold"))

    def _draw_ont(self, cv, x, y, nd):
        col = (C_ANOM if nd["anom"] else
               C_RULE if nd["rule"] else
               C_DOWN if nd["status"] == "down" else C_UP)
        s = 6
        if nd["anom"] or nd["rule"] or nd["status"] == "down":
            cv.create_rectangle(x-s-3, y-s-3, x+s+3, y+s+3,
                                 outline=col, fill="", width=1)
        cv.create_rectangle(x-s, y-s, x+s, y+s,
                             outline=col, fill="", width=1.5)
        if nd["anom"] or nd["rule"]:
            cv.create_rectangle(x-s+2, y-s+2, x+s-2, y+s-2,
                                 fill=col, outline="")
        if nd["anom"] or nd["rule"] or nd["status"] == "down" or self._filter != "All":
            cv.create_text(x, y+s+8, text=nd["label"],
                           fill=C_T_LBL, font=("JetBrains Mono", 6))

    # ── Visibility filter ─────────────────────────────────────────────────────

    def _visible(self, nid: str) -> bool:
        nd = self._nodes.get(nid, {})
        nt = nd.get("ntype", "")
        if self._filter == "All":
            return True
        if nt in ("olt", "splitter"):
            return True
        if self._filter == "Anomaly":
            return nd.get("anom") or nd.get("rule")
        if self._filter == "DOWN only":
            return nd.get("status") == "down"
        return True

    # ── Mouse interaction ─────────────────────────────────────────────────────

    def _hittest(self, sx, sy) -> Optional[str]:
        best, bd = None, 30
        for nid, nd in self._nodes.items():
            nx, ny = self._w2s(nd["x"], nd["y"])
            d = math.hypot(sx - nx, sy - ny)
            r = 44 if nd["ntype"] == "olt" else (36 if nd["ntype"] == "splitter" else 12)
            if d < r and d < bd:
                best, bd = nid, d
        return best

    def _press(self, e):
        hit = self._hittest(e.x, e.y)
        if hit:
            nd = self._nodes[hit]
            sx, sy = self._w2s(nd["x"], nd["y"])
            self._drag      = hit
            self._drag_ox   = e.x - sx
            self._drag_oy   = e.y - sy
            self._popup(hit)
        else:
            self._drag   = None
            self._pan_sx = e.x - int(self._pan_x)
            self._pan_sy = e.y - int(self._pan_y)

    def _drag_move(self, e):
        if self._drag:
            nd = self._nodes[self._drag]
            nd["x"] = (e.x - self._drag_ox - self._pan_x) / self._zoom
            nd["y"] = (e.y - self._drag_oy - self._pan_y) / self._zoom
        else:
            self._pan_x = float(e.x - self._pan_sx)
            self._pan_y = float(e.y - self._pan_sy)

    def _release(self, _e):
        self._drag = None

    def _wheel(self, e):
        f = 1.12 if e.delta > 0 else 0.89
        self._zoom = max(0.2, min(5.0, self._zoom * f))

    # ── Popup ─────────────────────────────────────────────────────────────────

    def _popup(self, nid: str):
        cv = self._cv
        for cid in self._popups:
            try: cv.delete(cid)
            except Exception: pass
        self._popups = []

        nd  = self._nodes[nid]
        col = (C_OLT_BD if nd["ntype"] == "olt" else
               C_SP_BD  if nd["ntype"] == "splitter" else
               C_ANOM   if nd["anom"] else
               C_RULE   if nd["rule"] else
               C_DOWN   if nd["status"] == "down" else C_UP)

        lines = [nd["label"]]
        if nd.get("sub"): lines.append(nd["sub"])
        lines += [f"Type:   {nd['ntype'].upper()}",
                  f"Status: {nd['status'].upper()}"]
        if nd.get("anom"): lines.append("AI Anomaly detected")
        if nd.get("rule"): lines.append("Rule alarm triggered")

        x, y = self._w2s(nd["x"], nd["y"])
        W    = cv.winfo_width() or 900
        pw, lh = 150, 15
        ph   = len(lines) * lh + 12
        px   = min(x + 18, W - pw - 6)
        py   = y - ph - 8

        ids = []
        ids.append(cv.create_rectangle(px, py, px+pw, py+ph,
                                        fill=C_POPUP, outline=col, width=1))
        for i, ln in enumerate(lines):
            ids.append(cv.create_text(
                px+8, py+7+i*lh, text=ln, anchor="w",
                fill=col if i == 0 else C_T_HI,
                font=("JetBrains Mono", 7, "bold" if i == 0 else "normal")))
        self._popups = ids
        self.after(3500, self._clear_popup)

    def _clear_popup(self):
        for cid in self._popups:
            try: self._cv.delete(cid)
            except Exception: pass
        self._popups = []

    # ── Filter ────────────────────────────────────────────────────────────────

    def _set_filter(self, opt: str):
        self._filter = opt
        for o, b in self._fbtn.items():
            b.configure(bg=ACCENT if o == opt else BG_CARD,
                        fg=TEXT1  if o == opt else TEXT2)

    # ── Toolbar actions ───────────────────────────────────────────────────────

    def _save(self):
        try:
            import os
            from PIL import ImageGrab
            os.makedirs("reports", exist_ok=True)
            x0, y0 = self._cv.winfo_rootx(), self._cv.winfo_rooty()
            ImageGrab.grab((x0, y0,
                             x0 + self._cv.winfo_width(),
                             y0 + self._cv.winfo_height())
                           ).save("reports/topology.png")
        except Exception:
            pass

    def _toggle_fs(self):
        tl = self.winfo_toplevel()
        tl.attributes("-fullscreen", not tl.attributes("-fullscreen"))

    def _reset(self):
        self._make_graph()
        self._fit()

    # ── Refresh (called by app when pipeline completes) ───────────────────────

    def refresh(self, app_state):
        self.app_state = app_state
        if self._anim:
            self.after_cancel(self._anim)
        self._make_graph()
        self._fit()
        self._schedule()
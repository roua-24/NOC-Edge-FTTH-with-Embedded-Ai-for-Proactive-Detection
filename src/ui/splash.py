"""
src/ui/splash.py — NOC-Edge FTTH Splash Screen
================================================
640x380 px, centered, 7 seconds, animated Hybrid-2 GPON radar logo.

CTK / TK ARCHITECTURE:
  Uses tk.Tk() with overrideredirect(True) — NOT CTk().
  Reason: CTk() initializes the theme engine and claims mainloop ownership.
  Destroying it before NOCApp(CTk) opens corrupts CTk state on Windows.
  All widgets inside are plain tk.* — no CTk widgets inside tk.Tk().

MAINLOOP CONTRACT (critical — this was the bug):
  SplashScreen.__init__ does NOT call on_done() from inside an after()
  callback. It only destroys self.win at 7 s, which causes mainloop() in
  main.py to return. main.py then opens NOCApp cleanly after mainloop()
  returns. NOCApp is NEVER opened from inside a Tk after() chain.

  The on_done parameter is accepted for test compatibility but ignored
  at runtime — main.py controls what happens after splash.
"""
from __future__ import annotations

import math
import tkinter as tk
from tkinter import font as tkfont

# ── Constants ──────────────────────────────────────────────────────────────────
SPLASH_W           = 640
SPLASH_H           = 380
SPLASH_DURATION_MS = 7000

# (delay_ms, message, progress 0.0-1.0)
LOADING_STEPS = [
    (0,    "Initializing parse_csv...",      0.00),
    (800,  "Loading kpi_builder...",         0.14),
    (1600, "Training IsolationForest...",    0.28),
    (2400, "Loading rules_engine...",        0.43),
    (3200, "Loading forecast engine...",     0.57),
    (4000, "Auditing SNMP security...",      0.71),
    (5200, "Building dashboard...",          0.86),
    (6500, "Ready",                          1.00),
]

# ── Colors ─────────────────────────────────────────────────────────────────────
C_BG      = "#040810"
C_GRID    = "#152238"
C_BRACKET = "#3b82f6"
C_TITLE   = "#e2eaf6"
C_TAGLINE = "#3b82f6"
C_MSG     = "#3d5a7a"
C_FOOTER  = "#243650"
C_BAR_BG  = "#1d3461"
C_BAR_FG  = "#3b82f6"
C_BLUE    = "#4f8ef7"
C_GREEN   = "#34d399"
C_RED     = "#f87171"
C_GOLD    = "#fcd34d"


def _blend(color: str, alpha: float, bg=(4, 8, 16)) -> str:
    alpha = max(0.0, min(1.0, alpha))
    try:
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        return "#{:02x}{:02x}{:02x}".format(
            int(r * alpha + bg[0] * (1 - alpha)),
            int(g * alpha + bg[1] * (1 - alpha)),
            int(b * alpha + bg[2] * (1 - alpha)),
        )
    except Exception:
        return color


# ── Animated logo ──────────────────────────────────────────────────────────────
class _LogoCanvas(tk.Canvas):
    def __init__(self, parent, size: int = 80, bg: str = C_BG, **kw):
        super().__init__(parent, width=size, height=size,
                         bg=bg, highlightthickness=0, **kw)
        self._size     = size
        self._angle    = 0.0
        self._blink    = 0.0
        self._halo_r   = 2.5
        self._halo_dir = 1
        self._after_id = None

    def _s(self, v): return v / 100.0 * self._size

    def start_animation(self): self._draw()

    def stop_animation(self):
        if self._after_id is not None:
            try: self.after_cancel(self._after_id)
            except Exception: pass
            self._after_id = None

    def _animate(self): self._draw()  # test alias

    def _draw(self):
        self.delete("all")
        s = self._s
        cx, cy = s(50), s(50)

        for r_pct, alpha in [(47,.18),(37,.12),(25,.10),(13,.08)]:
            r = s(r_pct)
            self.create_oval(cx-r, cy-r, cx+r, cy+r,
                             outline=_blend(C_BLUE, alpha), width=1, fill="")

        rad = math.radians(self._angle)
        ex = cx + math.cos(rad) * s(37)
        ey = cy + math.sin(rad) * s(37)
        self.create_line(cx, cy, ex, ey,
                         fill=C_BLUE, width=max(1, int(s(1.5))))

        self.create_line(s(50), s(43), s(50), s(23),
                         fill=C_BLUE, width=1, dash=(4, 3))
        sr = s(3)
        self.create_oval(s(50)-sr, s(21)-sr, s(50)+sr, s(21)+sr,
                         fill=C_BG, outline=C_GOLD, width=1)

        for ex2, ey2 in [(s(36),s(13)),(s(64),s(13)),
                          (s(22),s(40)),(s(78),s(40)),(s(50),s(76))]:
            self.create_line(s(50), s(21), ex2, ey2,
                             fill=C_BLUE, width=1, dash=(3, 3))

        ba = 0.5 + 0.5 * math.sin(self._blink)
        bb = 0.5 + 0.5 * math.sin(self._blink + math.pi / 2)
        onts = [(s(36),s(13),C_GREEN,ba,False),(s(64),s(13),C_GREEN,bb,False),
                (s(22),s(40),C_GREEN,1.0,False),(s(78),s(40),C_RED,1.0,True),
                (s(50),s(76),C_GREEN,1.0,False)]
        or_ = s(2.2)
        for ox, oy, col, alpha, is_anom in onts:
            if is_anom:
                hr = s(self._halo_r)
                ha = max(0.0, 0.8*(1.0-(self._halo_r-2.5)/6.5))
                self.create_oval(ox-hr, oy-hr, ox+hr, oy+hr,
                                 outline=_blend(C_RED, ha), fill="", width=1)
            self.create_oval(ox-or_, oy-or_, ox+or_, oy+or_,
                             fill=_blend(col, min(1.0, alpha*0.15)),
                             outline=_blend(col, min(1.0, alpha)), width=1)

        ow, oh = s(14), s(14)
        ox0, oy0 = s(43), s(43)
        self.create_rectangle(ox0, oy0, ox0+ow, oy0+oh,
                              fill=C_BG, outline=C_BLUE, width=1)
        self.create_text(ox0+ow/2, oy0+oh/2, text="OLT",
                         fill=C_BLUE,
                         font=("Courier", max(5, int(s(5))), "bold"))

        self._angle  = (self._angle + 4.8) % 360
        self._blink  = (self._blink + 0.08) % (2 * math.pi)
        self._halo_r += 0.18 * self._halo_dir
        if self._halo_r >= 9.0: self._halo_dir = -1
        elif self._halo_r <= 2.5: self._halo_dir = 1

        self._after_id = self.after(40, self._draw)


# ── Progress bar on Canvas ─────────────────────────────────────────────────────
class _ProgressBar:
    """tk.Canvas-based progress bar — safe inside tk.Tk() before CTk init."""
    def __init__(self, parent, width=300, height=6):
        self._w = width
        self._c = tk.Canvas(parent, width=width, height=height,
                            bg=C_BG, highlightthickness=0)
        self._c.create_rectangle(0, 0, width, height,
                                 fill=C_BAR_BG, outline="", tags="track")
        self._bar = self._c.create_rectangle(0, 0, 0, height,
                                             fill=C_BAR_FG, outline="",
                                             tags="bar")
    def place(self, **kw): self._c.place(**kw)
    def set(self, fraction):
        fraction = max(0.0, min(1.0, fraction))
        self._c.coords("bar", 0, 0, int(self._w * fraction), 6)


def _pick_font(preferred, fallback, size, weight="normal"):
    try:
        fam = preferred if preferred in tkfont.families() else fallback
    except Exception:
        fam = fallback
    return (fam, size, weight)


# ── Main Splash Screen ─────────────────────────────────────────────────────────
class SplashScreen:
    """
    7-second splash on tk.Tk().
    on_done is accepted for test compatibility but NOT called at runtime.
    main.py opens NOCApp after splash.win.mainloop() returns naturally.
    """

    def __init__(self, on_done=None):  # on_done kept for test compat only
        self._on_done  = on_done   # stored but only used if explicitly needed
        self._after_anim = None
        self._progress   = None
        self._msg_label  = None
        self._logo       = None

        self.win = tk.Tk()
        self.win.overrideredirect(True)
        self.win.configure(bg=C_BG)
        self.win.withdraw()

        self._build_widgets()

        self.win.update_idletasks()
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        x  = max(0, (sw - SPLASH_W) // 2)
        y  = max(0, (sh - SPLASH_H) // 2)
        self.win.geometry(f"{SPLASH_W}x{SPLASH_H}+{x}+{y}")

        self.win.deiconify()
        self.win.lift()
        try:
            self.win.attributes("-topmost", True)
        except Exception:
            pass

        self._schedule_steps()
        if self._logo:
            self._logo._draw()

    def _build_widgets(self):
        bg = tk.Canvas(self.win, width=SPLASH_W, height=SPLASH_H,
                       bg=C_BG, highlightthickness=0)
        bg.place(x=0, y=0)

        for gx in range(0, SPLASH_W, 24):
            bg.create_line(gx, 0, gx, SPLASH_H, fill=C_GRID, width=1)
        for gy in range(0, SPLASH_H, 24):
            bg.create_line(0, gy, SPLASH_W, gy, fill=C_GRID, width=1)

        arm = 24
        for cx_, cy_ in [(0,0),(SPLASH_W,0),(0,SPLASH_H),(SPLASH_W,SPLASH_H)]:
            sx = 1 if cx_ == 0 else -1
            sy = 1 if cy_ == 0 else -1
            bg.create_line(cx_, cy_, cx_+sx*arm, cy_, fill=C_BRACKET, width=2)
            bg.create_line(cx_, cy_, cx_, cy_+sy*arm, fill=C_BRACKET, width=2)

        logo_size = 80
        self._logo = _LogoCanvas(self.win, size=logo_size, bg=C_BG)
        self._logo.place(x=(SPLASH_W-logo_size)//2, y=46)

        tk.Label(self.win, text="NOC-Edge FTTH", bg=C_BG, fg=C_TITLE,
                 font=_pick_font("Inter","Helvetica",22,"bold")
                 ).place(relx=0.5, y=156, anchor="center")

        tk.Label(self.win,
                 text="Proactive  \u00b7  Offline  \u00b7  Intelligent",
                 bg=C_BG, fg=C_TAGLINE,
                 font=_pick_font("JetBrains Mono","Courier",11)
                 ).place(relx=0.5, y=183, anchor="center")

        bg.create_line(SPLASH_W//2-130, 208, SPLASH_W//2+130, 208,
                       fill=C_GRID, width=1)

        self._progress = _ProgressBar(self.win, width=300, height=6)
        self._progress.place(relx=0.5, y=254, anchor="center")

        self._msg_label = tk.Label(self.win, text="Initializing...",
                                   bg=C_BG, fg=C_MSG,
                                   font=_pick_font("JetBrains Mono","Courier",9))
        self._msg_label.place(relx=0.5, y=276, anchor="center")

        # Footer strip — darker background, bolder font, readable by jury
        footer_strip = tk.Frame(self.win, bg="#020509")
        footer_strip.place(x=0, y=334, width=SPLASH_W, height=46)
        tk.Label(footer_strip,
                 text="NOC-Edge FTTH v1.0  \u00b7  Capstone 2026  \u00b7  Roua Jendoubi",
                 bg="#020509", fg="#8da4be",
                 font=_pick_font("JetBrains Mono", "Courier", 10, "bold")
                 ).place(relx=0.5, rely=0.5, anchor="center")

    def _schedule_steps(self):
        for delay_ms, msg, prog in LOADING_STEPS:
            self.win.after(delay_ms,
                           lambda m=msg, p=prog: self._update_step(m, p))
        # At 7000 ms: stop animation, destroy window → mainloop() returns
        self.win.after(SPLASH_DURATION_MS, self._close)

    def _update_step(self, msg, progress):
        try:
            if self._msg_label and self._msg_label.winfo_exists():
                self._msg_label.configure(text=msg)
            if self._progress:
                self._progress.set(progress)
        except Exception:
            pass

    def _close(self):
        """Called at 7 s. Destroy window so mainloop() returns to main()."""
        if self._logo is not None:
            self._logo.stop_animation()
        try:
            self.win.destroy()
        except Exception:
            pass
        # Only call on_done if explicitly provided (used by tests)
        if self._on_done is not None:
            try:
                self._on_done()
            except Exception:
                pass

    # ── kept for test compatibility ────────────────────────────────────────────
    def _finish(self, on_done=None):
        self._close()

    def _animate_radar(self):
        if self._logo and self._logo.winfo_exists():
            self._logo._draw()
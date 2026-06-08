"""
logo.py — Hybrid 2 GPON Topology Inside Radar logo (README §4)
============================================================
Animated at 25fps via root.after(40, draw_frame).
Sizes: 40×40 sidebar, 64×64 splash.

Usage:
    from src.ui.logo import LogoCanvas, set_window_icon
    logo = LogoCanvas(parent, size=40)
    logo.pack()
    set_window_icon(root)          # sets iconphoto(True, ...)
"""
import tkinter as tk
import math

# ── Exact palette from README §2 ─────────────────────────────────────────────
_BLUE       = "#4f8ef7"
_BG         = "#0a0f1c"
_GOLD       = "#fbbf24"
_GREEN      = "#34d399"
_RED        = "#f87171"
_BD         = "#1c2d42"

# Concentric circle specs: (radius_fraction, stroke_opacity_approx_color)
_RING_SPECS = [
    (0.94, "#0d1c36"),  # outermost, faintest
    (0.74, "#0d1e38"),
    (0.50, "#0f2040"),
    (0.26, "#122348"),  # innermost, slightly brighter
]


class LogoCanvas(tk.Canvas):
    """
    Animated Hybrid 2 GPON topology inside radar logo.
    Call start_animation() once embedded in a window.
    """

    def __init__(self, parent, size: int = 40, bg: str = _BG, **kwargs):
        super().__init__(parent, width=size, height=size,
                         bg=bg, highlightthickness=0, **kwargs)
        self._sz  = size
        self._bg  = bg
        self._cx  = size / 2
        self._cy  = size / 2
        self._r   = size / 2 - 1          # outer radius

        # Animation state
        self._sweep_angle  = 0.0          # degrees, 0→360
        self._anom_r       = 0.15         # fraction of size, pulses
        self._anom_growing = True
        self._after_id     = None

        self._draw_static()
        self._radar_line   = self._make_sweep_line()
        self._anom_halo    = self._make_anom_halo()
        self._anom_dot     = self._make_anom_dot()

    # ── Static elements ────────────────────────────────────────────────────
    def _draw_static(self):
        sz, cx, cy = self._sz, self._cx, self._cy
        s = sz / 100.0   # scale factor from 100-unit coordinate space

        # 4 concentric radar rings  (r = 47,37,25,13 in 100-unit space)
        for r_u, fill_c in zip([47, 37, 25, 13], _RING_SPECS):
            r = r_u * s
            self.create_oval(cx - r, cy - r, cx + r, cy + r,
                             outline=_BLUE, width=0.8, fill=fill_c[1])

        # OLT rectangle  (x=43,y=43,w=14,h=14 in 100-unit space → centered)
        olt_hw = 7 * s    # half-width
        olt_hh = 6 * s    # half-height
        self.create_rectangle(cx - olt_hw, cy - olt_hh,
                               cx + olt_hw, cy + olt_hh,
                               outline=_BLUE, width=max(1, int(1.5 * s * 2)),
                               fill=_BG)
        font_sz = max(4, int(6 * s))
        self.create_text(cx, cy, text="OLT",
                         font=("JetBrains Mono", font_sz, "bold"), fill=_BLUE)

        # Trunk line: (50,43)→(50,23) in 100-unit space
        tx1, ty1 = cx, cy - olt_hh
        tx2, ty2 = cx, cy - 27 * s
        self.create_line(tx1, ty1, tx2, ty2, fill=_BLUE,
                         dash=(max(2, int(2.5 * s)), max(1, int(2 * s))),
                         width=max(1, s))

        # Splitter circle at (50,21)  r=3
        sp_x, sp_y = cx, cy - 29 * s
        sp_r = 3 * s
        self.create_oval(sp_x - sp_r, sp_y - sp_r,
                         sp_x + sp_r, sp_y + sp_r,
                         fill=_BG, outline=_GOLD, width=max(1, int(1.4 * s * 2)))

        # Top-left ONT branch  (50,21)→(36,13)
        self._draw_ont_branch(sp_x, sp_y,
                               cx - 14 * s, cy - 37 * s,
                               _GREEN, s)

        # Top-right ONT branch  (50,21)→(64,13)
        self._draw_ont_branch(sp_x, sp_y,
                               cx + 14 * s, cy - 37 * s,
                               _GREEN, s)

        # Left lateral ONT   OLT edge → (22,40)
        self._draw_ont_branch(cx - olt_hw, cy,
                               cx - 28 * s, cy - 10 * s,
                               _GREEN, s)

        # Bottom ONT  OLT edge → (50,76)
        self._draw_ont_branch(cx, cy + olt_hh,
                               cx, cy + 26 * s,
                               _GREEN, s)

        # Store anomaly position for pulsing  (right lateral ONT → (78,40))
        self._ax = cx + 28 * s
        self._ay = cy - 10 * s
        # Static wire (no halo yet)
        self.create_line(cx + olt_hw, cy, self._ax, self._ay,
                         fill=_BLUE,
                         dash=(max(2, int(2.5 * s)), max(1, int(2 * s))),
                         width=max(1, s))

    def _draw_ont_branch(self, x1, y1, x2, y2, color, s):
        """Draw a dashed branch line + ONT circle."""
        self.create_line(x1, y1, x2, y2, fill=_BLUE,
                         dash=(max(2, int(2.5 * s)), max(1, int(2 * s))),
                         width=max(1, s))
        r = 2.2 * s
        self.create_oval(x2 - r, y2 - r, x2 + r, y2 + r,
                         fill=_BG, outline=color,
                         width=max(1, int(1.2 * s * 2)))

    def _make_sweep_line(self):
        """Create the radar sweep line (will be animated)."""
        r_sweep = 37 * (self._sz / 100.0)   # matches 2nd ring radius
        return self.create_line(self._cx, self._cy,
                                self._cx + r_sweep, self._cy,
                                fill=_BLUE, width=max(1, int(1.5 * self._sz / 40)))

    def _make_anom_dot(self):
        """Static red dot for anomaly ONT."""
        s = self._sz / 100.0
        r = 2.2 * s
        ax, ay = self._ax, self._ay
        return self.create_oval(ax - r, ay - r, ax + r, ay + r,
                                fill=_BG, outline=_RED,
                                width=max(1, int(1.3 * s * 2)))

    def _make_anom_halo(self):
        """Pulsing halo for anomaly ONT."""
        s = self._sz / 100.0
        r = 2.5 * s
        ax, ay = self._ax, self._ay
        return self.create_oval(ax - r, ay - r, ax + r, ay + r,
                                outline=_RED, fill="", width=max(1, s))

    # ── Animation ─────────────────────────────────────────────────────────
    def start_animation(self):
        """Begin 25fps animation loop. Call once after window is created."""
        self._animate()

    def stop_animation(self):
        """Stop the animation (e.g. when splash is destroyed)."""
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _animate(self):
        # Radar sweep: 360° in 3s = 2° per frame at 25fps
        self._sweep_angle = (self._sweep_angle + 2.0) % 360.0
        r_sweep = 37 * (self._sz / 100.0)
        rad = math.radians(self._sweep_angle)
        ex = self._cx + r_sweep * math.cos(rad)
        ey = self._cy + r_sweep * math.sin(rad)
        self.coords(self._radar_line, self._cx, self._cy, ex, ey)

        # Anomaly halo pulse: r 2.5→9→2.5 in 50 frames (2s at 25fps)
        s = self._sz / 100.0
        min_r, max_r = 2.5 * s, 9.0 * s
        speed = (max_r - min_r) / 25   # 25 frames half-cycle
        ax, ay = self._ax, self._ay
        if self._anom_growing:
            self._anom_r += speed
            if self._anom_r >= max_r:
                self._anom_r = max_r
                self._anom_growing = False
        else:
            self._anom_r -= speed
            if self._anom_r <= min_r:
                self._anom_r = min_r
                self._anom_growing = True
        r = self._anom_r
        self.coords(self._anom_halo, ax - r, ay - r, ax + r, ay + r)

        # Raise animated items above static
        self.tag_raise(self._radar_line)
        self.tag_raise(self._anom_halo)
        self.tag_raise(self._anom_dot)

        self._after_id = self.after(40, self._animate)


# ── Window Icon Helper ────────────────────────────────────────────────────────

def set_window_icon(root: tk.Misc) -> None:
    """
    Render the Hybrid 2 logo at 32×32 and set it as the window icon.
    Uses PIL if available, falls back to a blank PhotoImage.
    README §4: root.iconphoto(True, img)
    """
    try:
        _set_icon_pil(root)
    except Exception:
        _set_icon_canvas(root)


def _set_icon_pil(root: tk.Misc) -> None:
    """PIL-based icon rendering (best quality)."""
    from PIL import Image, ImageDraw, ImageTk
    import math as _m

    size = 32
    img  = Image.new("RGBA", (size, size), (10, 15, 28, 255))
    draw = ImageDraw.Draw(img)
    cx, cy = size / 2, size / 2
    s = size / 100.0

    # Concentric rings
    rings = [(47, (79, 142, 247, 46)), (37, (79, 142, 247, 31)),
             (25, (79, 142, 247, 25)), (13, (79, 142, 247, 20))]
    for ru, rgba in rings:
        r = ru * s
        draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                     outline=rgba, width=1)

    # OLT box
    olt_hw, olt_hh = 7 * s, 6 * s
    draw.rectangle([cx - olt_hw, cy - olt_hh, cx + olt_hw, cy + olt_hh],
                   outline=(79, 142, 247, 255), width=1)

    # Trunk
    sp_x, sp_y = cx, cy - 29 * s
    draw.line([(cx, cy - olt_hh), (sp_x, sp_y)],
              fill=(79, 142, 247, 200), width=1)

    # Splitter
    sp_r = 3 * s
    draw.ellipse([sp_x - sp_r, sp_y - sp_r, sp_x + sp_r, sp_y + sp_r],
                 outline=(251, 191, 36, 255), width=1)

    # ONT branches (static green, red for anomaly)
    branches = [
        (sp_x, sp_y, cx - 14 * s, cy - 37 * s, (52, 211, 153, 220)),
        (sp_x, sp_y, cx + 14 * s, cy - 37 * s, (52, 211, 153, 220)),
        (cx - olt_hw, cy, cx - 28 * s, cy - 10 * s, (52, 211, 153, 220)),
        (cx, cy + olt_hh, cx, cy + 26 * s, (52, 211, 153, 220)),
        (cx + olt_hw, cy, cx + 28 * s, cy - 10 * s, (248, 113, 113, 255)),
    ]
    for x1, y1, x2, y2, col in branches:
        draw.line([(x1, y1), (x2, y2)], fill=(79, 142, 247, 160), width=1)
        r = 2.2 * s
        draw.ellipse([x2 - r, y2 - r, x2 + r, y2 + r], outline=col, width=1)

    # Radar sweep (static, pointing right)
    r_sw = 37 * s
    draw.line([(cx, cy), (cx + r_sw, cy)], fill=(79, 142, 247, 192), width=1)

    tk_icon = ImageTk.PhotoImage(img)
    # Keep a reference so it isn't garbage-collected
    root._noc_icon = tk_icon  # type: ignore[attr-defined]
    root.iconphoto(True, tk_icon)


def _set_icon_canvas(root: tk.Misc) -> None:
    """
    Fallback: create a temporary 32×32 canvas, draw to it,
    take a screenshot and use as PhotoImage.
    """
    try:
        import tkinter as _tk
        tmp = _tk.Toplevel()
        tmp.withdraw()
        c = _tk.Canvas(tmp, width=32, height=32, bg=_BG, highlightthickness=0)
        c.pack()
        tmp.update_idletasks()
        # Draw a minimal radar circle + OLT
        c.create_oval(2, 2, 30, 30, outline=_BLUE, width=1, fill=_BG)
        c.create_rectangle(12, 11, 20, 21, outline=_BLUE, width=1, fill=_BG)
        c.create_text(16, 16, text="N", font=("JetBrains Mono", 7, "bold"),
                      fill=_BLUE)
        tmp.destroy()
    except Exception:
        pass

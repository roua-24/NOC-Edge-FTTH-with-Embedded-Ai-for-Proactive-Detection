"""
icons.py — SVG Icon Registry (README §1, §4)
All icons are 14px Feather/Lucide-style SVG stroke icons.
No emojis. 1.8px stroke-width, stroke-linecap="round".
Rendered on tk.Canvas via create_line / create_arc / create_oval.
"""
import tkinter as tk
from src.ui.theme import ACCENT, TEXT2, TEXT3, BG_CARD, BG_SIDEBAR

# Icon size constants
ICON_SIZE   = 14
ICON_STROKE = 1.8

# ── SVG path data registry (Feather/Lucide style, 24x24 viewBox) ─────────────
# Each entry: list of draw commands for tk.Canvas scaled to ICON_SIZE px.
# Format: ("line"|"oval"|"arc"|"rect"|"poly", *args, **kwargs)

def _scale(pts, size=ICON_SIZE, vb=24):
    """Scale a list of (x,y) points from 24x24 viewBox to target size."""
    s = size / vb
    return [(x * s, y * s) for x, y in pts]


def _draw_icon(canvas, icon_name, x0=0, y0=0, color=TEXT2, size=ICON_SIZE):
    """
    Draw a named icon on a tk.Canvas at position (x0, y0).
    All coordinates are offsets from (x0, y0).
    """
    s = size / 24
    w = max(1, ICON_STROKE)

    def L(*pts):
        """Draw polyline through scaled points."""
        coords = []
        for px, py in pts:
            coords += [x0 + px * s, y0 + py * s]
        if len(coords) >= 4:
            canvas.create_line(*coords, fill=color, width=w,
                               capstyle="round", joinstyle="round")

    def R(x, y, x2, y2, rx=2):
        """Draw rounded rectangle."""
        canvas.create_rectangle(
            x0 + x * s, y0 + y * s, x0 + x2 * s, y0 + y2 * s,
            outline=color, width=w, fill="")

    def C(cx, cy, r):
        """Draw circle."""
        canvas.create_oval(
            x0 + (cx - r) * s, y0 + (cy - r) * s,
            x0 + (cx + r) * s, y0 + (cy + r) * s,
            outline=color, width=w, fill="")

    icons = {
        # grid icon (Dashboard)
        "grid": lambda: [
            R(3, 3, 10, 10), R(14, 3, 21, 10),
            R(14, 14, 21, 21), R(3, 14, 10, 21),
        ],
        # clock icon (Activity)
        "clock": lambda: [
            C(12, 12, 9),
            L((12, 7), (12, 12), (16, 14)),
        ],
        # share icon (Topology)
        "share": lambda: [
            C(18, 5, 3), C(6, 12, 3), C(18, 19, 3),
            L((8.59, 13.51), (15.42, 17.49)),
            L((15.41, 6.51), (8.59, 10.49)),
        ],
        # server icon (Devices)
        "server": lambda: [
            R(2, 2, 22, 8, rx=2), R(2, 14, 22, 20, rx=2),
            L((6, 6), (6.01, 6)), L((6, 18), (6.01, 18)),
        ],
        # activity icon (Bandwidth)
        "activity": lambda: [
            L((22, 12), (18, 12), (15, 21), (9, 3), (6, 12), (2, 12)),
        ],
        # layers icon (Netflow)
        "layers": lambda: [
            L((12, 2), (2, 7), (12, 12), (22, 7), (12, 2)),
            L((2, 17), (12, 22), (22, 17)),
            L((2, 12), (12, 17), (22, 12)),
        ],
        # shield icon (Security)
        "shield": lambda: [
            L((12, 22), (12, 22)),
            canvas.create_polygon(
                [x0 + 12*s, y0 + 22*s,
                 x0 + 4*s,  y0 + 14*s,
                 x0 + 4*s,  y0 + 5*s,
                 x0 + 12*s, y0 + 2*s,
                 x0 + 20*s, y0 + 5*s,
                 x0 + 20*s, y0 + 14*s],
                outline=color, width=w, fill=""),
        ],
        # alert-triangle icon (Incidents)
        "alert": lambda: [
            canvas.create_polygon(
                [x0 + 10.29*s, y0 + 3.86*s,
                 x0 + 1.21*s,  y0 + 19*s,
                 x0 + 22.79*s, y0 + 19*s],
                outline=color, width=w, fill=""),
            L((12, 9), (12, 13)), L((12, 17), (12.01, 17)),
        ],
        # radio icon (Diagnostics)
        "radio": lambda: [
            C(12, 12, 2), C(12, 12, 7),
            L((4.93, 4.93), (4.93, 4.93)),
            L((19.07, 4.93), (19.07, 4.93)),
            L((19.07, 19.07), (19.07, 19.07)),
            L((4.93, 19.07), (4.93, 19.07)),
        ],
        # settings/cog icon
        "settings": lambda: [
            C(12, 12, 3),
            canvas.create_polygon(
                [x0 + 19.4*s, y0 + 15*s,
                 x0 + 19.4*s, y0 + 15*s,
                 x0 + 21*s,   y0 + 12*s,
                 x0 + 19.4*s, y0 + 9*s,
                 x0 + 19.4*s, y0 + 9*s,
                 x0 + 16.76*s,y0 + 8.24*s,
                 x0 + 15*s,   y0 + 4.6*s,
                 x0 + 15*s,   y0 + 3*s,
                 x0 + 12*s,   y0 + 1*s,
                 x0 + 9*s,    y0 + 3*s,
                 x0 + 9*s,    y0 + 4.6*s,
                 x0 + 7.24*s, y0 + 8.24*s,
                 x0 + 4.6*s,  y0 + 9*s,
                 x0 + 3*s,    y0 + 9*s,
                 x0 + 1*s,    y0 + 12*s,
                 x0 + 3*s,    y0 + 15*s,
                 x0 + 4.6*s,  y0 + 15*s,
                 x0 + 7.24*s, y0 + 15.76*s,
                 x0 + 9*s,    y0 + 19.4*s,
                 x0 + 9*s,    y0 + 21*s,
                 x0 + 12*s,   y0 + 23*s,
                 x0 + 15*s,   y0 + 21*s,
                 x0 + 15*s,   y0 + 19.4*s,
                 x0 + 16.76*s,y0 + 15.76*s,
                 x0 + 19.4*s, y0 + 15*s],
                outline=color, width=w, fill=""),
        ],
        # eye icon (View)
        "eye": lambda: [
            canvas.create_arc(
                x0 + 1*s, y0 + 6*s,
                x0 + 23*s, y0 + 18*s,
                start=0, extent=180, outline=color, width=w, style="arc"),
            canvas.create_arc(
                x0 + 1*s, y0 + 6*s,
                x0 + 23*s, y0 + 18*s,
                start=180, extent=180, outline=color, width=w, style="arc"),
            C(12, 12, 3),
        ],
        # trash icon (Delete)
        "trash": lambda: [
            L((3, 6), (21, 6)),
            L((8, 6), (8, 3), (16, 3), (16, 6)),
            R(5, 6, 19, 21),
        ],
        # edit icon
        "edit": lambda: [
            canvas.create_polygon(
                [x0 + 11*s, y0 + 4*s,
                 x0 + 4*s,  y0 + 4*s,
                 x0 + 4*s,  y0 + 20*s,
                 x0 + 20*s, y0 + 20*s,
                 x0 + 20*s, y0 + 13*s],
                outline=color, width=w, fill=""),
            L((18.5, 2.5), (21.5, 5.5), (10.5, 16.5), (7, 17), (7.5, 13.5), (18.5, 2.5)),
        ],
        # refresh icon
        "refresh": lambda: [
            canvas.create_arc(
                x0 + 3*s, y0 + 3*s,
                x0 + 21*s, y0 + 21*s,
                start=0, extent=270, outline=color, width=w, style="arc"),
            L((20, 4), (20, 8), (16, 8)),
        ],
        # terminal icon
        "terminal": lambda: [
            R(4, 4, 20, 20, rx=2),
            L((9, 9), (15, 9)),
            L((9, 12), (9, 15)),
        ],
        # download icon
        "download": lambda: [
            L((12, 3), (12, 15)),
            L((8, 11), (12, 15), (16, 11)),
            L((3, 20), (21, 20)),
        ],
        # check circle
        "check_circle": lambda: [
            C(12, 12, 9),
            L((9, 12), (11, 14), (15, 10)),
        ],
        # x circle (close)
        "x_circle": lambda: [
            C(12, 12, 9),
            L((15, 9), (9, 15)),
            L((9, 9), (15, 15)),
        ],
        # info icon
        "info": lambda: [
            C(12, 12, 9),
            L((12, 8), (12, 8.01)),
            L((12, 11), (12, 16)),
        ],
        # wifi icon
        "wifi": lambda: [
            canvas.create_arc(x0 + 1*s, y0 + 3*s, x0 + 23*s, y0 + 23*s,
                              start=30, extent=120, outline=color, width=w, style="arc"),
            canvas.create_arc(x0 + 5*s, y0 + 7*s, x0 + 19*s, y0 + 19*s,
                              start=30, extent=120, outline=color, width=w, style="arc"),
            canvas.create_arc(x0 + 9*s, y0 + 11*s, x0 + 15*s, y0 + 17*s,
                              start=30, extent=120, outline=color, width=w, style="arc"),
            C(12, 20, 1),
        ],
        # bar-chart icon
        "bar_chart": lambda: [
            L((18, 20), (18, 10)),
            L((12, 20), (12, 4)),
            L((6, 20), (6, 14)),
        ],
        # file-text icon
        "file_text": lambda: [
            canvas.create_polygon(
                [x0 + 14*s, y0 + 2*s,
                 x0 + 4*s,  y0 + 2*s,
                 x0 + 4*s,  y0 + 22*s,
                 x0 + 20*s, y0 + 22*s,
                 x0 + 20*s, y0 + 8*s,
                 x0 + 14*s, y0 + 2*s],
                outline=color, width=w, fill=""),
            L((14, 2), (14, 8), (20, 8)),
            L((9, 13), (15, 13)),
            L((9, 17), (15, 17)),
        ],
        # cpu icon
        "cpu": lambda: [
            R(9, 9, 15, 15),
            R(4, 4, 20, 20),
            L((9, 1), (9, 4)),
            L((15, 1), (15, 4)),
            L((9, 20), (9, 23)),
            L((15, 20), (15, 23)),
            L((1, 9), (4, 9)),
            L((1, 15), (4, 15)),
            L((20, 9), (23, 9)),
            L((20, 15), (23, 15)),
        ],
        # zap icon (anomaly)
        "zap": lambda: [
            canvas.create_polygon(
                [x0 + 13*s, y0 + 2*s,
                 x0 + 3*s,  y0 + 14*s,
                 x0 + 12*s, y0 + 14*s,
                 x0 + 11*s, y0 + 22*s,
                 x0 + 21*s, y0 + 10*s,
                 x0 + 12*s, y0 + 10*s,
                 x0 + 13*s, y0 + 2*s],
                outline=color, width=w, fill=""),
        ],
    }

    if icon_name in icons:
        try:
            icons[icon_name]()
        except Exception:
            pass
    else:
        # Fallback: draw a small circle
        C(12, 12, 4)


def make_icon_canvas(parent, icon_name, size=ICON_SIZE,
                     color=TEXT2, bg=BG_CARD):
    """Create and return a tk.Canvas with the named icon drawn on it."""
    c = tk.Canvas(parent, width=size, height=size,
                  bg=bg, highlightthickness=0)
    _draw_icon(c, icon_name, x0=0, y0=0, color=color, size=size)
    return c


def nav_icon(parent, icon_name, is_active=False, bg=BG_SIDEBAR):
    """Return a 16×16 nav icon canvas for the sidebar."""
    color = ACCENT if is_active else TEXT3
    return make_icon_canvas(parent, icon_name, size=16, color=color, bg=bg)


# Icon name mapping for nav items (matches NAV_GROUPS in app.py)
NAV_ICON_MAP = {
    "grid":       "grid",
    "clock":      "clock",
    "share":      "share",
    "server":     "server",
    "activity":   "activity",
    "layers":     "layers",
    "shield":     "shield",
    "alert":      "alert",
    "radio":      "radio",
    "settings":   "settings",
}

"""
theme.py — Color tokens + matplotlib rcParams (README §2, §3, §17)
Exact hex values from NOC_EDGE_FTTH_UI_README_FOR_ANTIGRAVITY.md §2.
"""
import matplotlib.pyplot as plt

# ── Background layers (README §2) ────────────────────────────────────────────
BG_DEEP    = "#070b14"
BG_BODY    = "#0a0f1c"
BG_SIDEBAR = "#0c1222"
BG_CARD    = "#101828"
BG_CARD2   = "#131f30"
BG_HOVER   = "#162035"

# Legacy aliases (keep for backward compat with other modules)
BG_BASE    = BG_BODY
BG_VOID    = BG_DEEP
BG_DARK    = BG_DEEP

# ── Borders ───────────────────────────────────────────────────────────────────
BD         = "#1c2d42"
BDM        = "#253a55"
BDH        = "#3056a0"

# Legacy border aliases
BORDER_DIM = BD
BORDER_MID = BDM
BORDER_HI  = BDH

# ── Accent colors (README §2) ─────────────────────────────────────────────────
BLUE       = "#4f8ef7"
BLUE_BG    = "#132040"
TEAL       = "#2dd4bf"
GREEN      = "#34d399"
GREEN_BG   = "#083325"
YELLOW     = "#fbbf24"
YELLOW_BG  = "#291e06"
ORANGE     = "#fb923c"
ORANGE_BG  = "#28150a"
RED        = "#f87171"
RED_BG     = "#2a0f0f"
PURPLE     = "#a78bfa"
PURPLE_BG  = "#1e1340"
PINK       = "#f472b6"
CYAN       = "#67e8f9"

# Legacy accent aliases
ACCENT     = BLUE
ACCENT_DIM = BLUE_BG
GREEN_DIM  = GREEN_BG
RED_DIM    = RED_BG
PURPLE_DIM = PURPLE_BG

# ── Text levels (README §2) ───────────────────────────────────────────────────
T1 = "#e2eaf6"   # primary text
T2 = "#8da4be"   # secondary text
T3 = "#4a6278"   # muted / labels
T4 = "#2a3f55"   # group headings, very muted

# Legacy text aliases
TEXT1 = T1
TEXT2 = T2
TEXT3 = T3
TEXT4 = T4

# ── Severity mapping ──────────────────────────────────────────────────────────
SEVERITY_COLORS = {
    "ok":       GREEN,
    "warning":  YELLOW,
    "major":    ORANGE,
    "critical": RED,
    "ai":       PURPLE,
    "primary":  BLUE,
    "tx":       CYAN,
}

# ── Typography constants (README §3) ──────────────────────────────────────────
FONT_TITLE    = ("Inter", 16, "bold")
FONT_SUBTITLE = ("Inter", 12)
FONT_LABEL    = ("Inter", 11)
FONT_SMALL    = ("Inter", 10)
FONT_MONO_LG  = ("JetBrains Mono", 28, "bold")
FONT_MONO_MD  = ("JetBrains Mono", 16, "bold")
FONT_MONO     = ("JetBrains Mono", 10)
FONT_MONO_SM  = ("JetBrains Mono", 9)
FONT_MONO_XS  = ("JetBrains Mono", 8)
FONT_GROUP    = ("JetBrains Mono", 9)


# ── matplotlib rcParams (README §17) ─────────────────────────────────────────

NOC_RC = {
    "figure.facecolor":  "#0d1626",
    "axes.facecolor":    "#0d1626",
    "axes.edgecolor":    BD,
    "axes.labelcolor":   T3,
    "axes.titlecolor":   T1,
    "axes.grid":         True,
    "grid.color":        "#152238",
    "grid.linewidth":    0.5,
    "xtick.color":       T3,
    "ytick.color":       T3,
    "xtick.labelsize":   8,
    "ytick.labelsize":   8,
    "legend.facecolor":  BG_CARD,
    "legend.edgecolor":  BD,
    "legend.fontsize":   8,
    "font.family":       "monospace",
    "text.color":        T1,
    "lines.linewidth":   1.8,
    "figure.dpi":        96,
    "figure.autolayout": True,
}


def apply_matplotlib_theme():
    """Apply global matplotlib rcParams per README §17. Call once at startup."""
    plt.rcParams.update(NOC_RC)

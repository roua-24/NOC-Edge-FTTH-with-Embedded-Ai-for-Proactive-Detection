"""
tests/unit/conftest.py — MUST be placed at tests/unit/conftest.py
────────────────────────────────────────────────────────────────────
Runs BEFORE pytest collects any test module.
Fixes two problems:
  1. `import customtkinter` fails (not installed in CI / test env)
  2. `matplotlib.use("TkAgg")` at the top of every tab file crashes headless

Solution: switch matplotlib to Agg first, then stub use() so tab-level
calls to matplotlib.use("TkAgg") are silently ignored.
"""
import sys
import types
import tkinter as _tk

# ── Step 0: Agg backend FIRST, then make use() a no-op ───────────────────────
import matplotlib as _mpl
_mpl.use("Agg")                        # switch before any tab is imported

import matplotlib.pyplot as _plt
_plt.switch_backend("Agg")

_real_mpl_use = _mpl.use
def _safe_mpl_use(backend, *a, **kw):  # ignore TkAgg calls from tab files
    if str(backend).lower() == "tkagg":
        return
    _real_mpl_use(backend, *a, **kw)
_mpl.use = _safe_mpl_use              # monkey-patch before tab import

# ── Step 1: Stub FigureCanvasTkAgg ───────────────────────────────────────────
_be = types.ModuleType("matplotlib.backends.backend_tkagg")
class _FakeCanvas:
    def __init__(self, fig, master=None): self.fig = fig
    def draw(self):         pass
    def draw_idle(self):    pass
    def mpl_connect(self, *a, **kw): return 0
    def get_tk_widget(self):
        class _FW:
            def pack(self, *a, **kw):  pass
            def grid(self, *a, **kw):  pass
            def place(self, *a, **kw): pass
        return _FW()
_be.FigureCanvasTkAgg = _FakeCanvas
sys.modules["matplotlib.backends.backend_tkagg"] = _be

# ── Step 2: customtkinter stub ────────────────────────────────────────────────
def _build_ctk():
    ctk = types.ModuleType("customtkinter")
    ctk.set_appearance_mode     = lambda *a, **kw: None
    ctk.set_default_color_theme = lambda *a, **kw: None

    class _W(_tk.Frame):
        def __init__(self, master=None, *a, **kw):
            _tk.Frame.__init__(self, master)

        def get(self):                 return ""
        def set(self, *a, **kw):       pass
        def insert(self, *a, **kw):    pass
        def delete(self, *a, **kw):    pass
        def cget(self, key):           return ""
        def title(self, *a):           pass
        def geometry(self, *a):        pass
        def resizable(self, *a):       pass
        def overrideredirect(self, *a): pass
        def __iter__(self): return iter([])

        def __getattr__(self, name):
            # Returns a MagicMock for any undefined attribute.
            import unittest.mock as _mock
            return _mock.MagicMock()

    class _Var:
        def __init__(self, *a, **kw):
            self._v = kw.get("value", "")
        def get(self):       return self._v
        def set(self, v):    self._v = v
        def trace_add(self, *a, **kw): pass

    class StringVar(_Var):
        def __init__(self, *a, **kw): self._v = kw.get("value", "")
    class IntVar(_Var):
        def __init__(self, *a, **kw): self._v = kw.get("value", 0)
    class DoubleVar(_Var):
        def __init__(self, *a, **kw): self._v = kw.get("value", 0.0)
    class BooleanVar(_Var):
        def __init__(self, *a, **kw): self._v = kw.get("value", False)

    ctk.CTk                  = _W
    ctk.CTkToplevel          = _W
    ctk.CTkFrame             = _W
    ctk.CTkLabel             = _W
    ctk.CTkButton            = _W
    ctk.CTkEntry             = _W
    ctk.CTkScrollableFrame   = _W
    ctk.CTkOptionMenu        = _W
    ctk.CTkSlider            = _W
    ctk.CTkProgressBar       = _W
    ctk.CTkTextbox           = _W
    ctk.CTkTabview           = _W
    ctk.CTkCheckBox          = _W
    ctk.CTkSwitch            = _W
    ctk.CTkSegmentedButton   = _W
    ctk.CTkImage             = _W
    ctk.CTkFont              = _W
    ctk.StringVar            = StringVar
    ctk.IntVar               = IntVar
    ctk.DoubleVar            = DoubleVar
    ctk.BooleanVar           = BooleanVar
    return ctk

if "customtkinter" not in sys.modules:
    sys.modules["customtkinter"] = _build_ctk()

# ── Step 3: networkx optional stub ───────────────────────────────────────────
try:
    import networkx  # noqa
except ImportError:
    import unittest.mock as _mock
    _nx = types.ModuleType("networkx")
    _nx.DiGraph              = _mock.MagicMock
    _nx.draw_networkx_edges  = lambda *a, **kw: None
    _nx.draw_networkx_nodes  = lambda *a, **kw: None
    _nx.draw_networkx_labels = lambda *a, **kw: None
    sys.modules["networkx"] = _nx
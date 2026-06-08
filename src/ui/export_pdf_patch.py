# src/ui/export_pdf_patch.py
# FIXED: generate_pdf import moved INSIDE the function — not at top level.
# A top-level import of src.reports.pdf_generator pulls in reportlab immediately.
# If reportlab is not bundled by PyInstaller, the entire app crashes on launch.

import threading
import os
from datetime import datetime

try:
    import customtkinter as ctk
    _USE_CTK = True
except ImportError:
    _USE_CTK = False


def export_pdf(self) -> None:
    # Import INSIDE the function — only runs when button is clicked
    from src.reports.pdf_generator import generate_pdf

    if not hasattr(self, "df_kpi") or self.df_kpi is None or len(self.df_kpi) == 0:
        _show_error(self, "No dataset loaded. Please load a CSV file first.")
        return

    rapport  = getattr(self, "rapport_conformite", {})
    figures  = getattr(self, "figures", [])
    scenario = getattr(self, "scenario", "v3_MAX")

    _set_button_state(self, "export_btn", "disabled")
    _update_status(self, "Generating PDF report...")

    def _run():
        try:
            path = generate_pdf(
                df_kpi=self.df_kpi,
                rapport_conformite=rapport,
                figures=figures,
                path_out=None,
                scenario=scenario,
            )
            self.after(0, lambda: _on_success(self, path))
        except Exception as exc:
            self.after(0, lambda: _on_error(self, str(exc)))

    threading.Thread(target=_run, daemon=True).start()


def _on_success(app, path: str) -> None:
    _set_button_state(app, "export_btn", "normal")
    _update_status(app, f"Report generated: {os.path.basename(path)}")
    _show_info(app, f"PDF report saved:\n{path}")


def _on_error(app, msg: str) -> None:
    _set_button_state(app, "export_btn", "normal")
    _update_status(app, "PDF generation failed.")
    _show_error(app, f"PDF generation failed:\n{msg}")


def _set_button_state(app, btn_attr, state):
    btn = getattr(app, btn_attr, None)
    if btn is not None:
        try: btn.configure(state=state)
        except Exception: pass


def _update_status(app, msg):
    lbl = getattr(app, "lbl_status", None)
    if lbl is not None:
        try: lbl.configure(text=msg)
        except Exception: pass


def _show_info(app, msg):
    try:
        from CTkMessagebox import CTkMessagebox
        CTkMessagebox(master=app, title="Export PDF", message=msg, icon="check")
        return
    except Exception:
        pass
    import tkinter.messagebox as mb
    mb.showinfo("Export PDF", msg)


def _show_error(app, msg):
    try:
        from CTkMessagebox import CTkMessagebox
        CTkMessagebox(master=app, title="Error", message=msg, icon="cancel")
        return
    except Exception:
        pass
    import tkinter.messagebox as mb
    mb.showerror("Error", msg)
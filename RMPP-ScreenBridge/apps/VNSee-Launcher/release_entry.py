"""Single frozen entry point for the portable installer and uninstaller."""
from __future__ import annotations

import sys


def main() -> int:
    if "--smoke-test" in sys.argv:
        import cryptography  # noqa: F401
        import paramiko  # noqa: F401
        import win32api  # noqa: F401
        import win32cred  # noqa: F401
        from portable_manager import PROJECT
        from portable_gui import App
        from uninstaller_gui import Uninstaller

        qmd = PROJECT / "deploy" / "qmd-vnsee-layout" / "vnsee-asivery-clip-v7-landscape.qmd"
        if not qmd.is_file():
            raise FileNotFoundError(f"Release QMD is missing: {qmd}")
        for factory in (App, Uninstaller):
            window = factory().root
            window.withdraw()
            window.update_idletasks()
            window.destroy()
        return 0

    if "--uninstall" in sys.argv:
        from uninstaller_gui import Uninstaller

        Uninstaller().root.mainloop()
    else:
        from portable_gui import App

        App().root.mainloop()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        if "--smoke-test" in sys.argv:
            raise
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("RMPP ScreenBridge", str(exc), parent=root)
        raise SystemExit(1)

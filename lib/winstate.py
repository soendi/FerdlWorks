"""Fensterposition und -größe merken und wiederherstellen.

Speichert für jedes Fenster (nach Klassenname) Größe und Position in den
Settings und stellt sie beim nächsten Öffnen wieder her. So muss der
Benutzer Fenster nicht bei jedem Start neu anordnen.

Transiente Fenster (z. B. der Kalender-Popup) können sich per Attribut
``_winstate_exclude = True`` von der Speicherung ausnehmen.
"""
import tkinter as tk


def _key(win, suffix):
    return "winstate_{}{}".format(win.__class__.__name__, suffix)


class WinState:
    def __init__(self, db):
        self._db = db

    def restore(self, win, default_geometry=None):
        try:
            settings = self._db.settings_get_all()
        except Exception:
            return
        geo = settings.get(_key(win, "_geo"))
        zoom = settings.get(_key(win, "_zoom")) == "1"
        if not geo or "x" not in geo:
            if default_geometry:
                win.geometry(default_geometry)
            if zoom:
                try:
                    win.state("zoomed")
                except tk.TclError:
                    pass
            return
        try:
            size, _, pos = geo.partition("+")
            w, h = size.split("x")[0], size.split("x")[1]
            w, h = int(w), int(h)
            if pos:
                x, y = pos.split("+")
                x, y = int(x), int(y)
            else:
                x = y = 0
        except (ValueError, IndexError):
            return
        if w <= 0 or h <= 0:
            return
        try:
            sw = win.winfo_screenwidth()
            sh = win.winfo_screenheight()
        except tk.TclError:
            sw = sh = 0
        if sw and w > sw:
            w = sw
        if sh and h > sh:
            h = sh
        if sw and x < 0:
            x = 0
        if sh and y < 0:
            y = 0
        if sw and x + w > sw:
            x = max(0, sw - w)
        if sh and y + h > sh:
            y = max(0, sh - h)
        win.geometry("{}x{}+{}+{}".format(w, h, x, y))
        if zoom:
            try:
                win.state("zoomed")
            except tk.TclError:
                pass

    def save(self, win):
        try:
            if not win.winfo_exists():
                return
            state = win.state()
        except tk.TclError:
            return
        try:
            if state == "zoomed":
                self._db.settings_set(_key(win, "_zoom"), "1")
                self._db.settings_set(_key(win, "_geo"), win.geometry())
            elif state == "iconic":
                self._db.settings_set(_key(win, "_zoom"), "0")
            else:
                self._db.settings_set(_key(win, "_zoom"), "0")
                self._db.settings_set(_key(win, "_geo"), win.geometry())
        except Exception:
            pass


_installed = False


def install_auto(db):
    """Installiert das automatische Merken für alle Toplevel-Fenster."""
    global _installed
    if _installed:
        return
    _installed = True

    ws = WinState(db)
    _orig_init = tk.Toplevel.__init__
    _orig_destroy = tk.Toplevel.destroy

    def _safe(fn):
        try:
            fn()
        except Exception:
            pass

    def _patched_init(self, *args, **kwargs):
        _orig_init(self, *args, **kwargs)
        try:
            self.after(10, lambda: _safe(lambda: ws.restore(self)))
        except tk.TclError:
            pass

    def _patched_destroy(self):
        if not getattr(self, "_winstate_exclude", False):
            _safe(lambda: ws.save(self))
        _orig_destroy(self)

    tk.Toplevel.__init__ = _patched_init
    tk.Toplevel.destroy = _patched_destroy

import os, sys
import tkinter as tk
from PIL import Image, ImageDraw, ImageFont

ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
ICON_PNG = os.path.join(ICON_DIR, "ferdlworks.png")
ICON_ICO = os.path.join(ICON_DIR, "ferdlworks.ico")

RED = (139, 0, 0, 255)
RED_DARK = (92, 0, 0, 255)
BLACK = (0, 0, 0, 255)

_FONT_CANDIDATES = [
    ("C:\\Windows\\Fonts\\ariblk.ttf", "Arial Black"),
    ("C:\\Windows\\Fonts\\seguibl.ttf", "Segoe UI Black"),
    ("C:\\Windows\\Fonts\\arialbd.ttf", "Arial Bold"),
    ("C:\\Windows\\Fonts\\impact.ttf", "Impact"),
    ("C:\\Windows\\Fonts\\verdanab.ttf", "Verdana Bold"),
    ("C:\\Windows\\Fonts\\tahomabd.ttf", "Tahoma Bold"),
]

def _fat_font(size):
    for path, name in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    for name in ("Arial Black", "Segoe UI Black", "Arial", "DejaVu Sans"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return None

def _draw_f(draw, size):
    """Riesiges fettes F in der Mitte zeichnen (Schrift oder Polygon-Fallback)."""
    base = int(size * 0.92)
    font = _fat_font(base)
    if font is not None:
        try:
            bbox = draw.textbbox((0, 0), "F", font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            if tw > 0 and th > 0:
                max_dim = size * 0.84
                scale = min(max_dim / tw, max_dim / th, 1.0)
                font = _fat_font(max(1, int(base * scale)))
                bbox = draw.textbbox((0, 0), "F", font=font)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
                x = (size - tw) / 2 - bbox[0]
                y = (size - th) / 2 - bbox[1]
                draw.text((x, y), "F", font=font, fill=BLACK)
                return
        except Exception:
            pass
    # Fallback: blockiges F aus Rechtecken
    cx, cy = size // 2, size // 2
    t = size * 0.20
    top = size * 0.09
    bot = size * 0.91
    left = cx - t / 2
    right = cx + t / 2
    draw.rectangle([left, top, right, bot], fill=BLACK)
    draw.rectangle([left, top, left + size * 0.44, top + t], fill=BLACK)
    draw.rectangle([left, cy - t / 2, left + size * 0.26, cy + t / 2], fill=BLACK)

def create_icon():
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
        for d in (base, os.path.join(base, "_internal"), os.path.join(base, "assets")):
            p = os.path.join(d, "ferdlworks.ico")
            if os.path.exists(p):
                return os.path.abspath(p)
        return os.path.join(base, "ferdlworks.ico")
    os.makedirs(ICON_DIR, exist_ok=True)
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Roter Punkt
    draw.ellipse([(4, 4), (size - 4, size - 4)], fill=RED, outline=RED_DARK, width=6)
    _draw_f(draw, size)
    img.save(ICON_PNG, "PNG")
    img.save(ICON_ICO, "ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    return ICON_ICO

def set_window_icon(window, master=None):
    icon_paths = [ICON_ICO]
    if master and hasattr(master, '_icon_path'):
        icon_paths.insert(0, master._icon_path)
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
        icon_paths += [os.path.join(base, "ferdlworks.ico"),
                       os.path.join(base, "_internal", "ferdlworks.ico")]
    for p in icon_paths:
        if os.path.exists(p):
            try:
                window.iconbitmap(p)
                return
            except Exception:
                continue

_auto_installed = False


def install_auto():
    """Setzt das App-Icon automatisch für ALLE Toplevel-Fenster – sofort bei
    der Erzeugung, also auch für noch nicht gemappte (unmapped) Fenster.

    CustomTkinter überschreibt 200 ms nach der Erzeugung selbst das Icon eines
    jeden CTkToplevel mit dem CustomTkinter-Icon. Deshalb wird zusätzlich
    ``iconbitmap`` gepatcht: Jeder Versuch, das CustomTkinter-Icon zu setzen,
    wird auf unser App-Icon umgebogen. Damit gewinnt in jedem Fall unser Icon.
    """
    global _auto_installed
    if _auto_installed:
        return
    _auto_installed = True

    _orig_init = tk.Toplevel.__init__

    def _patched_init(self, *args, **kwargs):
        _orig_init(self, *args, **kwargs)
        try:
            set_window_icon(self)
        except Exception:
            pass

    tk.Toplevel.__init__ = _patched_init

    _orig_iconbitmap = tk.Wm.iconbitmap

    def _patched_iconbitmap(self, bitmap=None, default=None):
        if isinstance(bitmap, str) and "CustomTkinter_icon_Windows" in bitmap:
            bitmap = ICON_ICO
        return _orig_iconbitmap(self, bitmap, default)

    tk.Wm.iconbitmap = _patched_iconbitmap
    tk.Wm.wm_iconbitmap = _patched_iconbitmap

def get_icon_path():
    return ICON_ICO

def get_png_path():
    return ICON_PNG

import os, sys
from PIL import Image, ImageDraw

ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
ICON_PNG = os.path.join(ICON_DIR, "ferdlworks.png")
ICON_ICO = os.path.join(ICON_DIR, "ferdlworks.ico")

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
    # Blauer Kreis
    draw.ellipse([(4, 4), (size - 4, size - 4)], fill=(0, 100, 210), outline=(0, 60, 160), width=4)
    # Weisser Blitz (keine Schriftarten nötig)
    cx, cy = size // 2, size // 2
    s = size // 8
    draw.polygon([(cx - s, cy - s*2), (cx + s, cy), (cx, cy), (cx + s, cy + s*2), (cx - s, cy)], fill=(255, 220, 50))
    img.save(ICON_PNG, "PNG")
    img.save(ICON_ICO, "ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
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

def get_icon_path():
    return ICON_ICO

def get_png_path():
    return ICON_PNG

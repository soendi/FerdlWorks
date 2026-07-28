import os, sys
from PIL import Image, ImageDraw, ImageFont

ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
ICON_PNG = os.path.join(ICON_DIR, "ferdlworks.png")
ICON_ICO = os.path.join(ICON_DIR, "ferdlworks.ico")

def create_icon():
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
        for name in ("ferdlworks.ico", "ferdlworks.png"):
            for d in (base, os.path.join(base, "assets"), os.path.join(base, "_internal", "assets")):
                p = os.path.join(d, name)
                if os.path.exists(p):
                    if name == "ferdlworks.ico":
                        return p
        return os.path.join(base, "ferdlworks.ico")
    os.makedirs(ICON_DIR, exist_ok=True)
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Blauer Kreis (statt rot – sofort erkennbar)
    draw.ellipse([(4, 4), (size - 4, size - 4)], fill=(30, 100, 200), outline=(10, 60, 150), width=4)

    # Weisse Schrift (statt schwarz)
    fs = size - 20
    for name in ("segoeui.ttf", "arial.ttf", "arialbd.ttf", "tahoma.ttf"):
        try:
            font = ImageFont.truetype(name, fs)
            break
        except:
            font = ImageFont.load_default()
    draw.text((size // 2, size // 2), "F", fill=(255, 255, 255), font=font, anchor="mm")

    img.save(ICON_PNG, "PNG")
    img.save(ICON_ICO, "ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    return ICON_ICO

def get_icon_path():
    return ICON_ICO

def get_png_path():
    return ICON_PNG

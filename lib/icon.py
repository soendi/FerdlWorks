import os, sys
from PIL import Image, ImageDraw, ImageFont

ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
ICON_PNG = os.path.join(ICON_DIR, "ferdlworks.png")
ICON_ICO = os.path.join(ICON_DIR, "ferdlworks.ico")

def create_icon():
    if getattr(sys, "frozen", False):
        for p in (ICON_ICO, ICON_PNG):
            if os.path.exists(p):
                return p
    os.makedirs(ICON_DIR, exist_ok=True)
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Hintergrund: abgerundetes Rechteck (dunkelrot)
    draw.rounded_rectangle([(3, 3), (size-3, size-3)], radius=36,
                           fill=(139, 0, 0), outline=(80, 0, 0), width=4)

    # Inneres Rechteck
    m = size // 6
    draw.rounded_rectangle([(m, m), (size-m, size-m)], radius=18,
                           fill=(35, 35, 35, 230))

    # Schrift laden
    try:
        font = ImageFont.truetype("segoeui.ttf", size // 2)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", size // 2)
        except:
            font = ImageFont.load_default()

    # Schatten vom F
    draw.text((size//2 + 3, size//2 + 3), "F", fill=(0, 0, 0, 100), font=font, anchor="mm")
    # F in hellrot
    draw.text((size//2, size//2), "F", fill=(220, 60, 60), font=font, anchor="mm")

    img.save(ICON_PNG, "PNG")
    img.save(ICON_ICO, "ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    return ICON_ICO

def get_icon_path():
    return ICON_ICO

def get_png_path():
    return ICON_PNG

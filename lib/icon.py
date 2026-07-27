import os
from PIL import Image, ImageDraw, ImageFont

ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
ICON_PNG = os.path.join(ICON_DIR, "ferdlworks.png")
ICON_ICO = os.path.join(ICON_DIR, "ferdlworks.ico")
ICON_SIZE = 64


def create_icon():
    if os.path.exists(ICON_PNG) and os.path.exists(ICON_ICO):
        return ICON_ICO
    os.makedirs(ICON_DIR, exist_ok=True)
    img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        [(2, 2), (ICON_SIZE - 2, ICON_SIZE - 2)],
        radius=8,
        fill=(139, 0, 0),
        outline=(90, 0, 0),
        width=2,
    )
    draw.rounded_rectangle(
        [(8, 8), (ICON_SIZE - 8, ICON_SIZE - 8)],
        radius=4,
        fill=(26, 26, 26),
    )
    try:
        font = ImageFont.truetype("segoeui.ttf", 20)
    except Exception:
        font = ImageFont.load_default()
    draw.text(
        (ICON_SIZE // 2, ICON_SIZE // 2),
        "F",
        fill=(139, 0, 0),
        font=font,
        anchor="mm",
    )
    img.save(ICON_PNG, "PNG")
    img.save(ICON_ICO, "ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    return ICON_ICO


def get_icon_path():
    return ICON_ICO


def get_png_path():
    return ICON_PNG

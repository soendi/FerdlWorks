import os
from PIL import Image, ImageDraw, ImageFont

ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
ICON_PNG = os.path.join(ICON_DIR, "ferdlworks.png")
ICON_ICO = os.path.join(ICON_DIR, "ferdlworks.ico")


def create_icon():
    if os.path.exists(ICON_ICO):
        return ICON_ICO
    os.makedirs(ICON_DIR, exist_ok=True)
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Hintergrund-Rahmen (dunkelrot)
    draw.rounded_rectangle(
        [(4, 4), (size - 4, size - 4)],
        radius=28,
        fill=(139, 0, 0),
        outline=(90, 0, 0),
        width=4,
    )
    # Inneres Rechteck (dunkelgrau)
    inner_margin = size // 8
    draw.rounded_rectangle(
        [(inner_margin, inner_margin), (size - inner_margin, size - inner_margin)],
        radius=14,
        fill=(26, 26, 26),
    )
    # Grosses F
    try:
        font = ImageFont.truetype("segoeui.ttf", size // 2)
    except Exception:
        font = ImageFont.load_default()
    draw.text(
        (size // 2, size // 2),
        "F",
        fill=(139, 0, 0),
        font=font,
        anchor="mm",
    )
    img.save(ICON_PNG, "PNG")
    img.save(ICON_ICO, "ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    return ICON_ICO


def get_icon_path():
    return ICON_ICO


def get_png_path():
    return ICON_PNG

"""One-off script: draws 5 stylized placeholder icons for the Flak armor
pieces (transparent PNG backgrounds) into assets/. Swap these for real
game screenshots/icons whenever you have them -- just point each piece's
"Icon image" field in Settings at your own file.
"""
import os

from PIL import Image, ImageDraw

SIZE = 128
FILL = (91, 99, 80, 255)       # olive drab
OUTLINE = (40, 45, 33, 255)    # dark outline
HIGHLIGHT = (150, 161, 128, 255)  # lighter accent
OUTLINE_W = 4

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")


def _canvas():
    return Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))


def draw_helmet():
    img = _canvas()
    d = ImageDraw.Draw(img)
    # dome
    d.pieslice([20, 14, 108, 102], 180, 360, fill=FILL, outline=OUTLINE, width=OUTLINE_W)
    d.rectangle([20, 58, 108, 92], fill=FILL, outline=OUTLINE, width=OUTLINE_W)
    # brim
    d.rectangle([14, 88, 114, 100], fill=FILL, outline=OUTLINE, width=OUTLINE_W)
    # visor slit
    d.rectangle([34, 68, 94, 78], fill=HIGHLIGHT, outline=OUTLINE, width=2)
    return img


def draw_chestpiece():
    img = _canvas()
    d = ImageDraw.Draw(img)
    body = [(64, 12), (108, 30), (114, 96), (64, 118), (14, 96), (20, 30)]
    d.polygon(body, fill=FILL, outline=OUTLINE)
    d.line([(64, 12), (64, 118)], fill=OUTLINE, width=OUTLINE_W)
    d.line([(30, 44), (98, 44)], fill=HIGHLIGHT, width=5)
    d.ellipse([50, 56, 78, 84], outline=HIGHLIGHT, width=4)
    return img


def draw_gauntlet():
    img = _canvas()
    d = ImageDraw.Draw(img)
    # wrist cuff
    d.rectangle([44, 78, 92, 118], fill=FILL, outline=OUTLINE, width=OUTLINE_W)
    # hand/palm
    d.rounded_rectangle([28, 40, 100, 84], radius=16, fill=FILL, outline=OUTLINE, width=OUTLINE_W)
    # fingers
    finger_w = 14
    for i, x in enumerate([30, 48, 66, 84]):
        d.rounded_rectangle([x, 12, x + finger_w, 46], radius=6, fill=FILL, outline=OUTLINE, width=3)
    d.line([(38, 60), (90, 60)], fill=HIGHLIGHT, width=4)
    return img


def draw_leggings():
    img = _canvas()
    d = ImageDraw.Draw(img)
    # waist band
    d.rounded_rectangle([18, 10, 110, 40], radius=10, fill=FILL, outline=OUTLINE, width=OUTLINE_W)
    # legs
    d.rounded_rectangle([20, 34, 58, 118], radius=10, fill=FILL, outline=OUTLINE, width=OUTLINE_W)
    d.rounded_rectangle([70, 34, 108, 118], radius=10, fill=FILL, outline=OUTLINE, width=OUTLINE_W)
    d.line([(30, 60), (30, 100)], fill=HIGHLIGHT, width=4)
    d.line([(98, 60), (98, 100)], fill=HIGHLIGHT, width=4)
    return img


def draw_boots():
    img = _canvas()
    d = ImageDraw.Draw(img)
    # shaft
    d.rounded_rectangle([34, 10, 78, 76], radius=8, fill=FILL, outline=OUTLINE, width=OUTLINE_W)
    # foot
    d.polygon(
        [(34, 66), (78, 66), (108, 92), (108, 110), (24, 110), (24, 84)],
        fill=FILL, outline=OUTLINE,
    )
    d.line([(24, 84), (108, 92)], fill=OUTLINE, width=2)
    d.line([(44, 30), (44, 60)], fill=HIGHLIGHT, width=4)
    d.line([(30, 96), (100, 100)], fill=HIGHLIGHT, width=4)
    return img


PIECE_DRAWERS = {
    "helmet": draw_helmet,
    "chest_plate": draw_chestpiece,
    "gauntlet": draw_gauntlet,
    "leggings": draw_leggings,
    "boots": draw_boots,
}


def generate():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    paths = {}
    for key, drawer in PIECE_DRAWERS.items():
        img = drawer()
        path = os.path.join(ASSETS_DIR, f"{key}.png")
        img.save(path)
        paths[key] = path
    return paths


if __name__ == "__main__":
    for key, path in generate().items():
        print(f"{key}: {path}")

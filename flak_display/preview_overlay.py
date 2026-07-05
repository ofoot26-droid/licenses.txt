"""Renders offline PNG mockups of the HUD with Pillow (no tkinter/mss/
pytesseract needed) so the layout can be eyeballed without Windows or a
display. Calls the exact same render.render_hud_frame() the live overlay
uses, with sample durability values instead of live OCR.

Usage: python preview_overlay.py
"""
import os

from PIL import Image

from bg_remove import remove_background
from config import load_config
import render

OUT_DIR = os.path.join(os.path.dirname(__file__), "preview_out")

# One sample value per piece (Helmet, Chest Plate, Gauntlet, Leggings,
# Boots), chosen to sweep across the color range for a representative demo.
SAMPLE_VALUES = [8, 32, 52, 78, 97]


def load_icon(piece, size):
    img = Image.open(piece["image_path"])
    img = remove_background(img)
    return img.resize((size, size), Image.LANCZOS)


def render_in_context(hud_img, screen_size=(1920, 1080)):
    from PIL import ImageDraw, ImageFont

    sw, sh = screen_size
    scene = Image.new("RGB", (sw, sh), (18, 22, 16))
    draw = ImageDraw.Draw(scene)
    draw.rectangle([0, 0, sw, sh // 2], fill=(30, 38, 28))
    draw.rectangle([0, sh // 2, sw, sh], fill=(22, 26, 18))
    try:
        font = ImageFont.load_default(size=16)
    except TypeError:
        font = ImageFont.load_default()
    draw.text((24, 24), "(mock game background for placement reference)", fill=(120, 130, 110), font=font)

    margin = 12
    x = sw - hud_img.width - margin
    y = (sh - hud_img.height) // 2
    scene.paste(hud_img, (x, y), hud_img)
    return scene


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    cfg = load_config()

    compact = render.render_hud_frame(cfg, SAMPLE_VALUES, expanded=False, load_icon=load_icon)
    expanded = render.render_hud_frame(cfg, SAMPLE_VALUES, expanded=True, load_icon=load_icon)

    compact.save(os.path.join(OUT_DIR, "hud_compact.png"))
    expanded.save(os.path.join(OUT_DIR, "hud_expanded_h_held.png"))

    zoom = 3
    compact.resize((compact.width * zoom, compact.height * zoom), Image.NEAREST).save(
        os.path.join(OUT_DIR, "hud_compact_zoomed.png")
    )
    expanded.resize((expanded.width * zoom, expanded.height * zoom), Image.NEAREST).save(
        os.path.join(OUT_DIR, "hud_expanded_zoomed.png")
    )

    render_in_context(compact).save(os.path.join(OUT_DIR, "hud_in_context.png"))

    print(f"Wrote previews to {OUT_DIR}")


if __name__ == "__main__":
    main()

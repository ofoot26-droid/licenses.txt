"""Renders offline PNG mockups of the HUD with Pillow (no tkinter/mss/
pytesseract needed) so the layout can be eyeballed without Windows or a
display. Mirrors overlay.py's drawing logic exactly via layout.dims()
and color_utils, using sample durability values instead of live OCR.

Usage: python preview_overlay.py
"""
import os

from PIL import Image, ImageDraw, ImageFont

import layout
from color_utils import get_color_for_value
from config import load_config

OUT_DIR = os.path.join(os.path.dirname(__file__), "preview_out")

# One sample value per piece (Helmet, Chest Plate, Gauntlet, Leggings,
# Boots), chosen to sweep across the color range for a representative demo.
SAMPLE_VALUES = [8, 32, 52, 78, 97]


def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def render_hud(cfg, values, expanded):
    n = len(cfg["pieces"])
    icon, bar_h, gap, pad, width, height = layout.dims(cfg["hud_scale"], n, expanded)

    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    y = pad
    for piece, value in zip(cfg["pieces"], values):
        icon_img = Image.open(piece["image_path"]).convert("RGBA").resize((icon, icon), Image.LANCZOS)
        canvas.paste(icon_img, (pad, y), icon_img)

        color = get_color_for_value(value, cfg["thresholds"], cfg["low_value"], cfg["high_value"])
        bar_y = y + icon + 3
        draw.rectangle([pad, bar_y, pad + icon, bar_y + bar_h], fill="#222222", outline="#000000")
        if value is not None:
            span = max(1, cfg["high_value"] - cfg["low_value"])
            frac = max(0.0, min(1.0, (value - cfg["low_value"]) / span))
            fill_w = int(icon * frac)
            if fill_w > 0:
                draw.rectangle([pad, bar_y, pad + fill_w, bar_y + bar_h], fill=color)

        row_h = icon + bar_h + 4
        if expanded:
            label = f"{piece['name']}: {value if value is not None else '?'}"
            draw.text((pad, bar_y + bar_h + 12), label, fill="#FFFFFF", font=_font(11))
            row_h += 14
        y += row_h + gap

    return canvas


def render_in_context(hud_img, screen_size=(1920, 1080)):
    sw, sh = screen_size
    scene = Image.new("RGB", (sw, sh), (18, 22, 16))
    draw = ImageDraw.Draw(scene)
    # Faint horizon + ground so it reads as "in-game" rather than a blank void.
    draw.rectangle([0, 0, sw, sh // 2], fill=(30, 38, 28))
    draw.rectangle([0, sh // 2, sw, sh], fill=(22, 26, 18))
    draw.text((24, 24), "(mock game background for placement reference)", fill=(120, 130, 110), font=_font(16))

    margin = 12
    x = sw - hud_img.width - margin
    y = (sh - hud_img.height) // 2
    scene.paste(hud_img, (x, y), hud_img)
    return scene


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    cfg = load_config()

    compact = render_hud(cfg, SAMPLE_VALUES, expanded=False)
    expanded = render_hud(cfg, SAMPLE_VALUES, expanded=True)

    compact.save(os.path.join(OUT_DIR, "hud_compact.png"))
    expanded.save(os.path.join(OUT_DIR, "hud_expanded_h_held.png"))

    # 3x zoom versions since the real HUD is small at default scale.
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

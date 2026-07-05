"""Shared HUD-frame renderer. Both the live overlay (overlay.py) and the
offline mockup (preview_overlay.py) call this so their output can never
drift apart -- it draws the rounded panel, icons, durability bars, and
(when expanded) the numeric labels, and returns a single RGBA PIL.Image.
"""
from PIL import Image, ImageDraw, ImageFont

import layout
from color_utils import get_color_for_value


def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def render_hud_frame(cfg, values, expanded, load_icon, key_color=None):
    """load_icon(piece, size) -> RGBA PIL.Image already sized/background-stripped.

    key_color: None renders a real transparent PNG background (for the
    offline preview). An (r, g, b) tuple instead fills the background
    with that opaque color, reserving it as the Windows colorkey hole
    that lets the corners outside the rounded panel show the game
    through the live overlay window.
    """
    n = len(cfg["pieces"])
    icon, bar_h, gap, pad, width, height = layout.dims(cfg["hud_scale"], n, expanded)
    scale = layout.scale_clamped(cfg["hud_scale"])

    if key_color is None:
        frame = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    else:
        frame = Image.new("RGBA", (width, height), key_color + (255,))
    draw = ImageDraw.Draw(frame)

    radius = int(layout.PANEL_RADIUS * scale)
    draw.rounded_rectangle(
        [0, 0, width - 1, height - 1],
        radius=radius,
        fill=layout.PANEL_FILL,
        outline=layout.PANEL_OUTLINE,
        width=layout.PANEL_OUTLINE_W,
    )

    y = pad
    for piece, value in zip(cfg["pieces"], values):
        icon_img = load_icon(piece, icon)
        frame.paste(icon_img, (pad, y), icon_img)

        color = get_color_for_value(value, cfg["thresholds"], cfg["low_value"], cfg["high_value"])
        bar_y = y + icon + 3
        draw.rectangle([pad, bar_y, pad + icon, bar_y + bar_h], fill=(34, 34, 34, 255), outline=(0, 0, 0, 255))
        if value is not None:
            span = max(1, cfg["high_value"] - cfg["low_value"])
            frac = max(0.0, min(1.0, (value - cfg["low_value"]) / span))
            fill_w = int(icon * frac)
            if fill_w > 0:
                draw.rectangle([pad, bar_y, pad + fill_w, bar_y + bar_h], fill=color)

        row_h = icon + bar_h + 4
        if expanded:
            label = f"{piece['name']}: {value if value is not None else '?'}"
            draw.text(
                (pad, bar_y + bar_h + layout.LABEL_TEXT_OFFSET),
                label, fill=(255, 255, 255, 255), font=_font(11),
            )
            row_h += layout.EXPANDED_ROW_EXTRA
        y += row_h + gap

    return frame

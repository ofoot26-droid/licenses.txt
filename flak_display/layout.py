"""HUD layout constants shared by the live overlay and the offline preview
renderer, so the preview always matches what actually gets drawn."""

BASE_ICON = 48
BASE_BAR_H = 8
BASE_GAP = 6
BASE_PAD = 10


def scale_clamped(hud_scale):
    return max(0.5, min(3.0, float(hud_scale)))


def dims(hud_scale, num_pieces, expanded):
    scale = scale_clamped(hud_scale)
    icon = int(BASE_ICON * scale)
    bar_h = int(BASE_BAR_H * scale)
    gap = int(BASE_GAP * scale)
    pad = int(BASE_PAD * scale)
    width = pad * 2 + icon
    height = pad * 2 + num_pieces * icon + (num_pieces - 1) * gap + num_pieces * (bar_h + 4)
    if expanded:
        height += num_pieces * 14
        width = max(width, pad * 2 + icon + 70)
    return icon, bar_h, gap, pad, width, height

"""HUD layout constants shared by the live overlay and the offline preview
renderer, so the preview always matches what actually gets drawn."""

BASE_ICON = 48
BASE_BAR_H = 8
BASE_GAP = 6
BASE_PAD = 10

# The panel behind the stacked pieces: a solid, rounded-corner card. Areas
# outside its rounded corners are left as the window's colorkey so the
# HUD's silhouette itself reads as a rounded rectangle floating over the
# game, rather than a hard-edged box.
PANEL_RADIUS = 14
PANEL_FILL = (24, 24, 26, 255)
PANEL_OUTLINE = (75, 78, 70, 255)
PANEL_OUTLINE_W = 2

# Extra height per row in the expanded (H held) view: the numeric label is
# drawn LABEL_TEXT_OFFSET below the bar and needs the full text height on
# top of that, or the last row's label clips against the panel edge.
LABEL_TEXT_OFFSET = 6
EXPANDED_ROW_EXTRA = 24


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
        height += num_pieces * EXPANDED_ROW_EXTRA
        width = max(width, pad * 2 + icon + 70)
    return icon, bar_h, gap, pad, width, height

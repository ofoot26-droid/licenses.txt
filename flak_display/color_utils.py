"""Maps a durability value to one of the 7 configured threshold colors."""
from config import COLOR_STOPS


def get_color_for_value(value, thresholds, low_value, high_value):
    """thresholds: dict of color_key -> breakpoint value, ascending in COLOR_STOPS order.

    Each breakpoint is the highest value still classified as that color; a
    value at or below thresholds['dark_red'] is dark red, a value above the
    second-to-last breakpoint (yellow_green) up to high_value is green.
    """
    if value is None:
        return "#555555"  # unknown / OCR read failed
    value = max(low_value, min(high_value, value))
    for color_key, _label, hex_color in COLOR_STOPS:
        breakpoint = thresholds.get(color_key, high_value)
        if value <= breakpoint:
            return hex_color
    return COLOR_STOPS[-1][2]


def bar_fill_fraction(value, low_value, high_value):
    if value is None:
        return 0.0
    span = max(1, high_value - low_value)
    return max(0.0, min(1.0, (value - low_value) / span))

"""Automatic background stripping for user-supplied icon images.

Flood-fills inward from the image border, clearing to transparent any
pixel connected to the edge whose color is close to the border's own
(most common) color. Handles the common case of an icon rendered on a
flat white/gray background without needing any manual editing.
"""
from collections import Counter, deque

DEFAULT_TOLERANCE = 30


def _close(a, b, tolerance):
    return abs(a[0] - b[0]) <= tolerance and abs(a[1] - b[1]) <= tolerance and abs(a[2] - b[2]) <= tolerance


def remove_background(img, tolerance=DEFAULT_TOLERANCE):
    """img: a PIL Image. Returns a new RGBA image with the background
    flood-cleared to alpha 0."""
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()

    border_colors = Counter()
    for x in range(w):
        border_colors[px[x, 0][:3]] += 1
        border_colors[px[x, h - 1][:3]] += 1
    for y in range(h):
        border_colors[px[0, y][:3]] += 1
        border_colors[px[w - 1, y][:3]] += 1
    if not border_colors:
        return img
    bg_color = border_colors.most_common(1)[0][0]

    visited = bytearray(w * h)
    queue = deque()

    def maybe_enqueue(x, y):
        if not (0 <= x < w and 0 <= y < h):
            return
        idx = y * w + x
        if visited[idx]:
            return
        if _close(px[x, y][:3], bg_color, tolerance):
            visited[idx] = 1
            queue.append((x, y))

    for x in range(w):
        maybe_enqueue(x, 0)
        maybe_enqueue(x, h - 1)
    for y in range(h):
        maybe_enqueue(0, y)
        maybe_enqueue(w - 1, y)

    while queue:
        x, y = queue.popleft()
        r, g, b, _a = px[x, y]
        px[x, y] = (r, g, b, 0)
        maybe_enqueue(x + 1, y)
        maybe_enqueue(x - 1, y)
        maybe_enqueue(x, y + 1)
        maybe_enqueue(x, y - 1)

    return img

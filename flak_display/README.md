# Flak Display

A small, transparent, always-on-top overlay for ARK: Survival Ascended that
shows live durability for your Flak armor (Helmet, Chest Plate, Gauntlet,
Leggings, Boots) as a color bar under each piece's icon.

## Requirements

- Windows (uses Windows-only APIs for true transparency and click-through;
  it will still run on other platforms for testing, but the overlay
  background won't be see-through and clicks won't pass through it).
- Python 3.9+
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) installed
  separately (this is a system program, not a pip package). After
  installing, either add it to your PATH or set its full path in
  `flak_config.json` under `"tesseract_cmd"`, e.g.
  `"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"`.

## Setup

```bash
pip install -r requirements.txt
python main.py
```

On first run a `flak_config.json` is created next to `main.py` with
defaults you can edit from the Settings window.

## Configuring it

Open **Settings** from the control window and, for each armor piece:

1. **Icon image** — browse to the image you want shown for that piece.
   Until you set one, a placeholder square is shown.
2. **X / Y / Width / Height** — the screen region ARK draws that piece's
   durability number in (e.g. the inventory tooltip). Hover your mouse
   over that spot in-game and read the coordinates from the "Coordinate
   helper" panel at the bottom of the Settings window, then use **Test
   read** to confirm the number OCRs correctly.

Also set:

- **Low value / High value** — the durability range (defaults 0-100).
- **Color thresholds** — the value at or below which each color applies,
  from Dark Red (worst) up through Red, Orange, Amber Orange, Yellow,
  Yellow Green, to Green (best).
- **Scale** — resizes the overlay. Its position is fixed: vertically
  centered on the right edge of your screen.

Click **Save** to apply changes to the running overlay immediately.

## Controls

- The overlay normally shows just icons + color bars.
- Hold **H** while playing to switch to the expanded view, which adds the
  numeric durability value next to each bar.

## Notes

- `keyboard` (used for the H hold-to-expand behavior) may require running
  the app as Administrator on Windows to catch key presses globally.
- OCR runs about every 750ms per piece; if reads are unreliable, widen the
  region slightly or increase the in-game UI/text scale.

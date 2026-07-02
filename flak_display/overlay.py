"""The transparent, click-through Flak durability HUD."""
import platform
import tkinter as tk

from PIL import Image, ImageDraw, ImageFont, ImageTk

from color_utils import get_color_for_value
from ocr import read_value
import layout
import mss

TRANSPARENT_KEY = "#010101"  # background color treated as transparent (Windows only)
POLL_MS = 750


def _make_placeholder_icon(label, size):
    img = Image.new("RGBA", (size, size), (40, 40, 40, 235))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, size - 1, size - 1], outline=(160, 160, 160, 255), width=1)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    text = label[:1]
    draw.text((size / 2, size / 2), text, fill=(220, 220, 220, 255), anchor="mm", font=font)
    return img


def _enable_windows_clickthrough(hwnd):
    import ctypes

    GWL_EXSTYLE = -20
    WS_EX_LAYERED = 0x80000
    WS_EX_TRANSPARENT = 0x20
    user32 = ctypes.windll.user32
    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT)


class FlakOverlay:
    def __init__(self, get_config):
        """get_config: callable returning the live config dict (so edits in the
        settings menu are picked up without restarting the overlay)."""
        self.get_config = get_config
        self.expanded = False
        self._icon_cache = {}
        self._photo_refs = []

        self.root = tk.Toplevel()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=TRANSPARENT_KEY)
        if platform.system() == "Windows":
            self.root.attributes("-transparentcolor", TRANSPARENT_KEY)

        self.canvas = tk.Canvas(self.root, bg=TRANSPARENT_KEY, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self._sct = mss.mss()

        self.root.update_idletasks()
        if platform.system() == "Windows":
            try:
                hwnd = int(self.root.frame(), 16)
                _enable_windows_clickthrough(hwnd)
            except Exception:
                pass

        self._reposition()
        self._tick_ocr()
        self._tick_render()
        self._tick_hotkey()

    # -- layout -----------------------------------------------------------
    def _scale(self):
        cfg = self.get_config()
        return max(0.5, min(3.0, float(cfg.get("hud_scale", 1.0))))

    def _dims(self):
        n = len(self.get_config()["pieces"])
        return layout.dims(self._scale(), n, self.expanded)

    def _reposition(self):
        icon, bar_h, gap, pad, width, height = self._dims()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        margin = 12
        x = screen_w - width - margin
        y = (screen_h - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.canvas.config(width=width, height=height)

    # -- data ---------------------------------------------------------------
    def _tick_ocr(self):
        cfg = self.get_config()
        self._latest_values = getattr(self, "_latest_values", [None] * len(cfg["pieces"]))
        values = []
        for piece in cfg["pieces"]:
            region = tuple(piece.get("region", [0, 0, 0, 0]))
            values.append(read_value(region, sct=self._sct))
        self._latest_values = values
        self.root.after(POLL_MS, self._tick_ocr)

    def _tick_hotkey(self):
        try:
            import keyboard

            self.expanded = keyboard.is_pressed("h")
        except Exception:
            pass
        self.root.after(80, self._tick_hotkey)

    # -- rendering ------------------------------------------------------
    def _get_icon(self, piece, size):
        key = (piece["name"], piece.get("image_path", ""), size)
        if key in self._icon_cache:
            return self._icon_cache[key]
        path = piece.get("image_path", "")
        try:
            if path:
                img = Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS)
            else:
                raise FileNotFoundError
        except Exception:
            img = _make_placeholder_icon(piece["name"], size)
        photo = ImageTk.PhotoImage(img)
        self._icon_cache[key] = photo
        return photo

    def _tick_render(self):
        self._reposition()
        cfg = self.get_config()
        icon, bar_h, gap, pad, width, height = self._dims()
        self.canvas.delete("all")
        self._photo_refs.clear()

        values = getattr(self, "_latest_values", [None] * len(cfg["pieces"]))
        y = pad
        for piece, value in zip(cfg["pieces"], values):
            photo = self._get_icon(piece, icon)
            self._photo_refs.append(photo)
            self.canvas.create_image(pad, y, image=photo, anchor="nw")

            color = get_color_for_value(
                value, cfg["thresholds"], cfg["low_value"], cfg["high_value"]
            )
            bar_y = y + icon + 3
            self.canvas.create_rectangle(
                pad, bar_y, pad + icon, bar_y + bar_h,
                fill="#222222", outline="#000000",
            )
            if value is not None:
                span = max(1, cfg["high_value"] - cfg["low_value"])
                frac = max(0.0, min(1.0, (value - cfg["low_value"]) / span))
                fill_w = int(icon * frac)
                if fill_w > 0:
                    self.canvas.create_rectangle(
                        pad, bar_y, pad + fill_w, bar_y + bar_h,
                        fill=color, outline="",
                    )
            row_h = icon + bar_h + 4
            if self.expanded:
                label = f"{piece['name']}: {value if value is not None else '?'}"
                self.canvas.create_text(
                    pad, bar_y + bar_h + 12, text=label, fill="#FFFFFF",
                    anchor="nw", font=("Segoe UI", 8),
                )
                row_h += 14
            y += row_h + gap

        self.root.after(150, self._tick_render)

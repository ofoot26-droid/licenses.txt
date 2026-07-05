"""The transparent, click-through Flak durability HUD: a rounded-rect
panel with the 5 armor pieces stacked vertically inside it, floating
over the game."""
import platform
import tkinter as tk

from PIL import Image, ImageDraw, ImageFont, ImageTk

from bg_remove import remove_background
from ocr import read_value
import mss
import render

TRANSPARENT_KEY_HEX = "#010101"  # background color treated as transparent (Windows only)
TRANSPARENT_KEY_RGB = (1, 1, 1)
POLL_MS = 750


def _make_placeholder_icon(label, size):
    img = Image.new("RGBA", (size, size), (40, 40, 40, 235))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, size - 1, size - 1], outline=(160, 160, 160, 255), width=1)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    draw.text((size / 2, size / 2), label[:1], fill=(220, 220, 220, 255), anchor="mm", font=font)
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
        self._frame_photo = None  # keep a live reference so Tk doesn't GC it

        self.root = tk.Toplevel()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=TRANSPARENT_KEY_HEX)
        if platform.system() == "Windows":
            self.root.attributes("-transparentcolor", TRANSPARENT_KEY_HEX)

        self.canvas = tk.Canvas(self.root, bg=TRANSPARENT_KEY_HEX, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self._canvas_image_id = None

        self._sct = mss.mss()

        self.root.update_idletasks()
        if platform.system() == "Windows":
            try:
                hwnd = int(self.root.frame(), 16)
                _enable_windows_clickthrough(hwnd)
            except Exception:
                pass

        self._tick_ocr()
        self._tick_render()
        self._tick_hotkey()

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

    # -- icons ------------------------------------------------------------
    def _load_icon(self, piece, size):
        key = (piece["name"], piece.get("image_path", ""), size)
        if key in self._icon_cache:
            return self._icon_cache[key]
        path = piece.get("image_path", "")
        try:
            if not path:
                raise FileNotFoundError
            img = Image.open(path)
            img = remove_background(img)
            img = img.resize((size, size), Image.LANCZOS)
        except Exception:
            img = _make_placeholder_icon(piece["name"], size)
        self._icon_cache[key] = img
        return img

    # -- rendering ------------------------------------------------------
    def _reposition(self, width, height):
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        margin = 12
        x = screen_w - width - margin
        y = (screen_h - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.canvas.config(width=width, height=height)

    def _tick_render(self):
        cfg = self.get_config()
        values = getattr(self, "_latest_values", [None] * len(cfg["pieces"]))

        frame = render.render_hud_frame(
            cfg, values, self.expanded, self._load_icon, key_color=TRANSPARENT_KEY_RGB
        )
        self._reposition(frame.width, frame.height)

        self._frame_photo = ImageTk.PhotoImage(frame)
        if self._canvas_image_id is None:
            self._canvas_image_id = self.canvas.create_image(0, 0, image=self._frame_photo, anchor="nw")
        else:
            self.canvas.itemconfig(self._canvas_image_id, image=self._frame_photo)

        self.root.after(150, self._tick_render)

"""Settings menu: size, per-piece icon/coordinates, value range, and the
7 color-threshold breakpoints."""
import tkinter as tk
from tkinter import filedialog, ttk

from config import COLOR_STOPS, save_config
from ocr import read_value


class ScrollableFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.inner = ttk.Frame(canvas)
        self.inner.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")


class ConfigWindow:
    def __init__(self, root, config, on_save=None):
        self.config = config
        self.on_save = on_save
        self.win = tk.Toplevel(root)
        self.win.title("Flak Display Settings")
        self.win.geometry("420x640")

        scroller = ScrollableFrame(self.win)
        scroller.pack(fill="both", expand=True)
        body = scroller.inner

        # -- size --------------------------------------------------------
        size_frame = ttk.LabelFrame(body, text="Display size (position is fixed: right edge, vertically centered)")
        size_frame.pack(fill="x", padx=8, pady=6)
        self.scale_var = tk.DoubleVar(value=config.get("hud_scale", 1.0))
        ttk.Label(size_frame, text="Scale (0.5 - 3.0):").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        ttk.Spinbox(
            size_frame, from_=0.5, to=3.0, increment=0.1, textvariable=self.scale_var, width=8
        ).grid(row=0, column=1, padx=4, pady=4)

        # -- value range ---------------------------------------------------
        range_frame = ttk.LabelFrame(body, text="Durability range")
        range_frame.pack(fill="x", padx=8, pady=6)
        self.low_var = tk.IntVar(value=config.get("low_value", 0))
        self.high_var = tk.IntVar(value=config.get("high_value", 100))
        ttk.Label(range_frame, text="Low value:").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(range_frame, textvariable=self.low_var, width=8).grid(row=0, column=1, padx=4)
        ttk.Label(range_frame, text="High value:").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        ttk.Entry(range_frame, textvariable=self.high_var, width=8).grid(row=0, column=3, padx=4)

        # -- color thresholds ------------------------------------------------
        thresh_frame = ttk.LabelFrame(body, text="Color thresholds (value at/below this = that color)")
        thresh_frame.pack(fill="x", padx=8, pady=6)
        self.threshold_vars = {}
        thresholds = config.get("thresholds", {})
        for i, (key, label, hex_color) in enumerate(COLOR_STOPS):
            swatch = tk.Label(thresh_frame, bg=hex_color, width=2)
            swatch.grid(row=i, column=0, padx=4, pady=2)
            ttk.Label(thresh_frame, text=f"Input value, {label}:").grid(row=i, column=1, sticky="w", padx=4)
            var = tk.IntVar(value=thresholds.get(key, 0))
            ttk.Entry(thresh_frame, textvariable=var, width=8).grid(row=i, column=2, padx=4, pady=2)
            self.threshold_vars[key] = var

        # -- pieces ------------------------------------------------------
        self.piece_widgets = []
        for piece in config.get("pieces", []):
            self.piece_widgets.append(self._build_piece_section(body, piece))

        # -- mouse position helper -------------------------------------------
        pos_frame = ttk.LabelFrame(body, text="Coordinate helper")
        pos_frame.pack(fill="x", padx=8, pady=6)
        self.pos_label = ttk.Label(pos_frame, text="Move mouse over the game to find x, y")
        self.pos_label.pack(anchor="w", padx=4, pady=4)
        self._poll_mouse()

        # -- actions -------------------------------------------------------
        action_frame = ttk.Frame(body)
        action_frame.pack(fill="x", padx=8, pady=10)
        ttk.Button(action_frame, text="Save", command=self._save).pack(side="left", padx=4)
        self.status_label = ttk.Label(action_frame, text="")
        self.status_label.pack(side="left", padx=8)

    def _build_piece_section(self, parent, piece):
        frame = ttk.LabelFrame(parent, text=piece["name"])
        frame.pack(fill="x", padx=8, pady=6)

        path_var = tk.StringVar(value=piece.get("image_path", ""))
        ttk.Label(frame, text="Icon image:").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        ttk.Entry(frame, textvariable=path_var, width=26).grid(row=0, column=1, columnspan=3, padx=4, pady=2)

        def browse():
            path = filedialog.askopenfilename(
                title=f"Choose icon for {piece['name']}",
                filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")],
            )
            if path:
                path_var.set(path)

        ttk.Button(frame, text="Browse...", command=browse).grid(row=0, column=4, padx=4)

        region = piece.get("region", [0, 0, 60, 20])
        x_var, y_var, w_var, h_var = (
            tk.IntVar(value=region[0]),
            tk.IntVar(value=region[1]),
            tk.IntVar(value=region[2]),
            tk.IntVar(value=region[3]),
        )
        labels = ["X:", "Y:", "Width:", "Height:"]
        for i, (lbl, var) in enumerate(zip(labels, [x_var, y_var, w_var, h_var])):
            ttk.Label(frame, text=lbl).grid(row=1, column=i * 1, sticky="e", padx=2, pady=2)
            ttk.Entry(frame, textvariable=var, width=6).grid(row=2, column=i, padx=2, pady=2)

        result_var = tk.StringVar(value="")

        def test_read():
            value = read_value((x_var.get(), y_var.get(), w_var.get(), h_var.get()))
            result_var.set(f"Read: {value if value is not None else 'no match'}")

        ttk.Button(frame, text="Test read", command=test_read).grid(row=3, column=0, columnspan=2, pady=4, sticky="w")
        ttk.Label(frame, textvariable=result_var).grid(row=3, column=2, columnspan=3, sticky="w")

        return {
            "name": piece["name"],
            "path_var": path_var,
            "x_var": x_var,
            "y_var": y_var,
            "w_var": w_var,
            "h_var": h_var,
        }

    def _poll_mouse(self):
        x = self.win.winfo_pointerx()
        y = self.win.winfo_pointery()
        self.pos_label.config(text=f"Mouse position: x={x}, y={y}")
        self.win.after(200, self._poll_mouse)

    def _save(self):
        self.config["hud_scale"] = self.scale_var.get()
        self.config["low_value"] = self.low_var.get()
        self.config["high_value"] = self.high_var.get()
        self.config["thresholds"] = {k: v.get() for k, v in self.threshold_vars.items()}
        pieces = []
        for w in self.piece_widgets:
            pieces.append({
                "name": w["name"],
                "image_path": w["path_var"].get(),
                "region": [w["x_var"].get(), w["y_var"].get(), w["w_var"].get(), w["h_var"].get()],
            })
        self.config["pieces"] = pieces
        save_config(self.config)
        self.status_label.config(text="Saved.")
        if self.on_save:
            self.on_save()

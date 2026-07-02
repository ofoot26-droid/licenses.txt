"""Entry point: launches the Flak durability overlay plus its settings menu.

Run with:  python main.py
"""
import tkinter as tk
from tkinter import ttk

from config import load_config, save_config
from config_gui import ConfigWindow
from ocr import configure_tesseract
from overlay import FlakOverlay


class App:
    def __init__(self):
        self.config = load_config()
        configure_tesseract(self.config.get("tesseract_cmd", ""))

        self.root = tk.Tk()
        self.root.title("Flak Display Control")
        self.root.geometry("260x120")

        ttk.Label(self.root, text="Flak Display is running.").pack(pady=(16, 4))
        ttk.Label(self.root, text="Hold H in-game for the expanded view.").pack()
        ttk.Button(self.root, text="Open Settings", command=self.open_settings).pack(pady=8)
        ttk.Button(self.root, text="Quit", command=self.root.destroy).pack()

        self.overlay = FlakOverlay(get_config=lambda: self.config)

    def open_settings(self):
        def on_save():
            configure_tesseract(self.config.get("tesseract_cmd", ""))

        ConfigWindow(self.root, self.config, on_save=on_save)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()

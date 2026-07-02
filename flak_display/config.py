"""Loading, saving, and defaults for the Flak display configuration."""
import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "flak_config.json")

PIECE_NAMES = ["Helmet", "Chest Plate", "Gauntlet", "Leggings", "Boots"]

# Ordered low -> high. Each entry is (color_key, display_label, hex_color).
COLOR_STOPS = [
    ("dark_red", "Dark Red", "#8B0000"),
    ("red", "Red", "#E31C1C"),
    ("orange", "Orange", "#FF7F00"),
    ("amber_orange", "Amber Orange", "#FFBF00"),
    ("yellow", "Yellow", "#FFEA00"),
    ("yellow_green", "Yellow Green", "#B5D400"),
    ("green", "Green", "#2ECC40"),
]

DEFAULT_CONFIG = {
    "hud_scale": 1.0,
    "low_value": 0,
    "high_value": 100,
    "thresholds": {
        "dark_red": 10,
        "red": 25,
        "orange": 40,
        "amber_orange": 55,
        "yellow": 70,
        "yellow_green": 85,
        "green": 100,
    },
    "tesseract_cmd": "",
    "pieces": [
        {"name": name, "image_path": "", "region": [0, 0, 60, 20]}
        for name in PIECE_NAMES
    ],
}


def load_config():
    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return json.loads(json.dumps(DEFAULT_CONFIG))
    with open(CONFIG_PATH, "r") as f:
        data = json.load(f)
    # Backfill any missing keys from defaults (e.g. after an upgrade).
    merged = json.loads(json.dumps(DEFAULT_CONFIG))
    merged.update({k: v for k, v in data.items() if k != "thresholds"})
    if "thresholds" in data:
        merged["thresholds"].update(data["thresholds"])
    if "pieces" in data and len(data["pieces"]) == len(PIECE_NAMES):
        merged["pieces"] = data["pieces"]
    return merged


def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

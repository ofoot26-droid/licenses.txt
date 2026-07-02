"""Reads a durability number from a screen region via Tesseract OCR."""
import re

import mss
import pytesseract
from PIL import Image, ImageOps

_NUMBER_RE = re.compile(r"\d+")


def configure_tesseract(tesseract_cmd):
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd


def _preprocess(img):
    """Upscale + grayscale + threshold so small in-game digits OCR cleanly."""
    img = img.convert("L")
    img = img.resize((img.width * 4, img.height * 4), Image.LANCZOS)
    img = ImageOps.autocontrast(img)
    img = img.point(lambda p: 255 if p > 140 else 0)
    return img


def read_value(region, sct=None):
    """region: (x, y, width, height) in screen coordinates. Returns int or None."""
    x, y, w, h = region
    if w <= 0 or h <= 0:
        return None
    monitor = {"left": x, "top": y, "width": w, "height": h}
    owns_sct = sct is None
    if owns_sct:
        sct = mss.mss()
    try:
        shot = sct.grab(monitor)
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        img = _preprocess(img)
        text = pytesseract.image_to_string(
            img, config="--psm 7 -c tessedit_char_whitelist=0123456789"
        )
        match = _NUMBER_RE.search(text)
        return int(match.group()) if match else None
    except Exception:
        return None
    finally:
        if owns_sct:
            sct.close()

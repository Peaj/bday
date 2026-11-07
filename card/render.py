#!/usr/bin/env python3
"""Render the card for print.

Writes, next to this script:
- card-front.png, card-back.png: 2480 x 1748 px at 300 dpi (A5 landscape, trimmed size)
- card-front-bleed.jpg, card-back-bleed.jpg: the same with 3 mm bleed on every side
- print-sheet.pdf: A4 landscape, page 1 front, page 2 back, centred with crop marks

Usage: py -3 card/render.py
Needs Microsoft Edge (or Chrome) and Pillow.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
W, H, BLEED = 2480, 1748, 36
BROWSERS = [
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
]


def headless(browser, args):
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run([str(browser), "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        f"--user-data-dir={profile}", "--force-device-scale-factor=1",
                        "--virtual-time-budget=2000", *args],
                       check=True, capture_output=True, timeout=180)


def screenshot(browser, html, out, w, h, query=""):
    png = out.with_suffix(".png")
    headless(browser, [f"--window-size={w},{h}", f"--screenshot={png}", html.as_uri() + query])
    img = Image.open(png).convert("RGB")
    if img.size != (w, h):
        sys.exit(f"{png.name}: got {img.size}, expected {(w, h)}")
    if out.suffix == ".jpg":
        png.unlink()
        img.save(out, quality=93, dpi=(300, 300), subsampling=0)
    else:
        img.save(out, dpi=(300, 300))
    print(f"{out.name}: {w}x{h} px, 300 dpi")


def main():
    browser = next((b for b in BROWSERS if b.is_file()), None)
    if not browser:
        sys.exit("Edge or Chrome not found.")
    for side in ("front", "back"):
        html = HERE / f"{side}.html"
        screenshot(browser, html, HERE / f"card-{side}.png", W, H)
        screenshot(browser, html, HERE / f"card-{side}-bleed.jpg", W + 2 * BLEED, H + 2 * BLEED, "?bleed")
    pdf = HERE / "print-sheet.pdf"
    headless(browser, ["--no-pdf-header-footer", f"--print-to-pdf={pdf}", (HERE / "print-sheet.html").as_uri()])
    print(f"{pdf.name}: {pdf.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()

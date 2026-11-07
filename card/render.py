#!/usr/bin/env python3
"""Render the card for print.

The card is designed at 2480 x 1748 CSS px and rendered at CARD_WIDTH_MM wide (300 dpi),
sized to fit a 17 x 11.5 cm envelope when folded.

Public files (committed, linked on the page), next to this script:
- card-front.png, card-back.png: one panel at print size, 300 dpi
- card-front-bleed.jpg, card-back-bleed.jpg: the same with about 3 mm bleed on every side
- folding-card.pdf: one-sided A4 sheet; cut out and fold to the card

Private files in private/ (gitignored), only if private/guest-qr.svg exists:
- the same back and folding card with the guest pass QR code. Never commit or publish these.

Usage: py -3 card/render.py
Needs Microsoft Edge (or Chrome) and Pillow.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
PRIVATE = HERE / "private"
DESIGN_W, DESIGN_H, BLEED = 2480, 1748, 48     # CSS px; bleed must match html.bleed in card.css
CARD_WIDTH_MM = 155
DPI = 300
SCALE = CARD_WIDTH_MM / 25.4 * DPI / DESIGN_W
BROWSERS = [
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
]


def px_to_mm(px):
    return px / DPI * 25.4


def headless(browser, args, scale=1.0):
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run([str(browser), "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        f"--user-data-dir={profile}", f"--force-device-scale-factor={scale:.6f}",
                        "--virtual-time-budget=2000", *args],
                       check=True, capture_output=True, timeout=180)


def screenshot(browser, html, out, w, h, query=""):
    png = out.with_suffix(".png")
    headless(browser, [f"--window-size={w},{h}", f"--screenshot={png}", html.as_uri() + query], SCALE)
    img = Image.open(png).convert("RGB")
    expect = (round(w * SCALE), round(h * SCALE))
    if abs(img.size[0] - expect[0]) > 1 or abs(img.size[1] - expect[1]) > 1:
        sys.exit(f"{png.name}: got {img.size}, expected about {expect}")
    if out.suffix == ".jpg":
        png.unlink()
        img.save(out, quality=93, dpi=(DPI, DPI), subsampling=0)
    else:
        img.save(out, dpi=(DPI, DPI))
    print(f"{out.relative_to(HERE)}: {img.size[0]}x{img.size[1]} px = "
          f"{px_to_mm(img.size[0]):.1f} x {px_to_mm(img.size[1]):.1f} mm")
    return img.size


def side(browser, name, out_dir, query=""):
    html = HERE / f"{name}.html"
    size = screenshot(browser, html, out_dir / f"card-{name}.png", DESIGN_W, DESIGN_H, query)
    sep = "&" if query else "?"
    screenshot(browser, html, out_dir / f"card-{name}-bleed.jpg",
               DESIGN_W + 2 * BLEED, DESIGN_H + 2 * BLEED, query + sep + "bleed")
    return size


def pdf(browser, out, size, private=False):
    q = f"?pw={px_to_mm(size[0]):.3f}&ph={px_to_mm(size[1]):.3f}&b={px_to_mm(BLEED * SCALE):.3f}"
    if private:
        q += "&private"
    headless(browser, ["--no-pdf-header-footer", f"--print-to-pdf={out}", (HERE / "folding-card.html").as_uri() + q])
    print(f"{out.relative_to(HERE)}: {out.stat().st_size // 1024} KB")


def main():
    browser = next((b for b in BROWSERS if b.is_file()), None)
    if not browser:
        sys.exit("Edge or Chrome not found.")
    size = side(browser, "front", HERE)
    side(browser, "back", HERE)
    pdf(browser, HERE / "folding-card.pdf", size)
    if (PRIVATE / "guest-qr.svg").is_file():
        side(browser, "back", PRIVATE, "?guest")
        pdf(browser, PRIVATE / "folding-card-guest-pass.pdf", size, private=True)


if __name__ == "__main__":
    main()

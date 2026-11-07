#!/usr/bin/env python3
"""Render the card for print.

Public files (committed, linked on the page), next to this script:
- card-front.png, card-back.png: 2480 x 1748 px at 300 dpi (A5 landscape, trimmed size)
- card-front-bleed.jpg, card-back-bleed.jpg: the same with 3 mm bleed on every side
- folding-card.pdf: one-sided A4 sheet, printed borderless and folded to an A5 card

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
    print(f"{out.relative_to(HERE)}: {w}x{h} px, 300 dpi")


def side(browser, name, out_dir, query=""):
    html = HERE / f"{name}.html"
    screenshot(browser, html, out_dir / f"card-{name}.png", W, H, query)
    sep = "&" if query else "?"
    screenshot(browser, html, out_dir / f"card-{name}-bleed.jpg", W + 2 * BLEED, H + 2 * BLEED, query + sep + "bleed")


def pdf(browser, out, query=""):
    headless(browser, ["--no-pdf-header-footer", f"--print-to-pdf={out}", (HERE / "folding-card.html").as_uri() + query])
    print(f"{out.relative_to(HERE)}: {out.stat().st_size // 1024} KB")


def main():
    browser = next((b for b in BROWSERS if b.is_file()), None)
    if not browser:
        sys.exit("Edge or Chrome not found.")
    side(browser, "front", HERE)
    side(browser, "back", HERE)
    pdf(browser, HERE / "folding-card.pdf")
    if (PRIVATE / "guest-qr.svg").is_file():
        side(browser, "back", PRIVATE, "?guest")
        pdf(browser, PRIVATE / "folding-card-guest-pass.pdf", "?private")


if __name__ == "__main__":
    main()

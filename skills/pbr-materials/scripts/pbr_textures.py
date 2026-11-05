#!/usr/bin/env python3
"""Find PBR texture sets in a folder and pack channels into the textures a PBR shader expects.

Commands:
    scan <folder>
        Groups texture files by name (rock_albedo.png, rock_normal.png, ...) and lists which maps each set
        has and which are missing. Read-only.

    pack -o <out.png> --r <src> --g <src> --b <src> [--a <src>] [--size 2048]
        Builds one image from single channels. <src> is either an image path with an optional channel
        (rock_roughness.png, rock_orm.png:g), a constant 0-255 (e.g. 0 for "not metal"), and can be
        inverted with a leading ~ (~rock_gloss.png turns gloss into roughness).

    flip-green <normal.png> -o <out.png>
        Converts a normal map between OpenGL (Y+) and DirectX (Y-) conventions.

Never overwrites an existing output file unless --force is given. Needs Pillow (pip install pillow).
"""
import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

try:
    from PIL import Image, ImageChops
except ImportError:
    sys.exit("Pillow is missing. Install it with:  py -m pip install pillow")

IMAGE_EXT = {".png", ".tga", ".jpg", ".jpeg", ".tif", ".tiff", ".exr", ".bmp", ".psd"}
MAP_NAMES = {
    "albedo": ["albedo", "basecolor", "base_color", "basecolour", "diffuse", "color", "colour", "col", "diff"],
    "normal": ["normal", "normalgl", "normaldx", "nrm", "nor", "norm", "nml"],
    "roughness": ["roughness", "rough", "rgh"],
    "gloss": ["gloss", "glossiness", "smoothness"],
    "metalness": ["metalness", "metallic", "metal", "met"],
    "ao": ["ao", "ambientocclusion", "ambient_occlusion", "occlusion", "occ"],
    "height": ["height", "displacement", "disp", "displ", "bump"],
    "emission": ["emission", "emissive", "emit", "glow"],
    "opacity": ["opacity", "alpha", "mask"],
}
ALIASES = {alias: kind for kind, names in MAP_NAMES.items() for alias in names}
def classify(stem):
    """'rock_wall_Albedo_4k' -> ('rock_wall', 'albedo'); 'x_ambient_occlusion' -> ('x', 'ao')."""
    s = re.sub(r"[_\-. ]?\d+k$", "", stem, flags=re.IGNORECASE)
    parts = [p for p in re.split(r"[_\-. ]", s) if p]
    for n in (2, 1):
        if len(parts) > n:
            kind = "_".join(parts[-n:]).lower()
            if kind in ALIASES:
                return "_".join(parts[:-n]), ALIASES[kind]
    return None, None


def cmd_scan(args):
    sets = defaultdict(dict)
    unknown = []
    for p in sorted(Path(args.folder).rglob("*")):
        if p.suffix.lower() not in IMAGE_EXT:
            continue
        base, kind = classify(p.stem)
        if base:
            sets[(p.parent, base)][kind] = p
        else:
            unknown.append(p)
    if not sets:
        print("No texture sets found.")
    for (folder, base), maps in sorted(sets.items()):
        sizes = set()
        for p in maps.values():
            try:
                with Image.open(p) as im:
                    sizes.add(im.size)
            except Exception:
                pass
        has = ", ".join(sorted(maps))
        missing = [k for k in ("albedo", "normal", "roughness", "ao") if k not in maps
                   and not (k == "roughness" and "gloss" in maps)]
        size_note = ", ".join(f"{w}x{h}" for w, h in sorted(sizes))
        npot = any(w & (w - 1) or h & (h - 1) for w, h in sizes)
        print(f"{folder.name}/{base}: {has}  [{size_note}{'  NOT power of two' if npot else ''}]"
              + (f"  missing: {', '.join(missing)}" if missing else ""))
    if unknown:
        print(f"\n{len(unknown)} image(s) not recognized as part of a set, e.g.: "
              + ", ".join(p.name for p in unknown[:8]))


def split_spec(spec):
    """'~C:/x/rock.png:g' -> (invert=True, path='C:/x/rock.png', channel='g', constant=None)."""
    invert = spec.startswith("~")
    spec = spec[1:] if invert else spec
    if re.fullmatch(r"\d{1,3}", spec):
        return invert, None, "", int(spec)
    if re.search(r":[rgba]$", spec, flags=re.IGNORECASE):
        return invert, spec[:-2], spec[-1].lower(), None
    return invert, spec, "", None


def load_channel(spec, size):
    """Return an 'L' image for a channel spec: path[:channel], constant 0-255, optional leading ~ to invert."""
    invert, path, chan, constant = split_spec(spec)
    if constant is not None:
        img = Image.new("L", size, constant)
    else:
        with Image.open(path) as src:
            src = src.convert("RGBA") if chan else src
            if chan:
                img = src.getchannel("RGBA".index(chan.upper()))
            else:
                img = src.convert("L")
            if img.size != size:
                img = img.resize(size, Image.LANCZOS)
            img = img.copy()
    return ImageChops.invert(img) if invert else img


def _check_out(path, force):
    out = Path(path)
    if out.exists() and not force:
        sys.exit(f"{out} already exists. Use --force to overwrite.")
    out.parent.mkdir(parents=True, exist_ok=True)
    return out


def cmd_pack(args):
    specs = [args.r, args.g, args.b] + ([args.a] if args.a else [])
    if args.size:
        size = (args.size, args.size)
    else:
        first_file = next((split_spec(s)[1] for s in specs if split_spec(s)[1]), None)
        if not first_file:
            sys.exit("All channels are constants: give --size.")
        with Image.open(first_file) as im:
            size = im.size
    channels = [load_channel(s, size) for s in specs]
    out = _check_out(args.output, args.force)
    Image.merge("RGBA" if len(channels) == 4 else "RGB", channels).save(out)
    print(f"Wrote {out} ({size[0]}x{size[1]}, {'RGBA' if len(channels) == 4 else 'RGB'})")


def cmd_flip_green(args):
    with Image.open(args.normal) as src:
        mode = "RGBA" if "A" in src.getbands() else "RGB"
        bands = list(src.convert(mode).split())
    bands[1] = ImageChops.invert(bands[1])
    out = _check_out(args.output, args.force)
    Image.merge(mode, bands).save(out)
    print(f"Wrote {out} (green channel inverted)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan")
    s.add_argument("folder")
    p = sub.add_parser("pack")
    p.add_argument("-o", "--output", required=True)
    for c in "rgb":
        p.add_argument(f"--{c}", required=True)
    p.add_argument("--a")
    p.add_argument("--size", type=int, help="output size (square); default: size of the first image")
    p.add_argument("--force", action="store_true")
    f = sub.add_parser("flip-green")
    f.add_argument("normal")
    f.add_argument("-o", "--output", required=True)
    f.add_argument("--force", action="store_true")
    args = ap.parse_args()
    {"scan": cmd_scan, "pack": cmd_pack, "flip-green": cmd_flip_green}[args.cmd](args)


if __name__ == "__main__":
    main()

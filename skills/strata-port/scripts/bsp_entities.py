#!/usr/bin/env python3
"""Extract the entities (names, keyvalues, I/O connections) from a compiled Source / Strata map.

Usage:
    python bsp_entities.py <map.bsp> [-o entities.json] [--raw entities.txt]

Read-only: the BSP is never modified. Uses only the Python standard library.
"""
import argparse
import json
import lzma
import re
import struct
import sys
from collections import Counter
from pathlib import Path

LUMP_COUNT = 64
SPECIAL_SEPARATOR = "\x1b"  # Portal 2 / newer branches separate output fields with ESC instead of commas


def _decompress_valve_lzma(data: bytes) -> bytes:
    """Valve LZMA lump: 'LZMA', uint32 actualSize, uint32 lzmaSize, 5 property bytes, payload."""
    if data[:4] != b"LZMA":
        return data
    actual_size, lzma_size = struct.unpack_from("<II", data, 4)
    props = data[12:17]
    d = props[0]
    lc, d = d % 9, d // 9
    lp, pb = d % 5, d // 5
    dict_size = struct.unpack_from("<I", props, 1)[0]
    decoder = lzma.LZMADecompressor(
        format=lzma.FORMAT_RAW,
        filters=[{"id": lzma.FILTER_LZMA1, "lc": lc, "lp": lp, "pb": pb, "dict_size": dict_size}],
    )
    return decoder.decompress(data[17:17 + lzma_size], actual_size)[:actual_size]


def _looks_like_entities(data: bytes) -> bool:
    return data.lstrip()[:1] == b"{" and b'"classname"' in data[:4096]


def read_entity_text(path: Path):
    """Return (entity lump text, bsp version, how it was found)."""
    size = path.stat().st_size
    with path.open("rb") as fh:
        head = fh.read(8 + LUMP_COUNT * 16)
        ident = head[:4]
        version = struct.unpack_from("<i", head, 4)[0] if len(head) >= 8 else None

        if ident == b"VBSP" and len(head) == 8 + LUMP_COUNT * 16:
            # Lump 0 is the entity lump. Most branches store (offset, length, version, fourCC);
            # Left 4 Dead 2 style stores (version, offset, length, fourCC). Try both and validate.
            fields = struct.unpack_from("<iiii", head, 8)
            for label, (ofs, length) in (("standard", (fields[0], fields[1])), ("l4d2", (fields[1], fields[2]))):
                if 0 < ofs < size and 0 < length <= size - ofs:
                    fh.seek(ofs)
                    data = _decompress_valve_lzma(fh.read(length))
                    if _looks_like_entities(data):
                        return data.split(b"\0", 1)[0].decode("latin-1"), version, f"lump header ({label})"

    # Fallback for unknown or changed BSP layouts: search for the worldspawn entity text.
    raw = path.read_bytes()
    hit = raw.find(b'"worldspawn"')
    if hit != -1:
        start = raw.rfind(b"{", 0, hit)
        end = raw.find(b"\0", hit)
        if start != -1:
            data = raw[start:end if end != -1 else len(raw)]
            if _looks_like_entities(data):
                return data.decode("latin-1"), version, "text search (unknown BSP layout)"

    raise ValueError(
        f"No entity lump found in {path} (ident {ident!r}, version {version}). "
        "The file may use a compressed or unknown BSP layout."
    )


_TOKEN = re.compile(r'"([^"]*)"|([{}])')


def parse_connection(value: str):
    """Return a dict if the value looks like an I/O connection, else None."""
    if SPECIAL_SEPARATOR in value:
        parts = value.split(SPECIAL_SEPARATOR)
    else:
        parts = value.split(",")
    if len(parts) != 5:
        return None
    target, inp, param, delay, times = parts
    try:
        delay_f = float(delay)
        times_i = int(float(times))
    except ValueError:
        return None
    return {"target": target, "input": inp, "param": param, "delay": delay_f, "times": times_i}


def parse_entities(text: str):
    entities, current, pending_key = [], None, None
    for quoted, brace in _TOKEN.findall(text):
        if brace == "{":
            current, pending_key = [], None
        elif brace == "}":
            if current is not None:
                entities.append(current)
            current = None
        elif current is not None:
            if pending_key is None:
                pending_key = quoted
            else:
                current.append((pending_key, quoted))
                pending_key = None

    result = []
    for pairs in entities:
        ent = {"classname": "", "targetname": "", "keyvalues": {}, "outputs": []}
        for key, value in pairs:
            conn = parse_connection(value)
            if conn is not None:
                ent["outputs"].append({"output": key, **conn})
                continue
            if key == "classname":
                ent["classname"] = value
            elif key == "targetname":
                ent["targetname"] = value
            # keep duplicate keys as lists
            existing = ent["keyvalues"].get(key)
            if existing is None:
                ent["keyvalues"][key] = value
            elif isinstance(existing, list):
                existing.append(value)
            else:
                ent["keyvalues"][key] = [existing, value]
        result.append(ent)
    return result


def load_entities(path):
    """Load entities from a .bsp or from a .json file written by this script."""
    path = Path(path)
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    text, version, method = read_entity_text(path)
    return {"file": str(path), "bsp_version": version, "found_by": method, "entities": parse_entities(text)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bsp", help="compiled map (.bsp)")
    ap.add_argument("-o", "--output", help="write entities as JSON to this file")
    ap.add_argument("--raw", help="write the raw entity text to this file")
    args = ap.parse_args()

    path = Path(args.bsp)
    text, version, method = read_entity_text(path)
    data = {"file": str(path), "bsp_version": version, "found_by": method, "entities": parse_entities(text)}

    if args.raw:
        Path(args.raw).write_text(text, encoding="utf-8")
    if args.output:
        Path(args.output).write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")

    ents = data["entities"]
    classes = Counter(e["classname"] for e in ents)
    n_out = sum(len(e["outputs"]) for e in ents)
    print(f"{path.name}: BSP version {version}, entities found via {method}")
    print(f"{len(ents)} entities, {len(classes)} classes, {n_out} I/O connections")
    for cls, n in classes.most_common(12):
        print(f"  {n:5d}  {cls}")
    if args.output:
        print(f"JSON written to {args.output}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as exc:
        sys.exit(f"Error: {exc}")

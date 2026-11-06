#!/usr/bin/env python3
"""Compare entity definitions (FGD files) between two engine versions, optionally only for what the mod uses.

Without --usage: lists every entity class, keyvalue, input and output that was removed,
added or changed type between OLD and NEW.
With --usage (from vmf_inventory.py --json): reports only what the mod's maps actually use,
which is the list that matters for a port. --old is optional then: with only --new it checks
the maps against the new FGD and lists everything the new FGD doesn't know.

Usage:
    python fgd_diff.py --old portal2.fgd --new p2ce.fgd [--usage usage.json] [-o report.md]
    python fgd_diff.py --new p2ce.fgd --usage usage.json [-o report.md]

@include lines are followed automatically. Read-only, standard library only.
If an FGD uses syntax this parser doesn't understand, the report says so: read the file directly then.
"""
import argparse
import json
import re
import sys
from pathlib import Path

_TOKEN = re.compile(r'//[^\n]*|"((?:[^"\\]|\\.)*)"|(@\w+)|([\[\](),:=+])|([^\s\[\](),:=+"]+)')


def tokenize(text):
    toks = []
    for m in _TOKEN.finditer(text):
        s, directive, punct, word = m.groups()
        if m.group(0).startswith("//"):
            continue
        if s is not None:
            toks.append(("str", s))
        elif directive:
            toks.append(("dir", directive))
        elif punct:
            toks.append(("p", punct))
        else:
            toks.append(("w", word))
    return toks


class FGD:
    def __init__(self):
        self.classes = {}   # name -> {"kind", "bases", "kv": {name: type}, "in": {name: type}, "out": {...}}
        self.warnings = []
        self.files = []

    def load(self, path, seen=None):
        path = Path(path).resolve()
        seen = seen if seen is not None else set()
        if path in seen:
            return
        seen.add(path)
        self.files.append(path)
        toks = tokenize(path.read_text(encoding="utf-8", errors="replace"))
        i = 0
        while i < len(toks):
            kind, val = toks[i]
            if kind != "dir":
                i += 1
                continue
            d = val.lower()
            if d == "@include" and i + 1 < len(toks) and toks[i + 1][0] == "str":
                inc = path.parent / toks[i + 1][1]
                if inc.is_file():
                    self.load(inc, seen)
                else:
                    self.warnings.append(f"{path.name}: included file not found: {toks[i + 1][1]}")
                i += 2
            elif d.endswith("class"):
                i = self._parse_class(toks, i, d, path)
            else:
                i = self._skip_directive(toks, i + 1)

    @staticmethod
    def _skip_directive(toks, i):
        """Skip e.g. @mapsize(...) or @MaterialExclusion [ ... ]."""
        depth = 0
        while i < len(toks):
            k, v = toks[i]
            if k == "dir" and depth == 0:
                return i
            if v in "([" and k == "p":
                depth += 1
            elif v in ")]" and k == "p":
                depth -= 1
                if depth == 0:
                    return i + 1
            i += 1
        return i

    def _parse_class(self, toks, i, kind, path):
        i += 1
        bases = []
        # header: helpers like base(A, B) size(...) color(...) until '='
        while i < len(toks) and toks[i] != ("p", "="):
            k, v = toks[i]
            if k == "dir":
                self.warnings.append(f"{path.name}: class header without '=' near token {i}")
                return i
            if k == "w" and v.lower() == "base" and i + 1 < len(toks) and toks[i + 1] == ("p", "("):
                i += 2
                while i < len(toks) and toks[i] != ("p", ")"):
                    if toks[i][0] == "w":
                        bases.append(toks[i][1].lower())
                    i += 1
            elif k == "p" and v == "(":
                depth = 1
                i += 1
                while i < len(toks) and depth:
                    if toks[i] == ("p", "("):
                        depth += 1
                    elif toks[i] == ("p", ")"):
                        depth -= 1
                    i += 1
                continue
            i += 1
        i += 1  # '='
        if i >= len(toks) or toks[i][0] != "w":
            self.warnings.append(f"{path.name}: class without a name near token {i}")
            return i
        name = toks[i][1].lower()
        i += 1
        while i < len(toks) and toks[i] != ("p", "["):   # description: ":" "text" + "more"
            if toks[i][0] == "dir":
                self.warnings.append(f"{path.name}: class {name} has no body")
                return i
            i += 1
        cls = {"kind": kind, "bases": bases, "kv": {}, "in": {}, "out": {}, "file": path.name}
        i = self._parse_body(toks, i + 1, cls)
        self.classes[name] = cls
        return i

    def _parse_body(self, toks, i, cls):
        while i < len(toks):
            k, v = toks[i]
            if (k, v) == ("p", "]"):
                return i + 1
            if k == "w" and v.lower() in ("input", "output") and i + 2 < len(toks) \
                    and toks[i + 1][0] == "w" and toks[i + 2] == ("p", "("):
                io_type = toks[i + 3][1].lower() if i + 3 < len(toks) else "?"
                cls["in" if v.lower() == "input" else "out"][toks[i + 1][1]] = io_type
                i += 4
            elif k == "w" and i + 1 < len(toks) and toks[i + 1] == ("p", "("):
                kv_type = toks[i + 2][1].lower() if i + 2 < len(toks) else "?"
                cls["kv"][v.lower()] = kv_type
                i += 3
            elif (k, v) == ("p", "["):   # choices / flags block
                depth = 1
                i += 1
                while i < len(toks) and depth:
                    if toks[i] == ("p", "["):
                        depth += 1
                    elif toks[i] == ("p", "]"):
                        depth -= 1
                    i += 1
                continue
            elif k == "dir":
                return i
            i += 1
        return i

    def resolved(self, name, _stack=None):
        """Class with all base classes merged in."""
        _stack = _stack or set()
        cls = self.classes.get(name)
        if cls is None or name in _stack:
            return None
        _stack = _stack | {name}
        merged = {"kv": {}, "in": {}, "out": {}, "kind": cls["kind"]}
        for base in cls["bases"]:
            b = self.resolved(base, _stack)
            if b is None:
                if base not in self.classes:
                    self.warnings.append(f"class {name}: unknown base class {base}")
                continue
            for part in ("kv", "in", "out"):
                merged[part].update(b[part])
        for part in ("kv", "in", "out"):
            merged[part].update(cls[part])
        return merged

    def placeable(self):
        return {n for n, c in self.classes.items() if c["kind"] != "@baseclass"}


def load_fgds(paths):
    fgd = FGD()
    for p in paths:
        fgd.load(p)
    return fgd


LABELS = {"kv": "keyvalues", "in": "inputs", "out": "outputs"}


def compare_full(old, new, limit):
    out = []
    w = out.append
    o_cls, n_cls = old.placeable(), new.placeable()
    removed, added = sorted(o_cls - n_cls), sorted(n_cls - o_cls)
    w(f"## Classes removed ({len(removed)})\n")
    w(", ".join(f"`{c}`" for c in removed[:limit]) or "None.")
    w(f"\n## Classes added ({len(added)})\n")
    w(", ".join(f"`{c}`" for c in added[:limit]) or "None.")
    w("\n## Changes in classes that exist in both\n")
    any_change = False
    for name in sorted(o_cls & n_cls):
        a, b = old.resolved(name), new.resolved(name)
        if not a or not b:
            continue
        lines = []
        for part in ("kv", "in", "out"):
            gone = sorted(set(a[part]) - set(b[part]))
            new_ = sorted(set(b[part]) - set(a[part]))
            retyped = sorted(x for x in set(a[part]) & set(b[part]) if a[part][x] != b[part][x])
            if gone:
                lines.append(f"  - {LABELS[part]} removed: " + ", ".join(gone))
            if new_:
                lines.append(f"  - {LABELS[part]} added: " + ", ".join(new_))
            if retyped:
                lines.append(f"  - {LABELS[part]} changed type: " +
                             ", ".join(f"{x} ({a[part][x]} → {b[part][x]})" for x in retyped))
        if lines:
            any_change = True
            w(f"- `{name}`")
            out.extend(lines)
    if not any_change:
        w("None.")
    return out


COMPILER_CLASSES = {"func_instance", "func_instance_parms", "func_instance_io_proxy"}
GENERIC_KEYS = {"origin", "angles", "targetname", "spawnflags", "parentname", "mapversion", "hammerid", "id"}
LEGACY_KEYS = {"mindxlevel", "maxdxlevel", "mincpulevel", "maxcpulevel", "mingpulevel", "maxgpulevel", "disablex360"}


def compare_usage(old, new, usage):
    out = []
    w = out.append
    w("## What your maps use that is gone or unknown in the new FGD\n")
    found = False
    legacy_seen = set()
    for cls in sorted(usage, key=lambda c: -usage[c]["count"]):
        u = usage[cls]
        if cls in COMPILER_CLASSES:
            continue  # handled by the map compiler, not described like normal entities
        b = new.resolved(cls)
        a = old.resolved(cls) if old else None
        where = f"{u['count']}× in {', '.join(u['maps'][:5])}{' …' if len(u['maps']) > 5 else ''}"
        if b is None:
            found = True
            state = "removed (was in the old FGD)" if a else "not defined in the new FGD"
            w(f"- **`{cls}`**: class {state}. Used {where}")
            continue
        lines = []
        for part, used in (("kv", u["keyvalues"]), ("out", u["outputs"]), ("in", u["inputs"])):
            known = {k.lower() for k in b[part]}
            missing = sorted(x for x in used if x.strip() and x.lower() not in known
                             and not x.lower().startswith(("instance:", "$")))
            if part == "kv":
                legacy_seen.update(x.lower() for x in missing if x.lower() in LEGACY_KEYS)
                missing = [x for x in missing if x.lower() not in GENERIC_KEYS | LEGACY_KEYS
                           and not x.startswith("_") and not x.lower().startswith("replace")]
            if missing:
                tag = []
                for x in missing:
                    was = a and x.lower() in {k.lower() for k in a[part]}
                    tag.append(f"{x}{' (removed)' if was else ''}")
                lines.append(f"  - {LABELS[part]} not in new FGD: " + ", ".join(tag))
        if lines:
            found = True
            w(f"- `{cls}` (used {where})")
            out.extend(lines)
    if not found:
        w("Nothing. Every class, keyvalue and I/O your maps use exists in the new FGD.")
    if legacy_seen:
        w(f"\nNot listed above: old hardware-level keys ({', '.join(sorted(legacy_seen))}). "
          "They only filtered entities by graphics level on old hardware.")
    w("\nNote: an FGD only describes what Hammer shows. Something missing here may still work in the engine, "
      "and something present can still behave differently. Use this list to decide what to test first.")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--old", nargs="+", help="FGD file(s) of the old engine (e.g. Portal 2)")
    ap.add_argument("--new", nargs="+", required=True, help="FGD file(s) of the new engine (e.g. Strata)")
    ap.add_argument("--usage", help="usage JSON from vmf_inventory.py --json")
    ap.add_argument("-o", "--output", help="Markdown report file (default: print)")
    ap.add_argument("--max", type=int, default=400, help="max classes listed per section in the full comparison")
    args = ap.parse_args()
    if not args.old and not args.usage:
        ap.error("give --old, --usage or both")

    old = load_fgds(args.old) if args.old else None
    new = load_fgds(args.new)

    out = ["# FGD comparison\n"]
    if old:
        out.append(f"- **Old:** {', '.join(p.name for p in old.files)} ({len(old.placeable())} entity classes)")
    out.append(f"- **New:** {', '.join(p.name for p in new.files)} ({len(new.placeable())} entity classes)\n")
    if args.usage:
        usage = json.loads(Path(args.usage).read_text(encoding="utf-8"))
        out += compare_usage(old, new, usage)
        out.append("")
    if old and not args.usage:
        out += compare_full(old, new, args.max)
    warnings = (old.warnings if old else []) + new.warnings
    if warnings:
        out.append("\n## Parser warnings\n")
        out += [f"- {x}" for x in sorted(set(warnings))[:50]]

    report = "\n".join(out)
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"Report written to {args.output}")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(report)


if __name__ == "__main__":
    try:
        main()
    except OSError as exc:
        sys.exit(f"Error: {exc}")

#!/usr/bin/env python3
"""Compare the entities of two compiled versions of the same map and write a Markdown report.

Typical use in a port: OLD = the map compiled with the Portal 2 tools (works),
NEW = the same map compiled with the Strata tools (broken). The report shows renamed,
missing and added entities, changed keyvalues, changed I/O connections and, most
importantly, I/O connections whose target no longer exists.

Usage:
    python entity_diff.py <old.bsp|old.json> <new.bsp|new.json> [-o report.md] [--max 200]

Read-only. Uses only the Python standard library. Needs bsp_entities.py next to it.
"""
import argparse
import fnmatch
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bsp_entities import load_entities  # noqa: E402

IGNORED_KEYS = {"hammerid"}
SPECIAL_TARGET_PREFIX = "!"  # !player, !self, !activator, !caller, ...


def _norm(value):
    """Normalize numbers so '0 0 0' equals '0.0 0 0'."""
    if isinstance(value, list):
        return tuple(_norm(v) for v in value)
    parts = value.split()
    try:
        return tuple(round(float(p), 3) for p in parts) if parts else value
    except ValueError:
        return value.strip()


def _label(ent):
    name = ent["targetname"] or "(unnamed)"
    return f"`{name}` ({ent['classname']}, origin {ent['keyvalues'].get('origin', '?')})"


def _conn_key(c):
    return (c["output"], c["target"].lower(), c["input"].lower(), c["param"], round(c["delay"], 3), c["times"])


def _conn_str(c):
    extra = f" ({c['param']})" if c["param"] else ""
    delay = f" after {c['delay']:g}s" if c["delay"] else ""
    return f"{c['output']} → `{c['target']}`.{c['input']}{extra}{delay}"


def match_entities(old, new):
    """Pair entities: first by (classname, targetname), then leftovers by (classname, origin)."""
    def bucket(ents, keyfn):
        b = defaultdict(list)
        for i, e in enumerate(ents):
            b[keyfn(e)].append(i)
        return b

    pairs, old_left, new_left = [], set(range(len(old))), set(range(len(new)))

    def named(e):
        return (e["classname"], e["targetname"].lower()) if e["targetname"] else None

    def placed(e):
        return (e["classname"], _norm(e["keyvalues"].get("origin", "")))

    for keyfn, kind in ((named, "same name"), (placed, "same class and position")):
        ob = bucket([old[i] for i in sorted(old_left)], keyfn)
        nb = bucket([new[i] for i in sorted(new_left)], keyfn)
        old_idx, new_idx = sorted(old_left), sorted(new_left)
        for key, olist in ob.items():
            if key is None or key not in nb:
                continue
            for oi, ni in zip(olist, nb[key]):
                o, n = old_idx[oi], new_idx[ni]
                pairs.append((o, n, kind))
                old_left.discard(o)
                new_left.discard(n)
    return pairs, sorted(old_left), sorted(new_left)


def broken_links(ents):
    """I/O connections whose target matches no entity name or classname in the map."""
    names = {e["targetname"].lower() for e in ents if e["targetname"]}
    classes = {e["classname"].lower() for e in ents}
    broken = []
    for e in ents:
        for c in e["outputs"]:
            t = c["target"].lower()
            if not t or t.startswith(SPECIAL_TARGET_PREFIX):
                continue
            if "*" in t:
                if any(fnmatch.fnmatchcase(n, t) for n in names) or any(fnmatch.fnmatchcase(n, t) for n in classes):
                    continue
            elif t in names or t in classes:
                continue
            broken.append((e, c))
    return broken


def diff(old_data, new_data, limit):
    old, new = old_data["entities"], new_data["entities"]
    out = []
    w = out.append

    w(f"# Entity comparison\n")
    w(f"- **Old:** `{old_data.get('file', '?')}`: {len(old)} entities")
    w(f"- **New:** `{new_data.get('file', '?')}`: {len(new)} entities\n")

    # 1. Broken links, the most likely cause of "works sometimes / not at all"
    old_broken = {(e["targetname"], _conn_key(c)) for e, c in broken_links(old)}
    new_broken = broken_links(new)
    fresh = [(e, c) for e, c in new_broken if (e["targetname"], _conn_key(c)) not in old_broken]
    w("## 1. I/O connections that point at nothing (new in the new map)\n")
    if fresh:
        w("These connections fire into the void in the new map but not in the old one. Check these first.\n")
        for e, c in fresh[:limit]:
            w(f"- {_label(e)}: {_conn_str(c)}")
        if len(fresh) > limit:
            w(f"- … and {len(fresh) - limit} more")
    else:
        w("None.")
    if old_broken:
        w(f"\n({len(old_broken)} connections were already pointing at nothing in the old map; they're not listed.)")
    w("")

    pairs, old_only, new_only = match_entities(old, new)

    # 2. Renamed entities
    renamed = [(o, n) for o, n, kind in pairs if kind != "same name" and old[o]["targetname"] != new[n]["targetname"]]
    w("## 2. Renamed entities (same class and position, different name)\n")
    if renamed:
        w("Often caused by a different instance name fixup (prefix/postfix) in the new compiler.\n")
        for o, n in renamed[:limit]:
            w(f"- `{old[o]['targetname'] or '(unnamed)'}` → `{new[n]['targetname'] or '(unnamed)'}` ({old[o]['classname']})")
        if len(renamed) > limit:
            w(f"- … and {len(renamed) - limit} more")
    else:
        w("None.")
    w("")

    # 3. Missing / added
    for title, idxs, ents in (("## 3. Only in the old map (missing in the new one)", old_only, old),
                              ("## 4. Only in the new map", new_only, new)):
        w(title + "\n")
        if idxs:
            by_class = Counter(ents[i]["classname"] for i in idxs)
            w("By class: " + ", ".join(f"{c} ×{n}" for c, n in by_class.most_common()) + "\n")
            for i in idxs[:limit]:
                w(f"- {_label(ents[i])}")
            if len(idxs) > limit:
                w(f"- … and {len(idxs) - limit} more")
        else:
            w("None.")
        w("")

    # 5. Changed keyvalues and connections on matched entities
    kv_changes, io_changes = [], []
    for o, n, _ in pairs:
        eo, en = old[o], new[n]
        keys = (set(eo["keyvalues"]) | set(en["keyvalues"])) - IGNORED_KEYS
        changes = []
        for k in sorted(keys):
            a, b = eo["keyvalues"].get(k), en["keyvalues"].get(k)
            if a is None or b is None or _norm(a) != _norm(b):
                changes.append(f"`{k}`: {a!r} → {b!r}")
        if changes:
            kv_changes.append((en, changes))
        co = {_conn_key(c): c for c in eo["outputs"]}
        cn = {_conn_key(c): c for c in en["outputs"]}
        lost = [co[k] for k in co if k not in cn]
        gained = [cn[k] for k in cn if k not in co]
        if lost or gained:
            io_changes.append((en, lost, gained))

    w("## 5. Changed I/O connections\n")
    if io_changes:
        for e, lost, gained in io_changes[:limit]:
            w(f"- {_label(e)}")
            for c in lost:
                w(f"  - removed: {_conn_str(c)}")
            for c in gained:
                w(f"  - added: {_conn_str(c)}")
        if len(io_changes) > limit:
            w(f"- … and {len(io_changes) - limit} more entities")
    else:
        w("None.")
    w("")

    w("## 6. Changed keyvalues\n")
    if kv_changes:
        for e, changes in kv_changes[:limit]:
            w(f"- {_label(e)}: " + "; ".join(changes))
        if len(kv_changes) > limit:
            w(f"- … and {len(kv_changes) - limit} more entities")
    else:
        w("None.")
    w("")

    # 7. Class count overview
    co, cn = Counter(e["classname"] for e in old), Counter(e["classname"] for e in new)
    changed = sorted(c for c in set(co) | set(cn) if co[c] != cn[c])
    w("## 7. Entity counts per class that changed\n")
    if changed:
        w("| Class | Old | New |\n|---|---:|---:|")
        for c in changed:
            w(f"| {c} | {co[c]} | {cn[c]} |")
    else:
        w("No differences.")
    w("")
    return "\n".join(out), len(fresh)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("old", help="working version (.bsp or .json from bsp_entities.py)")
    ap.add_argument("new", help="new version (.bsp or .json)")
    ap.add_argument("-o", "--output", help="write the Markdown report to this file (default: print)")
    ap.add_argument("--max", type=int, default=200, help="max items per section (default 200)")
    args = ap.parse_args()

    report, n_fresh = diff(load_entities(args.old), load_entities(args.new), args.max)
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"Report written to {args.output} ({n_fresh} new connections pointing at nothing)")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(report)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as exc:
        sys.exit(f"Error: {exc}")

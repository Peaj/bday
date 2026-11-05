#!/usr/bin/env python3
"""Take stock of a mod's map sources: entities, instances, instance parameters and I/O.

Scans every .vmf under the given folders (maps and instances) and writes a Markdown report:
which maps use which instances, missing instance files, instance parameters that are used
but never declared (or the reverse), instance I/O (func_instance_io_proxy, "instance:" inputs)
and how often each entity class is used. With --json it also writes the usage data that
fgd_diff.py can check against an FGD.

Usage:
    python vmf_inventory.py <folder> [more folders] [-o report.md] [--json usage.json]
                            [--instance-root <folder>]

Read-only. Uses only the Python standard library.
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

_TOKEN = re.compile(r'"((?:[^"\\]|\\.)*)"|([{}])|([^\s{}"]+)')
ESC = "\x1b"


def parse_kv(text):
    """Parse Valve KeyValues text into nested [name, [children...]] / (key, value) items."""
    root = []
    stack = [root]
    pending = None
    for quoted, brace, bare in _TOKEN.findall(text):
        if brace == "{":
            block = []
            stack[-1].append((pending or "", block))
            stack.append(block)
            pending = None
        elif brace == "}":
            if len(stack) > 1:
                stack.pop()
            pending = None
        else:
            token = quoted if quoted or bare == "" else bare
            if pending is None:
                pending = token
            else:
                stack[-1].append((pending, token))
                pending = None
    return root


def blocks(items, name):
    return [v for k, v in items if k.lower() == name and isinstance(v, list)]


def kvs(items):
    return [(k, v) for k, v in items if isinstance(v, str)]


def parse_connection(value):
    parts = value.split(ESC) if ESC in value else value.split(",")
    if len(parts) != 5:
        return None
    return {"target": parts[0], "input": parts[1], "param": parts[2]}


def read_vmf(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    tree = parse_kv(text)
    entities = []
    for ent_items in blocks(tree, "entity"):
        kv = {}
        for k, v in kvs(ent_items):
            kv.setdefault(k.lower(), v)
        outputs = []
        for conn_block in blocks(ent_items, "connections"):
            for k, v in kvs(conn_block):
                c = parse_connection(v)
                if c:
                    outputs.append({"output": k, **c})
        entities.append({"kv": kv, "outputs": outputs})
    # worldspawn counts too (it carries map-wide settings)
    for world in blocks(tree, "world"):
        kv = {k.lower(): v for k, v in kvs(world)}
        entities.insert(0, {"kv": kv, "outputs": []})
    return entities


def resolve_instance(file_value, map_path, roots):
    rel = Path(file_value.replace("\\", "/"))
    candidates = [map_path.parent / rel]
    for parent in list(map_path.parents)[:5]:
        candidates.append(parent / rel)
    for root in roots:
        candidates += [root / rel, root / "maps" / rel]
    for c in candidates:
        if c.is_file():
            return c.resolve()
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folders", nargs="+", help="folders with .vmf files (searched recursively)")
    ap.add_argument("-o", "--output", help="Markdown report file (default: print)")
    ap.add_argument("--json", help="also write usage data (classes, keyvalues, I/O) for fgd_diff.py")
    ap.add_argument("--instance-root", action="append", default=[],
                    help="extra folder instance paths are relative to (e.g. sdk_content/maps); repeatable")
    args = ap.parse_args()

    roots = [Path(r) for r in args.instance_root] + [Path(f) for f in args.folders]
    vmfs = sorted({p.resolve() for f in args.folders for p in Path(f).rglob("*.vmf")})
    if not vmfs:
        sys.exit("No .vmf files found.")

    class_count = Counter()
    class_maps = defaultdict(set)
    usage_kv = defaultdict(set)
    usage_out = defaultdict(set)
    usage_in = defaultdict(set)
    instances_used = []                    # (map, targetname, file, resolved, fixup, params)
    missing_instances = []
    instance_users = defaultdict(set)
    params_declared = defaultdict(set)     # instance vmf -> declared $params
    params_used = defaultdict(set)         # instance vmf -> $params referenced in values
    io_proxies = defaultdict(int)
    instance_inputs = []                   # (map, entity, connection) using "instance:" syntax
    failed = []

    for vmf in vmfs:
        try:
            ents = read_vmf(vmf)
        except OSError as exc:
            failed.append((vmf, str(exc)))
            continue
        names_to_class = {e["kv"].get("targetname", "").lower(): e["kv"].get("classname", "") for e in ents}
        for e in ents:
            kv = e["kv"]
            cls = kv.get("classname", "?")
            class_count[cls] += 1
            class_maps[cls].add(vmf.name)
            usage_kv[cls].update(k for k in kv if k not in ("id", "classname"))
            for c in e["outputs"]:
                usage_out[cls].add(c["output"])
                target_cls = names_to_class.get(c["target"].lower())
                if c["input"].lower().startswith("instance:") or c["target"].lower().startswith("instance:"):
                    instance_inputs.append((vmf, kv.get("targetname", "(unnamed)"), c))
                elif target_cls:
                    usage_in[target_cls].add(c["input"])
            if cls not in ("func_instance", "func_instance_parms"):
                values = list(kv.values()) + [c[f] for c in e["outputs"] for f in ("target", "input", "param")]
                for v in values:
                    for p in re.findall(r"\$[A-Za-z_]\w*", v):
                        params_used[vmf].add(p.lower())
            if cls == "func_instance":
                file_value = kv.get("file", "")
                resolved = resolve_instance(file_value, vmf, roots) if file_value else None
                fixup = {"0": "prefix", "1": "postfix", "2": "none"}.get(kv.get("fixup_style", "0"), kv.get("fixup_style"))
                params = sorted(v.split()[0] for k, v in kv.items() if k.startswith("replace") and v.strip())
                instances_used.append((vmf, kv.get("targetname", ""), file_value, resolved, fixup, params))
                if resolved:
                    instance_users[resolved].add(vmf.name)
                elif file_value:
                    missing_instances.append((vmf, file_value))
            elif cls == "func_instance_parms":
                for k, v in kv.items():
                    if k.startswith("parm") and v.strip():
                        params_declared[vmf].add(v.split()[0].lower())
            elif cls == "func_instance_io_proxy":
                io_proxies[vmf] += 1

    out = []
    w = out.append
    w("# Map source inventory\n")
    w(f"{len(vmfs)} VMF files scanned, {len(instances_used)} instance placements, "
      f"{len(instance_users)} different instance files in use, {sum(class_count.values())} entities.\n")

    w("## Missing instance files\n")
    if missing_instances:
        for vmf, f in missing_instances:
            w(f"- `{vmf.name}` uses `{f}`: file not found")
    else:
        w("None. Every func_instance points to an existing file.")
    w("")

    w("## Instance parameters\n")
    problems = False
    for inst in sorted(set(params_declared) | set(params_used)):
        used, declared = params_used[inst], params_declared[inst]
        undeclared, unused = used - declared, declared - used
        if undeclared or unused:
            problems = True
            w(f"- `{inst.name}`: " + "; ".join(filter(None, [
                f"used but not declared in func_instance_parms: {', '.join(sorted(undeclared))}" if undeclared else "",
                f"declared but never used: {', '.join(sorted(unused))}" if unused else ""])))
    if not problems:
        w("No mismatches between declared and used $parameters.")
    w("")

    w("## Instance I/O (a frequent source of port problems)\n")
    if io_proxies or instance_inputs:
        for vmf, n in sorted(io_proxies.items()):
            w(f"- `{vmf.name}`: {n} func_instance_io_proxy")
        for vmf, ent, c in instance_inputs[:200]:
            w(f"- `{vmf.name}` `{ent}`: {c['output']} → `{c['target']}`.{c['input']}")
    else:
        w("No instance I/O found.")
    w("")

    w("## Which maps use which instances\n")
    w("| Instance file | Used in | Placements |\n|---|---|---:|")
    placements = Counter(r for _, _, _, r, _, _ in instances_used if r)
    for inst, users in sorted(instance_users.items(), key=lambda x: -placements[x[0]]):
        w(f"| {inst.name} | {', '.join(sorted(users))} | {placements[inst]} |")
    w("")

    fixups = Counter(f for *_, f, _ in instances_used)
    w("## Instance name fixup styles\n")
    w(", ".join(f"{k}: {v}" for k, v in fixups.most_common()) or "No instances.")
    w("")

    w("## Entity classes\n")
    w("| Class | Count | Maps |\n|---|---:|---:|")
    for cls, n in class_count.most_common():
        w(f"| {cls} | {n} | {len(class_maps[cls])} |")
    w("")

    if failed:
        w("## Files that could not be read\n")
        for vmf, err in failed:
            w(f"- `{vmf}`: {err}")

    report = "\n".join(out)
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"Report written to {args.output}")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(report)

    if args.json:
        usage = {cls: {"count": class_count[cls],
                       "maps": sorted(class_maps[cls]),
                       "keyvalues": sorted(usage_kv[cls]),
                       "outputs": sorted(usage_out[cls]),
                       "inputs": sorted(usage_in[cls])} for cls in class_count}
        Path(args.json).write_text(json.dumps(usage, indent=1), encoding="utf-8")
        print(f"Usage data written to {args.json}")


if __name__ == "__main__":
    main()

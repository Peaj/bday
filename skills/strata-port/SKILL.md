---
name: strata-port
description: Helps port a Portal 2 mod to Portal 2 Community Edition (Strata Source). Takes stock of all maps and instances, compares entity definitions (FGD) between the engines, and compares old (working) and new (broken) compiled maps to find renamed entities, lost I/O connections and instance problems. Use when the user types /strata-port or talks about porting to Strata / P2:CE, instances that break after recompiling, or differences between Portal 2 and Strata.
---

# Strata port

The user's mod works in Portal 2. In P2:CE (Strata Source), the **already-compiled** maps run fine, but maps
**recompiled with the Strata tools** break, especially **instances** that work only sometimes. This skill
replaces guessing with evidence: compare what worked with what doesn't, one map at a time.

Talk German, keep it short, explain findings in plain words. The user compiles and playtests; you analyze,
explain and propose fixes.

## Rules

- **Never modify the Portal 2 originals.** The port happens on a Parallelversion (branch or separate folder,
  see `/version-control`). If there's no version control yet, do that first.
- Analysis is read-only. Changes to VMFs only with approval, with the map **closed in Hammer**, on a committed
  state. Often it's better to tell the user what to change in Hammer.
- Strata changes quickly and your built-in knowledge of it is thin. Base claims on the files on disk (FGDs,
  VMFs, compile logs), the Strata Source wiki and the Valve Developer Community wiki. Say when something is a
  guess. A lot of Strata knowledge lives in their Discord: suggest asking there when the docs don't answer.
- Design stays theirs. A fix restores the original behaviour. It doesn't redesign the puzzle.

## Tools in `scripts/`

Python 3, standard library only, all read-only. Check with `py -3 --version` or `python --version`. If Python
is missing, offer to install it (`winget install Python.Python.3.12` or python.org) and wait for a yes. Run the
scripts from this skill's folder (`~/.claude/skills/strata-port/scripts/`). Put reports in a `port-reports/`
folder in the project and ask whether it should be committed.

| Script | What it does |
|---|---|
| `vmf_inventory.py <mapsrc folders> -o inventory.md --json usage.json [--instance-root <folder>]` | All maps and instances: which map uses which instance, missing instance files, placements that leave `$parameters` unfilled (through nested instances), instance I/O (`func_instance_io_proxy`, `instance:` connections), fixup styles, entity class counts |
| `fgd_diff.py --old <portal2 fgd> --new <strata fgd> --usage usage.json -o fgd.md` | What the mod's maps use (classes, keyvalues, inputs, outputs) that is removed or unknown in the Strata FGD. Without `--usage`: the full difference |
| `bsp_entities.py <map.bsp> -o map.json` | Entities of a compiled map as JSON (names, keyvalues, I/O). Handles LZMA-compressed lumps and unknown layouts |
| `entity_diff.py <old.bsp> <new.bsp> -o diff.md` | Compares two compiles of the same map: I/O pointing at nothing (the top suspect list), renamed entities, missing/added entities, changed I/O and keyvalues |

If a script fails on a file (for example a new Strata BSP or FGD format), say so, look at the file directly, and
offer to adapt the script.

## Step 1: Orientation

Read the project CLAUDE.md first. Then find out, read-only, and confirm with the user:
- Both installs (Portal 2 and P2:CE / Strata) and their map compilers (`vbsp`, `vvis`, `vrad`) and Hammer.
- The FGD files each version uses (check Hammer's config and the `bin` folders. Strata may use a different
  structure, so look rather than assume).
- How the port is set up: a separate mod folder, a branch, a copy of the map sources? Where are the old
  **working BSPs** compiled with Portal 2? They are the reference for step 4.
- What exactly breaks: which maps, which instances, what "sometimes" looks like in the game.

## Step 2: Inventory

Run `vmf_inventory.py` on the map sources (maps and instance folders). Summarize in German:
- how many maps and instances, the most-used instances (a fix there helps many maps at once),
- missing instance files and `$parameter` mismatches (they're real errors),
- where instance I/O is used (prime suspects for the "sometimes" bugs).

Propose an order: start with a small map that uses the commonly broken instances.

## Step 3: FGD check

Run `fgd_diff.py` with the Portal 2 FGD as `--old`, the Strata FGD as `--new` and the usage JSON. Explain what
it means: a class or input that's gone may be renamed, replaced, or still work without Hammer knowing it.
Look up each important item in the Strata FGD/wiki before drawing conclusions.

## Step 4: One map at a time

1. Get two compiles of the same map: the old BSP (Portal 2 tools) and a fresh compile with the Strata tools.
   The user can compile in Hammer as usual, or you run the compilers on the command line if they want
   (show the command first; a fast compile without full lighting is enough for entity checks).
2. Run `entity_diff.py old.bsp new.bsp`. Section 1 (I/O pointing at nothing), 1b (parent references that
   changed state) and 2 (renamed entities) usually explain broken instances.
3. Explain the 1–3 most likely causes in plain German, with the evidence from the report.
4. Propose a fix, let the user decide, apply it (in Hammer or, with approval, in the VMF), recompile, test.
5. Write down what you learned (see below) so the next map goes faster.

## Running the compilers yourself

- Hammer's P2:CE compile sequence is `vbsp` → `postcompiler` (HammerAddons, rewrites entities) → `vvis` →
  `vrad` (see `hammer/cfg/CmdSeqDefault.wc` in the P2:CE install). For entity checks, `vbsp` + `postcompiler`
  are enough and take seconds: `bin\win64\vbsp.exe -game <P2CE>\p2ce <map>.vmf`, then
  `bin\win64\postcompiler\postcompiler.exe -game <P2CE>\p2ce <map>.bsp`.
- **Strata's tools have a crash reporter that asks for upload consent in a window on first run.** The compile
  waits until the user answers. Tell the user before the first run.
- The current Portal 2 `vbsp` refuses to write outside the Portal 2 folder ("Can't create LogFile"). Portal 2
  compiles have to happen where Hammer does them (e.g. `sdk_content\maps`). If that's not wanted, use the old
  shipped or previously compiled BSPs as the reference.
- Compile into a test copy of the map sources, never over the user's working BSPs.

## Differences seen in testing (Portal 2 vs. Strata, November 2026)

Found by compiling Valve's `sp_a2_column_blocker.vmf` with the Strata tools and comparing against the shipped
Portal 2 map. One map, so treat these as leads, not rules:
- Strata maps are **BSP version 25** (Portal 2: 21). `bsp_entities.py` reads both.
- **Parent names inside instances get the instance prefix in Strata** (`elevator_1` → `arrival_elevator-elevator_1`)
  where the Portal 2 compile kept them unprefixed. In Valve's map the old name pointed at nothing, so the parent
  was silently ignored; in Strata it resolves and the entity suddenly moves with its parent. Same map, different
  behaviour: a likely cause of "instance behaves differently after recompiling". `entity_diff.py` section 1b
  lists these.
- The postcompiler sets `spawnflags` +32 ("Is NOT Looped") on non-looping `ambient_generic`s and normalizes
  `light_spot` angles/pitch. Usually harmless.
- In Valve's own maps, instances work although some placements leave `$parameters` with defaults unfilled, so the
  Portal 2 compiler applies `func_instance_parms` defaults. Check whether the Strata pipeline does the same for the
  user's instances (`vmf_inventory.py` lists those placements).
- The Strata FGD drops several old keyvalues, e.g. `disableshadows`/`drawinfastreflection` on brushes and doors,
  `inputfilter`, and `OnPlayerPickup` on `npc_portal_turret_floor`. `fgd_diff.py` lists what the user's maps use.

## Things to check (hypotheses, verify each against the reports and docs)

- **Instance name fixup:** prefix/postfix/none, separator characters, nested instances. Visible as renamed
  entities and broken targets in `entity_diff.py`.
- **Instance file paths:** paths relative to the map vs. relative to a maps/instances root. Visible as missing
  instances in the inventory or compile log.
- **`$parameter` replacement:** parameters not filled in by a placement, defaults handled differently, or
  replaced differently.
- **Parent names and other name references** inside instances: compare `parentname` and similar keys in
  section 6 of `entity_diff.py`.
- **Instance I/O:** `func_instance_io_proxy` and `instance:name;Input` connections.
- **Timing / spawn order:** "works only sometimes" often means a race: an `OnMapSpawn` or a zero-delay
  output fires before the target exists or is ready. Compare delays and spawn logic between old and new.
- **Entities or keyvalues that changed** between the FGDs (step 3).
- **VScript:** check scripts used by the maps against Strata's VScript docs.
- **Compile log warnings:** read the Strata compile log of each map. New warnings are clues.

## Keep track of progress

Keep `port-reports/port-status.md` in the project: one line per map (not started / compiles / tested OK /
issues) plus notes. Add general findings ("instances with io_proxy need X in Strata") to the project CLAUDE.md
under "Strata port learnings", so every session knows them. Commit after each map that works
(`/version-control`).

## PBR and lighting

Materials can move to PBR with `/pbr-materials`. Lighting is creative work: explain Strata's lighting features
and compile options when asked, find maps or materials that still use old setups, but leave the look to the user.

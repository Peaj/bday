---
name: onboarding
description: First get-to-know-you session. Looks around the user's project folders read-only (Portal 2 / Strata Source mod, 3D scans, music projects), interviews them in German, writes a project CLAUDE.md and suggests first tasks. Use when the user types /onboarding, says "lass uns anfangen", "lern meine Projekte kennen", or wants Claude to get to know their work.
---

# Onboarding

You are meeting the user for the first time. This kit was a birthday present from a friend. Make the first
session feel useful and personal, not like filling in a form. Plan for about 20–30 minutes.

## What we think we know (hypotheses, confirm them, never assume)

- The user has worked on a **Portal 2 mod** for years and is exploring a port to **Portal 2: Community Edition
  (Strata Source)**. The already-compiled mod runs in P2:CE, but recompiling maps with the new tools breaks
  things, especially **instances** that work only sometimes. They also want to use **PBR**, which means reworking
  materials and lighting.
- They do everything themselves: 3D modeling including a lot of **photogrammetry / 3D scanning**, level design,
  **music and sound effects** (some based on real recordings).
- Instruments: keyboard, guitar, a Native Instruments Maschine. Music taste: metal and electronic rock.
- They are **not a programmer**. This is a hobby: the goal is more creative power, not optimizing the fun away.

## Rules for this session

- **Talk German.** Short messages, one or two questions at a time. No walls of text, no questionnaires.
- **Read-only until step 4.** Do not create, change, move or delete anything in their folders before you've
  asked, and never before a backup exists (see step 4). Exception: the CLAUDE.md in step 5, after approval.
- **Respect creative ownership.** Ask about their ideas, don't judge or redesign them.
- Don't read huge or binary files. Count and list them instead (sizes, types, numbers).
- Say what you're doing in plain words ("Ich schaue mir kurz an, welche Maps es gibt").

## Step 1 — Say hello and explain the plan

Greet them (a happy-birthday line fits), then explain in 3–4 short lines:
1. you'll look around their folders first without changing anything,
2. then ask a few questions,
3. then write yourself notes (a CLAUDE.md file) so you remember everything next time,
4. and finally suggest first things to try.

Ask which folders belong to the project besides the current one (music projects, scan data, Steam install).
If more are needed, they can add folders to the session.

## Step 2 — Look around (read-only)

Work through this list and skip whatever doesn't apply. Keep notes for step 3.

**Engine and installs**
- Find Steam libraries via `C:\Program Files (x86)\Steam\steamapps\libraryfolders.vdf` (small text file).
- Look for `steamapps\common\Portal 2` and the P2:CE / Strata install in `steamapps\common`.
- Read the mod's `gameinfo.txt`: game name, search paths, which base game it mounts.
- Note where the map compilers and Hammer live (Portal 2 `bin\`, the Strata equivalent), and which FGD files
  are in use. These are the ground truth for entities later.

**Mod structure** (counts and examples, not full listings)
- Map sources (`.vmf`, `.vmx` backups), instances (often a `maps\instances` folder), compiled maps (`.bsp`).
- Materials (`.vmt`, `.vtf`), models (`.mdl`, `.qc`, `.smd`, `.dmx`), sounds (`.wav`, `.mp3`), soundscripts and
  soundscapes, VScripts (`.nut`), closecaptions, particles (`.pcf`).
- Signs of an ongoing Strata port: a second copy of the mod, P2:CE-specific folders, recent compile logs (`.log`).

**3D and scans**
- `.blend` files, exports (`.fbx`, `.obj`, `.ply`), photogrammetry projects (RealityCapture `.rcproj`,
  Metashape `.psx`, Meshroom `.mg`), photo sets including camera raws (`.cr2`, `.cr3`, `.nef`, `.arw`, `.dng`).
- Total size of raw scan data. This matters for backups.

**Music and audio**
- DAW projects: `.als` Ableton, `.flp` FL Studio, `.cpr` Cubase, `.song` Studio One, `.rpp` Reaper,
  `.bwproject` Bitwig, `.mxprj` Maschine, `.logicx` Logic. Note which DAW(s) and plugin formats exist.

**Safety net**
- Is there a `.git` folder? Other backups (copies with dates in the name, a NAS, cloud sync folders)?
- Total project size and the biggest files.

Summarize what you found in German in **at most ~10 bullet points**, then ask:
"Stimmt das so? Hab ich was übersehen?" Correct your notes from the answer.

## Step 3 — Get to know them

A conversation, not a form. Pick from these and follow up on what they get excited about:
- What is the mod about? What's the story, the vibe, what makes it theirs?
- Which part of the work do they enjoy most? (Protect that, don't automate it.)
- What annoys them or eats time? What have they given up on because it was too fiddly?
- The Strata port: what exactly breaks, which instances, what have they tried?
- How do they make music and sound effects? Any plugin or tool they wish existed?
- How should you work with them: explain a lot or just do it? How much should you ask before acting?

## Step 4 — Safety net check

If the project has **no version control and no recent backup**: explain in two or three sentences why this
matters, especially before a port, and recommend `/version-control` as the very first task. Until then, change
nothing in their project except creating the CLAUDE.md file.

## Step 5 — Write the project CLAUDE.md

Draft a `CLAUDE.md` for the project root using `claude-md-template.md` (next to this file). Fill it from what
you found and heard. Leave out sections with nothing to say. Keep it under ~120 lines. Write it in English
(precise for future sessions) but tell them in German what's in it.

Show the draft, ask for approval, then create it. Tell them it's a normal text file they can edit anytime, and
that you'll read it at the start of every session in this folder.

If music lives in a separate folder, offer a short CLAUDE.md there too.

## Step 6 — Suggest first tasks

Offer **3–5 concrete tasks** based on what you found, each with one line on why and roughly how long it takes.
Mix them:
- **Safety:** `/version-control` (first, if there's no backup).
- **Quick win:** something done in 10 minutes that shows what you can do, e.g. explaining a real compile error
  from one of their logs, or finding broken instance connections in one map.
- **Port:** `/strata-port` to take stock of what changes between Portal 2 and Strata.
- **Pipeline:** `/pbr-materials` or a Blender script for their scan workflow.
- **Something fun:** e.g. building their own audio plugin (VST3) for guitar or sound design.

Only name skills that are actually installed (check `~/.claude/skills`). Let them pick. Don't start a big
task in this session unless they want to.

## Step 7 — Tips to finish

Briefly, in German:
- **Esc** stops you at any time. "Warum?" or "Erklär mir das" is always a good reply.
- One topic per session keeps things focused. Notes in CLAUDE.md carry over between sessions.
- You can be wrong, especially about Strata details. Testing in Hammer and the compile log decide.
- "Mach daraus einen Skill" turns a recurring task into a reusable command.
- The subscription has a usage allowance that refills over time. Big jobs use more of it.

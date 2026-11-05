---
name: source-reference
description: Working rules and practical knowledge for Source engine and Strata Source modding (Portal 2, Portal 2 Community Edition), covering Hammer entities and I/O, scale and dimensions, models and QC, materials and textures, sound and soundscripts, and compile errors. Use whenever the user asks about Hammer, entities, keyvalues, instances, VScript, QC/studiomdl, VMT/VTF, soundscripts, compile logs, or how big something should be in Source units.
user-invocable: false
---

# Source / Strata reference

## How to answer Source questions

Source and Strata details are obscure, differ between branches and change between versions. Wrong answers
cost the user hours of compiling and testing, so:

1. **Check the files on disk first.** They're the ground truth for this user's setup:
   - entities, keyvalues, inputs, outputs → the FGD files Hammer uses
   - how something is done in practice → existing VMF/VMT/QC/soundscript files in the game or mod
   - what went wrong → the compile log (`<map>.log` next to the VMF) or the console output
2. **Then the docs:** the Strata Source wiki for P2:CE and the Valve Developer Community wiki
   (developer.valvesoftware.com) for Source in general. Note which branch a VDC page is about.
3. **Say how sure you are.** Mark guesses as guesses. Never invent entity names, keyvalues, I/O, shader
   parameters or command-line options.
4. Strata knowledge often lives in the Strata Discord. If the docs don't answer, suggest asking there.

You can't see Hammer or play the game. When something needs testing, say exactly what to compile or try
and what result would confirm or rule out your theory.

## Scale and dimensions

Hammer measures in **units**. The standard Source player hull is 32×32×72 units standing and 32×32×36
crouching, with eyes at 64. These are the classic values: check the VDC "Dimensions" page and the
game's own settings before relying on them, since branches can differ.

For **real-world scans**, one unit is roughly one inch, so 1 m ≈ 39.37 units. Valve itself doesn't build
everything strictly to that scale: architecture is often exaggerated so spaces feel right in first person.
So:
- Agree on a scale factor with the user and write it into the project CLAUDE.md.
- Test a scanned object in-game next to a known prop or brush of known size before batch-processing more.
- Blender Source Tools exports Blender units 1:1 by default, so set the scale in Blender or the QC (`$scale`).

## Models (QC, studiomdl)

- Source models are compiled from SMD/DMX + a `.qc` file with `studiomdl` (in the game's `bin`). Crowbar is a
  popular GUI for compiling and decompiling.
- Static props need `$staticprop`, plus a simple convex collision model (`$collisionmodel` or `$collisionjoints`).
  Never use the full scan mesh as collision.
- Scans are heavy: decimate, and add `$lod` levels. Vertex and triangle limits per model or mesh exist in
  Source and may be higher in Strata. Read the `studiomdl` error, then check the limit for the branch.
- Material paths: `$cdmaterials` in the QC + material names in the mesh must match the VMT paths.

## Materials and textures (VMT/VTF)

- A material is a text `.vmt` (shader + parameters) pointing to `.vtf` textures. Convert images with VTFCmd
  or VTFEdit (or the tools Strata ships). Texture dimensions should be powers of two.
- Normal maps: Source expects the **DirectX convention** (green channel "Y-"). Many scan and Blender bakes are
  OpenGL ("Y+"), so the green channel needs flipping. Check on a test material: bumps that look like dents
  mean the wrong convention.
- PBR in Strata: see `/pbr-materials`. Shader names and parameters must come from Strata's docs or existing
  Strata VMTs.

## Sound

- Safe format: **WAV, 16-bit PCM, 44.1 kHz.** Positional (3D) sounds should be **mono**. Stereo is for
  non-positional sounds and music.
- **Looping:** a WAV loops in Source when it contains loop/cue points. A DAW export usually doesn't keep them.
  Check with a tool that shows cue chunks, or add them in a wave editor.
- Sounds are played through **soundscripts** (named entries with volume, pitch, level, files) and placed with
  `ambient_generic`. Ambience uses **soundscapes**. Portal 2 also has its own sound mixing system (operator
  stacks / soundmixers). Look at the game's existing scripts before writing new ones.
- Special prefix characters in sound file paths change behaviour (e.g. `*` streaming, `#` no DSP, `)` spatial
  stereo). See the VDC "Soundscripts" page for the full list and the branch differences.
- Batch conversion and checks (sample rate, channels, peak level, cue points) are a good job for ffmpeg or a
  small script. Ask before converting originals: write converted files to a new folder.

## Maps and compiling

- `vbsp` (geometry) → `vvis` (visibility) → `vrad` (lighting). Each writes into the compile log.
- **Leak:** the map isn't sealed from the void. `vbsp` writes a pointfile (`.lin`) that Hammer can load
  (Map → Load Pointfile) to show the leak path.
- "Material not found", "model not found": usually a path or search path (`gameinfo.txt`) problem.
- Limits (`MAX_MAP_*`, brush sides, entity counts) differ per branch. Read the exact error and check the branch.
- Instances (`func_instance`) are merged into the map by `vbsp`. Entity names get a prefix or postfix depending
  on the fixup style, `$parameters` are replaced, and instance I/O goes through `func_instance_io_proxy`.
  For port problems, use `/strata-port`.
- VScript (Squirrel in Portal 2) files live under `scripts/vscripts`. Check functions against the docs for the
  branch the map runs on.

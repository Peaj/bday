---
name: pbr-materials
description: Turns scan and photogrammetry textures (albedo, normal, roughness/gloss, AO, metalness) into PBR materials for Strata Source / Portal 2 Community Edition. Finds texture sets, packs channels, fixes normal map conventions, converts to VTF and writes VMTs, starting with one test material and then in batches. Use when the user types /pbr-materials or wants PBR materials, channel packing, VTF/VMT conversion, or to update old materials for Strata.
---

# PBR materials

Goal: the user's scans and textures become PBR materials in Strata **without hand-editing every file**. How
a material should *look* (roughness, tint, how shiny the metal is) stays the user's decision. You do the
plumbing.

Talk German, explain in plain words.

## Rules

- **Never overwrite** existing textures, VTFs or VMTs. Write new files into a new folder or with a new name,
  and keep the Portal 2 materials intact for the Portal 2 version (see `/version-control`).
- **Strata facts come from Strata.** Shader names, parameter names, the expected channel layout and texture
  formats must come from the Strata Source wiki, Strata's own example materials or the shader files in the
  install, not from memory. Write what you found into the project CLAUDE.md under "PBR setup" so it's
  looked up once.
- **One material first.** Never batch-convert before one test material has been checked in-game by the user.

## Tools

`scripts/pbr_textures.py` (Python 3 + Pillow. If Pillow is missing, offer `py -m pip install pillow`):

| Command | What it does |
|---|---|
| `scan <folder>` | Groups texture files into sets (`rock_albedo`, `rock_normal`, …), shows which maps exist and which are missing, flags sizes that aren't powers of two. Read-only |
| `pack -o <out> --r <src> --g <src> --b <src> [--a <src>]` | Builds a packed texture from single channels. `<src>` = file, `file:g` (one channel of a file), a constant `0`–`255`, `~` in front inverts (gloss → roughness) |
| `flip-green <normal> -o <out>` | Converts a normal map between OpenGL (Y+) and DirectX (Y-) |

For VTF conversion use the tool Strata recommends (check the wiki and the install's `bin` folder), or
VTFCmd / VTFEdit. Format choice matters (compression, sRGB vs. linear for data maps like roughness and normal),
so look up the current advice for Strata.

## Step 1: Find out how Strata wants it

1. Look in the P2:CE install for materials that already use the PBR shader (search `.vmt` files for the
   shader name from the docs). Read two or three of them.
2. Read the Strata wiki page on PBR / the shader.
3. Summarize for the user in a few lines: which textures a PBR material needs, which channel holds what in
   packed textures, the normal map convention, and which parameters matter. Save this in the project CLAUDE.md.

## Step 2: Take stock

Run `scan` on the user's texture/scan folders. Explain the result: complete sets, missing maps (e.g. no
roughness: use a constant or derive it, as the user prefers), sizes that need resizing, gloss maps that need
inverting.

Scanned albedo often contains baked lighting and shadows. Mention it briefly: de-lighting (in the
photogrammetry software, Substance or by hand) is an artistic choice, so ask, don't decide.

## Step 3: One test material

Pick one set together with the user (ideally something visible and simple). Then:
1. Pack and convert the textures (`pack`, `flip-green` if needed, VTF conversion).
2. Write the VMT, following the structure of Strata's own PBR materials.
3. Tell the user where it is and how to test it: put it on a brush or prop in a test map, look at it under a
   few lights, compare with a reference photo.
4. Adjust with them: brighter or darker, rougher or shinier, a normal map that looks inverted. Note the decisions.

## Step 4: Batch

When the test material is approved:
- Agree on naming and output folders, and defaults for missing maps.
- Convert in batches. Show the list first, then report what was created and any sets that were skipped and why.
- Offer a small reusable script or a skill for this pipeline ("Mach daraus einen Skill") so the next scans
  go through the same steps.

## Old materials and lighting

Finding materials still using old (non-PBR) shaders is easy: search the `.vmt` files and list them by map
or folder. Upgrading them can be planned map by map with `/strata-port`. Lighting is the user's creative work:
explain options when asked, don't change light entities or compile settings on your own.

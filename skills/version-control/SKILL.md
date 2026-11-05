---
name: version-control
description: Sets up backups and version control (Git with Git LFS) for a creative project such as a Source / Strata mod, step by step and explained for a non-programmer. Also checks an existing setup and teaches the everyday workflow (save points, history, restoring old versions). Use when the user types /version-control or asks about backups, Git, "Speicherpunkte", restoring an old version, or protecting their project before a big change like the Strata port.
---

# Version control and backups

The user's project holds years of work. **Nothing in this skill may put it at risk.** Go slowly, explain each
step in two or three plain German sentences, and get a yes before each phase. The user doesn't need to learn
Git commands: they'll ask you in plain words later. They do need to understand what's protected and where.

Words to use (German, plain):
- **Commit** = Speicherpunkt (a saved state of the whole project you can always go back to)
- **Push** = Speicherpunkte auf das Backup/den Server kopieren
- **Branch** = Parallelversion (e.g. a Strata version next to the Portal 2 version)
- **LFS** = Git's storage for big files (textures, sounds, models)

## Hard rules

- Never run `git reset --hard`, `git clean`, `git checkout -- .`, `git push --force`, `git rebase`,
  `git filter-repo` or anything else that discards work, unless the user explicitly asked, you explained what
  would be lost, **and** a backup copy exists.
- Never delete, move or rename project files during setup. Moving files breaks paths in Hammer and the mod.
- Never delete the safety copy from phase 1.
- Raw photogrammetry data never goes into Git.
- Never handle passwords or tokens. Logins happen in the browser window Git or GitHub opens.
- Change global Git settings only for the user's name/email and `git lfs install`, and say so first.
- Before restoring an old version of a file, make sure it's closed in Hammer, Blender or the DAW, and that the
  current state is committed, so the restore can be undone.

## Phase 0: Check the starting point

1. Read the project's CLAUDE.md if there is one (from `/onboarding`). It may already list folders, sizes and
   backups.
2. `git --version` and `git lfs version`. If Git is missing, help the user install **Git for Windows**
   (includes Git LFS) from git-scm.com, then continue.
3. Is there already a `.git` folder in the project or a parent folder? If yes, go to **"Existing repository"**
   at the end instead of setting up a new one.
4. Find out where everything lives. Map sources (VMFs, instances), mod content and model sources may sit in
   different places (the Steam game folder, `sdk_content`, separate work folders). Agree with the user on **one
   project root** that contains as much as possible *without moving anything*. If important sources live
   outside it, note them: they can get their own repository or go into the plain backup in phase 4.

## Phase 1: Full safety copy (always first)

1. Measure the project size and check free space on the target drive.
2. Ask where the copy should go, ideally **another drive** (external disk, NAS). Same disk is better than
   nothing, but say why it's weaker.
3. Copy with `robocopy "<source>" "<target>\<Projekt>_Backup_<YYYY-MM-DD>" /E /COPY:DAT /R:1 /W:1`.
   Never use `/MIR` or `/PURGE` (they delete files in the target).
4. Verify: compare file count and total size of source and copy. Tell the user the result.
5. Tell them: keep this copy at least until the new setup has proven itself for a few weeks.

## Phase 2: Decide what goes where

List the file types in the project root with count and total size, then sort them into three groups and
explain the result in a short table:

| Group | What | Where |
|---|---|---|
| Normal Git | Text sources: `.vmf`, `.nut`, `.vmt`, `.qc`, `.txt`, `.cfg`, `.res`, `.fgd`, soundscripts, soundscapes | tracked, readable history |
| Git LFS | Big binaries: textures, sounds, models, `.blend`, compiled maps | tracked, stored efficiently |
| Not in Git | Compile byproducts, autosaves, raw scans, other huge source data | ignored; raw scans get a plain backup in phase 4 |

Start from `gitattributes-template` and `gitignore-template` next to this file and adapt them to what's
actually there. Ask the user about:
- **Compiled maps (`.bsp`):** tracking them in LFS is recommended during the Strata port, because the old,
  working BSPs are the reference `/strata-port` compares against. Later they could be ignored instead.
- **`.vpk` files:** if they're built from loose files that are also in the repo, ignore them. If they're the
  only copy of that content, track them in LFS.
- **Raw scan folders:** add the real folder names and file types to `.gitignore`.
- **Music projects:** better kept as a separate project (own folder, own backup) than inside the mod.

## Phase 3: Create the repository

Explain each step in a sentence, then:
1. Ask for the name and email to use in commits. If they plan to use GitHub and want their email private, they
   can switch to GitHub's noreply address later. Set them with `git config --global` (say so first).
2. `git lfs install` (once per computer; it adds LFS hooks to the global Git config, say so).
3. `git init -b main` in the project root.
4. Write `.gitattributes` and `.gitignore` (show them and get approval first).
5. Dry run: `git add --dry-run .` and report: how many files, total size, size going to LFS vs normal Git.
   Check for any single file **over 50 MB that LFS doesn't cover** and fix the patterns first. GitHub rejects
   normal files over 100 MB.
6. `git add .` then check `git lfs ls-files` to confirm the big files really went to LFS.
7. First commit: `git commit -m "Ausgangsstand: Projekt vor Versionskontrolle"`. This can take a while for big
   projects; run it in the background and say so.
8. Celebrate briefly: the whole project now has a first save point.

## Phase 4: Get a copy off this computer

A repository on the same disk doesn't protect against a dead disk. Explain the options and let the user choose:

**A) External drive or NAS (recommended start: no account, no size limits)**
- Create a bare repository there: `git init --bare "<drive>\Git\<Projekt>.git"`, add it as remote `backup`,
  push with `git push backup main` and `git lfs push --all backup`.
- **Verify** by cloning into a temporary folder and checking that a few big files (a texture, a sound) open
  and aren't tiny LFS pointer files. Then delete only that temporary test clone.

**B) GitHub (private repository)**
- The user creates the account themselves on github.com. Never do it for them.
- Logging in happens through the browser window Git Credential Manager opens on the first push. No tokens to
  copy.
- GitHub's free plan has **limited LFS storage and bandwidth**. Check the current limits on GitHub's docs and
  compare them with the LFS size from phase 3 before choosing this.

**C) Other hosts** (GitLab, Azure DevOps, a Gitea server on a NAS): have different LFS limits. Look up current
numbers if the user is interested.

Both A and B together is ideal: one copy at home, one somewhere else.

**Raw scans and other data outside Git:** offer a small `backup-rohdaten.bat` in the project root that copies
those folders to the backup drive with `robocopy /E` (no `/MIR`, so nothing is ever deleted on the backup). Write
it only with approval, explain how to run it, and suggest a rhythm (e.g. after every scan session).

## Phase 5: Everyday use

Teach this with examples. The user just asks you:
- „Mach einen Speicherpunkt: neue Kammer 3 fertig“ → `git add -A`, commit with their words, push to remotes.
- „Was hab ich seit gestern geändert?“ → summarize `git log` / `git diff --stat` in plain German.
- „Hol mir die Version von map_03 von letzter Woche zurück“ → follow the restore rule above, then
  `git restore --source=<commit> -- <file>`. Offer to save it as a copy next to the current file instead.
- **Strata port:** a Parallelversion (branch) keeps the Portal 2 version safe. If the port lives in a separate
  folder, a second working folder of the same repository (`git worktree`) may fit better. Decide this together
  with `/strata-port`.

Optional: if the user would like to *see* history, suggest **GitHub Desktop** or **Fork** (free Git apps with a
visual timeline). They work with the same repository.

Finally, add a "Version control and backups" section to the project's CLAUDE.md: project root, remotes,
what's ignored, where raw scans are backed up, the backup rhythm. Show it before saving.

## Existing repository

If Git is already set up, don't re-initialize. Check and report in plain German:
- `git status`: uncommitted changes? When was the last commit?
- Remotes: is there one, and is everything pushed (`git status -sb`)?
- LFS: installed and used? Big files committed **without** LFS (`git lfs migrate info --everything`
  is read-only)? Explain the options for fixing it, but **don't rewrite history** without a fresh full copy
  and explicit approval.
- Does `.gitignore` cover compile byproducts and raw scans?
Then offer only the missing pieces from phases 1–5.

# copilot-workflow-base

Reusable **GitHub Copilot / VS Code AI-workflow baseline** — a single set of generic
instructions, skills, prompts, and helper scripts that you drop into any repository as a
git **submodule** so every project shares the same baseline Copilot behavior while keeping
its own domain-specific `.github/` content layered on top.

The two layers **combine**, they do not replace each other: your repo keeps its own
`.github/copilot-instructions.md` and repo-specific `instructions/`, `prompts/`, `skills/`,
and this baseline adds the generic layer through VS Code settings.

There are **two independent ways** to consume it, and you can use **both at the same time**:

- **Per-repo submodule** (committed, pinned) — vendor the baseline into one repo at
  `.github/shared/` so teammates and CI get exactly the same pinned version. Best for shared
  projects. See [Add it to a repository](#add-it-to-a-repository-one-time).
- **Machine-wide** (User settings, live) — point your VS Code **User** settings at a single
  clone so **every** workspace on that machine inherits the baseline, updating the instant you
  `git pull`. Best for your personal editor. See
  [Machine-wide setup](#machine-wide-setup-every-vs-code-window).

They layer cleanly: a repo can carry the pinned submodule *and* your machine can apply the
machine-wide copy. If a file happens to load from both, it simply applies twice (harmless).

## What's inside

```
copilot-workflow-base/
├── instructions/          # *.instructions.md with applyTo globs (always-on baseline)
│   ├── context-engineering.instructions.md   # applyTo: **
│   ├── deck-design.instructions.md           # applyTo: deck specs, themes, builder code
│   ├── engineering-discipline.instructions.md # applyTo: ** (how changes are made)
│   ├── ponytail.instructions.md              # applyTo: ** (vendored, lazy-senior-dev ruleset)
│   ├── python.instructions.md                # applyTo: **/*.py, pyproject.toml, ...
│   ├── readme.instructions.md                # applyTo: **/README.md
│   └── tests.instructions.md                 # applyTo: tests/**
├── prompts/               # shared *.prompt.md (placeholder — add yours here)
├── skills/
│   ├── boost-prompt/SKILL.md
│   ├── deck-builder/SKILL.md                 # topic -> fully-editable .pptx via deckforge
│   ├── knowledge-doc/SKILL.md                # retention-first .md explainer of any topic
│   ├── learning-dashboard/SKILL.md
│   └── markdown-formatting/SKILL.md          # CommonMark rules (auto-invoked on .md edits)
├── scripts/
│   ├── check_markdown.py  # section numbering + TOC + table-alignment checker/fixer
│   ├── deck.py            # cross-platform launcher for the deckforge CLI
│   └── deckforge/         # PowerPoint generation: themes, archetypes, artifacts, verifier
├── extensions/
│   ├── install.ps1 / .sh  # generic installer; discovers every extension folder here
│   └── md-flashcards/     # VS Code extension: `::` spaced-repetition over your notes
├── vendor/
│   └── last30days-skill/  # submodule: multi-source research skill (see below)
├── .github/workflows/
│   └── markdown.yml        # self-lints this repo's own markdown
├── bootstrap.sh            # POSIX onboarding (Linux/macOS/Git-Bash)
├── bootstrap.ps1           # PowerShell onboarding (Windows)
├── LICENSE                 # MIT
└── README.md              # this file
```

Nothing here mentions any single project — it is deliberately domain-neutral so it can be
consumed by many repos at once.

[`ponytail.instructions.md`](instructions/ponytail.instructions.md) is the one vendored
third-party file: a verbatim copy of the ruleset from
[DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) (MIT), which VS Code
Copilot Chat has no plugin for. Re-sync it from upstream rather than editing it in place:

```bash
curl -sSL -o /tmp/ponytail.md \
  https://raw.githubusercontent.com/DietrichGebert/ponytail/main/.github/copilot-instructions.md
```

then diff it against everything below this repo's frontmatter block.

## Deck generation

`scripts/deckforge/` turns a content-only spec into a **fully-editable `.pptx`** — every
element a native PowerPoint shape or table, never a rasterised diagram. It reads its
palette, grid and type scale from a theme token file, harvests templates and reusable
design artifacts out of decks you already have, and verifies the result before you open
it.

```bash
python scripts/deck.py doctor                                       # what this machine can render
python scripts/deck.py harvest "/path/to/branded.pptx" --name acme  # template + design report
python scripts/deck.py build PRESENTATION/specs/feedback-loop.deck.yaml
```

```powershell
python scripts\deck.py doctor
python scripts\deck.py harvest "C:\path\to\branded.pptx" --name acme
python scripts\deck.py build PRESENTATION\specs\feedback-loop.deck.yaml
```

Decks land in `<workspace>/PRESENTATION` unless you pass `--out`. The
[deck-builder skill](skills/deck-builder/SKILL.md) drives the whole flow from a chat
request, and [deck-design.instructions.md](instructions/deck-design.instructions.md)
applies the design rules automatically whenever a spec or builder file is edited. See
[scripts/deckforge/README.md](scripts/deckforge/README.md) for the artifact-reuse model,
the spec format and the full command reference.

## Vendored VS Code extensions

`extensions/` holds optional, dependency-free VS Code extensions. Today that is
`md-flashcards`, which turns any `::` line in your Markdown into an Anki-style flashcard with
scheduling state stored as one sorted JSON file inside the notes repo.

`bootstrap.ps1` / `bootstrap.sh` install everything under `extensions/` as their first step,
so the same onboarding command that wires up instructions, prompts, and skills also installs
these — no extra step. Pass `-NoExtensions` / `--no-extensions` to skip it, or drive the
shared installer yourself:

```powershell
pwsh extensions/install.ps1 [-List] [-Copy] [-Uninstall] [<folder-name>...]
```

```bash
bash extensions/install.sh [--list] [--copy] [--uninstall] [<folder-name>...]
```

Unlike instructions/prompts/skills, VS Code has no setting that points at an arbitrary
extension folder, so the installer links each folder into `~/.vscode/extensions`; the code
still lives here and updates on `git pull`.

Adding your own is a matter of dropping a folder in — the installer discovers any subfolder
whose `package.json` declares `publisher`, `name`, `version`, and `engines.vscode`. See
[extensions/README.md](extensions/README.md) for the layout convention and ground rules, and
[extensions/md-flashcards/README.md](extensions/md-flashcards/README.md) for the flashcard
card syntax, scheduling algorithm, and state schema.

## Vendored research skill: last30days

`vendor/last30days-skill/` is a **git submodule** of
[mvanhorn/last30days-skill](https://github.com/mvanhorn/last30days-skill) (MIT) — an agent
skill that researches a topic across Reddit, X, YouTube, TikTok, Hacker News, Polymarket,
GitHub and the web, scores results by real engagement, and synthesises one grounded brief.

It is a submodule, not a vendored copy, because it is a versioned Python application (~33 MB,
126 modules) with its own release cadence — a copy would bloat this repo's history on every
re-sync and strand you on a stale version. The submodule records only a commit pointer.
`bootstrap.sh` / `bootstrap.ps1` already run `submodule update --init --recursive`, so it
clones itself during onboarding.

**Prerequisites:** `python3` >= 3.12 and `node` on PATH. There are no pip dependencies — the
runtime is standard library only.

**Activation.** It is a skill, not an instruction: nothing enters your prompt until the agent
invokes it, so it costs nothing on unrelated work. It needs the `chat.agentSkillsLocations`
entry from the settings block above — `.github/shared/vendor/last30days-skill/skills` for the
submodule layout, `${userHome}/copilot-workflow-base/vendor/last30days-skill/skills`
machine-wide.

**Use it** by asking in Copilot Chat, in plain language:

```text
last30days what are people saying about MCP servers
last30days Peter Steinberger
last30days what's trending in AI agents      # topic-less discovery
last30days search my library for MCP servers # offline search of past briefs
```

Verify the install without running any research or touching credentials:

```bash
python3 vendor/last30days-skill/skills/last30days/scripts/last30days.py --preflight
```

Reddit, Hacker News, Polymarket and GitHub work with zero configuration. X, YouTube, TikTok
and the rest unlock by setting API keys or browser sessions — see upstream's
[Bring your own keys](https://github.com/mvanhorn/last30days-skill#bring-your-own-keys) and
[CONFIGURATION.md](https://github.com/mvanhorn/last30days-skill/blob/main/CONFIGURATION.md).
Briefs are written to `~/Documents/Last30Days/` unless `LAST30DAYS_MEMORY_DIR` says otherwise.

**Two things to know.** Its `SKILL.md` is ~258 KB, so an invocation loads far more context
than the rest of this baseline combined — expect it to crowd the window during a run. And to
reach authenticated sources it can read your Chrome/Safari cookie jars; `--preflight` reports
`Browser cookies: off` until you opt in, and reads nothing itself.

**Update** to the latest upstream release, then commit the moved pointer:

```bash
git -C vendor/last30days-skill pull origin main
git add vendor/last30days-skill && git commit -m "chore: bump last30days-skill"
```

**Remove it** with `git rm vendor/last30days-skill` plus the matching
`chat.agentSkillsLocations` line.

## Add it to a repository (one-time)

Run these from the **root of the consuming repo**.

```bash
# 1. add the submodule at .github/shared
git submodule add https://github.com/vishalchovatiya/copilot-workflow-base.git .github/shared

# 2. make future clones/pulls pull submodules automatically
git config submodule.recurse true

# 3. wire VS Code to load BOTH layers (see snippet below), commit, done
git add .gitmodules .github/shared .vscode/settings.json
git commit -m "chore: add copilot-workflow-base shared AI workflow"
```

Add these keys to the consuming repo's `.vscode/settings.json` (merge with what's there —
all paths are workspace-relative and forward-slash, so they work identically on Windows and
Linux):

```jsonc
{
  "github.copilot.chat.codeGeneration.useInstructionFiles": true,
  "chat.useAgentSkills": true,
  "chat.instructionsFilesLocations": {
    ".github/instructions": true,
    ".github/shared/instructions": true
  },
  "chat.promptFilesLocations": {
    ".github/prompts": true,
    ".github/shared/prompts": true
  },
  "chat.agentSkillsLocations": {
    ".github/skills": true,
    ".github/shared/skills": true,
    ".github/shared/vendor/last30days-skill/skills": true
  }
}
```

Then run the bootstrap once (idempotent, safe to re-run):

```bash
bash .github/shared/bootstrap.sh      # Linux / macOS / Git-Bash
# or
pwsh  .github/shared/bootstrap.ps1    # Windows PowerShell
```

## Clone a repo that already uses it

```bash
# <repo-url> is the consuming repo, e.g. chandoo:
git clone --recurse-submodules https://github.com/vishalchovatiya/chandoo.git
# already cloned without --recurse-submodules?
git submodule update --init --recursive
```

## Update the pinned version later

A submodule is pinned to a specific commit. To move a consuming repo to the latest base:

```bash
git -C .github/shared pull origin main   # or: git submodule update --remote .github/shared
git add .github/shared
git commit -m "chore: bump copilot-workflow-base"
```

## Machine-wide setup (every VS Code window)

Use this when you want the baseline in **all** VS Code windows on a machine, independent of
any repo. Instead of vendoring a submodule you point your **User** (global) settings at one
clone.

1. Clone once to a stable path:

   ```bash
   # Linux / macOS
   git clone https://github.com/vishalchovatiya/copilot-workflow-base.git ~/copilot-workflow-base
   ```

   ```powershell
   # Windows PowerShell
   git clone https://github.com/vishalchovatiya/copilot-workflow-base.git "$env:USERPROFILE\copilot-workflow-base"
   ```

2. Open **User** settings JSON (`Ctrl+Shift+P` -> *Preferences: Open User Settings (JSON)*)
   and add these keys as-is. `${userHome}` expands to your home directory on every OS, so
   this snippet is copy-pastable without editing (it resolves to the `~/copilot-workflow-base`
   / `%USERPROFILE%\copilot-workflow-base` clone from step 1):

   ```jsonc
   {
     "github.copilot.chat.codeGeneration.useInstructionFiles": true,
     "chat.useAgentSkills": true,
     "chat.instructionsFilesLocations": {
       "${userHome}/copilot-workflow-base/instructions": true
     },
     "chat.promptFilesLocations": {
       "${userHome}/copilot-workflow-base/prompts": true
     },
     "chat.agentSkillsLocations": {
       "${userHome}/copilot-workflow-base/skills": true,
       "${userHome}/copilot-workflow-base/vendor/last30days-skill/skills": true
     }
   }
   ```

3. Reload the window (`Developer: Reload Window`). Every workspace now loads the baseline on
   top of whatever `.github/` each project provides.

**Does it update instantly?** Yes, effectively. All windows read the same folder, so:

- Editing an instruction/prompt/skill file in that clone is picked up on the **next chat
  request** in every open window — no reload.
- `git pull` in the clone updates every window the same way, on the next request.
- Changing *which folders* are listed (the settings keys themselves) needs a window reload.

This is the opposite of the submodule, which is intentionally **pinned** and only moves when
you run `git submodule update --remote`.

**Caveats:**

- `${userHome}` keeps the path portable across machines/OSes **as long as you clone to
  `~/copilot-workflow-base` everywhere**. If you clone elsewhere, hardcode that absolute path
  instead — but then it is not portable via Settings Sync, so keep it in a machine-specific
  profile.
- The `applyTo: **` baseline instructions now apply to **every** project on the machine —
  that is the intent.
- `.github/workflows/markdown.yml` is irrelevant machine-wide; GitHub Actions only run from a
  repo's own root `.github/workflows/`.

## Why submodule (and not symlinks)

Symlinks into a shared checkout need Developer Mode or admin rights on Windows and behave
differently across filesystems. A submodule plus workspace-relative VS Code settings gives
**identical** behavior on Windows and Linux with no elevated privileges. Skills, prompts,
and instructions are all discovered from the submodule via the `chat.*Locations` settings —
no copying required on VS Code builds that support `chat.agentSkillsLocations`. The
bootstrap scripts include a copy fallback only for older VS Code builds.

## License

MIT — see [LICENSE](LICENSE).

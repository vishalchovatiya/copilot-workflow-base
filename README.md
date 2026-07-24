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
│   ├── markdown.instructions.md              # applyTo: **/*.md
│   ├── python.instructions.md                # applyTo: **/*.py, pyproject.toml, ...
│   ├── readme.instructions.md                # applyTo: **/README.md
│   └── tests.instructions.md                 # applyTo: tests/**
├── prompts/               # shared *.prompt.md (placeholder — add yours here)
├── skills/
│   └── boost-prompt/SKILL.md
├── scripts/
│   └── check_markdown.py  # section numbering + TOC + table-alignment checker/fixer
├── .github/workflows/
│   └── markdown.yml        # self-lints this repo's own markdown
├── bootstrap.sh            # POSIX onboarding (Linux/macOS/Git-Bash)
├── bootstrap.ps1           # PowerShell onboarding (Windows)
├── LICENSE                 # MIT
└── README.md              # this file
```

Nothing here mentions any single project — it is deliberately domain-neutral so it can be
consumed by many repos at once.

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
    ".github/shared/skills": true
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
       "${userHome}/copilot-workflow-base/skills": true
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

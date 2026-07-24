# copilot-workflow-base

Reusable **GitHub Copilot / VS Code AI-workflow baseline** — a single set of generic
instructions, skills, prompts, and helper scripts that you drop into any repository as a
git **submodule** so every project shares the same baseline Copilot behavior while keeping
its own domain-specific `.github/` content layered on top.

The two layers **combine**, they do not replace each other: your repo keeps its own
`.github/copilot-instructions.md` and repo-specific `instructions/`, `prompts/`, `skills/`,
and this submodule adds the generic baseline through committed VS Code settings.

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

Run these from the **root of the consuming repo**. Replace the URL with this repo's remote.

```bash
# 1. add the submodule at .github/shared
git submodule add https://github.com/<you>/copilot-workflow-base.git .github/shared

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
git clone --recurse-submodules <repo-url>
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

## Why submodule (and not symlinks)

Symlinks into a shared checkout need Developer Mode or admin rights on Windows and behave
differently across filesystems. A submodule plus workspace-relative VS Code settings gives
**identical** behavior on Windows and Linux with no elevated privileges. Skills, prompts,
and instructions are all discovered from the submodule via the `chat.*Locations` settings —
no copying required on VS Code builds that support `chat.agentSkillsLocations`. The
bootstrap scripts include a copy fallback only for older VS Code builds.

## License

MIT — see [LICENSE](LICENSE).

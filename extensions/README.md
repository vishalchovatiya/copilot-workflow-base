**Table of Contents**

- [1. Overview](#1-overview)
- [2. Available Extensions](#2-available-extensions)
- [3. Installing](#3-installing)
- [4. Adding a New Extension](#4-adding-a-new-extension)
  - [4.1. Layout Convention](#41-layout-convention)
  - [4.2. Required Manifest Fields](#42-required-manifest-fields)
  - [4.3. Ground Rules](#43-ground-rules)

## 1. Overview

VS Code extensions vendored alongside the instruction/prompt/skill layer. Unlike those, VS
Code offers no setting that points at an arbitrary extension folder, so [install.ps1](install.ps1)
/ [install.sh](install.sh) link each folder here into `~/.vscode/extensions`. The code stays
in this clone and updates on `git pull`; only a window reload is needed.

---

## 2. Available Extensions

| #   | Folder                          | What it does                                                     |
| --- | ------------------------------- | ---------------------------------------------------------------- |
| 1   | [md-flashcards](md-flashcards/) | Anki-style spaced repetition over any `::` line in your Markdown |

---

## 3. Installing

`bootstrap.ps1` / `bootstrap.sh` at the repo root run this for you, so normally there is
nothing to do. To drive it directly:

```powershell
pwsh extensions/install.ps1                  # all extensions
pwsh extensions/install.ps1 md-flashcards    # one, by folder name
pwsh extensions/install.ps1 -List            # show what would be installed
pwsh extensions/install.ps1 -Uninstall       # remove them again
```

```bash
bash extensions/install.sh                   # same flags as --long-options
bash extensions/install.sh md-flashcards
bash extensions/install.sh --list
bash extensions/install.sh --uninstall
```

Add `-Copy` / `--copy` on filesystems that refuse junctions or symlinks — that variant must
be re-run after every `git pull`. Add `-Insiders` / `--insiders` to target VS Code Insiders.

---

## 4. Adding a New Extension

### 4.1. Layout Convention

Create a folder here; the installer discovers it on the next run with no script changes:

```
extensions/
├── install.ps1          # generic installer - never edit when adding an extension
├── install.sh
├── README.md            # this file (add a row to the table above)
└── my-extension/
    ├── package.json     # manifest (see below)
    ├── src/
    │   └── extension.js # entry point named by "main"
    └── README.md        # what it does, settings, troubleshooting
```

### 4.2. Required Manifest Fields

A folder is only treated as an extension when its `package.json` declares all four:

| #   | Field            | Purpose                                                             |
| --- | ---------------- | ------------------------------------------------------------------- |
| 1   | `publisher`      | Use `local` — these are never published to the Marketplace          |
| 2   | `name`           | Folder name; combines into the extension id `local.<name>`          |
| 3   | `version`        | Bump it when behaviour changes; the installer replaces old versions |
| 4   | `engines.vscode` | Minimum VS Code version, e.g. `^1.85.0`                             |

Anything without all four is skipped with a warning, so scratch folders are harmless.

### 4.3. Ground Rules

Keep new extensions consistent with what is already here:

1. **No dependencies, no build step.** Plain CommonJS against the VS Code API. Anything
   needing npm, TypeScript, or a bundler defeats the point of a clone-and-go baseline.
2. **No `node_modules`.** If a package feels unavoidable, reconsider the feature first.
3. **State in the consuming repo**, in sorted plain text, so it is diffable and travels
   through git rather than a hidden global store.
4. **Read user files non-destructively.** Never rewrite notes or source as a side effect.
5. **Webviews stay locked down**: nonce CSP, `localResourceRoots: []`, and HTML-escape
   anything read from disk before rendering it.
6. Document it in its own `README.md` and add a row to
   [Available Extensions](#2-available-extensions).

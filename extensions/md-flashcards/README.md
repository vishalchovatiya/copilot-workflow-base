**Table of Contents**

- [1. Overview](#1-overview)
- [2. Repo Structure](#2-repo-structure)
- [3. Quick Start](#3-quick-start)
  - [3.1. Why Not a Settings Path Like Skills?](#31-why-not-a-settings-path-like-skills)
- [4. Usage](#4-usage)
  - [4.1. Launching a Session](#41-launching-a-session)
  - [4.2. Keyboard Shortcuts](#42-keyboard-shortcuts)
- [5. Writing Cards](#5-writing-cards)
  - [5.1. The `::` Rule](#51-the--rule)
  - [5.2. Per-Section vs Per-File](#52-per-section-vs-per-file)
- [6. Scheduling](#6-scheduling)
  - [6.1. Algorithm](#61-algorithm)
  - [6.2. State Schema](#62-state-schema)
  - [6.3. Worked Example](#63-worked-example)
- [7. Settings](#7-settings)
- [8. Troubleshooting](#8-troubleshooting)

## 1. Overview

Anki-style spaced repetition that reads your existing Markdown notes directly. Any line
containing `::` becomes a card — text before the delimiter is the front, text after is the
back. Nothing is copied into a deck format, no note is ever modified, and the only state the
system owns is one sorted JSON file you commit alongside your notes.

Zero runtime dependencies: plain CommonJS against the VS Code API, no build step, no npm
install, no bundler.

---

## 2. Repo Structure

```
extensions/
├── install.ps1              # shared installer for every vendored extension
├── install.sh
└── md-flashcards/
    ├── src/
    │   ├── extension.js     # commands, context menus, session loop
    │   ├── parser.js        # `::` extraction (also runnable standalone)
    │   ├── scheduler.js     # SM-2 intervals and ease
    │   ├── store.js         # sorted-JSON state read/write
    │   └── webview.js       # review panel markup (escaped, CSP-locked)
    ├── samples/
    │   └── sample-cards.md  # example note showing both card types
    ├── package.json         # manifest: commands, submenu, settings
    └── README.md            # this file
```

---

## 3. Quick Start

On a fresh machine, with VS Code already installed:

```powershell
# Windows
git clone https://github.com/vishalchovatiya/copilot-workflow-base.git "$env:USERPROFILE\copilot-workflow-base"
pwsh "$env:USERPROFILE\copilot-workflow-base\bootstrap.ps1"
```

```bash
# Linux / macOS / Git-Bash
git clone https://github.com/vishalchovatiya/copilot-workflow-base.git ~/copilot-workflow-base
bash ~/copilot-workflow-base/bootstrap.sh
```

Then run **Developer: Reload Window** in VS Code. `bootstrap` installs every extension under
`extensions/` as its first step, so this is the *same* one-time command that wires up your
instructions, prompts, and skills — there is no separate flashcard install. Skip it with
`-NoExtensions` / `--no-extensions`, or drive the shared installer directly:

```powershell
pwsh extensions/install.ps1 md-flashcards              # install just this one
pwsh extensions/install.ps1 md-flashcards -Uninstall   # remove it
```

Add `-Copy` / `--copy` on filesystems that refuse links; that variant must be re-run after
every `git pull`. See [../README.md](../README.md) for the full installer reference and how to
add another extension.

The installer creates a junction (Windows) or symlink (POSIX) into the VS Code extensions
folder, so `git pull` updates the extension in place; only a window reload is needed.

### 3.1. Why Not a Settings Path Like Skills?

Instructions, prompts, and skills are loaded from arbitrary folders because VS Code exposes
`chat.instructionsFilesLocations`, `chat.promptFilesLocations`, and
`chat.agentSkillsLocations`. **There is no equivalent setting for extensions.** VS Code
discovers extensions from exactly three places: the extensions directory
(`~/.vscode/extensions`), an installed `.vsix`, and `--extensionDevelopmentPath` (which only
applies to a debug window). So the folder has to be present there.

The link created by the installer is the closest possible equivalent: the extensions
directory holds a pointer, while the real code stays in this clone and updates on `git pull`.
Building a `.vsix` instead would add `@vscode/vsce`, an npm install, and a rebuild-per-change
loop — strictly more setup for less freshness.

Preview what a note yields without launching VS Code:

```bash
node extensions/md-flashcards/src/parser.js path/to/note.md
```

---

## 4. Usage

### 4.1. Launching a Session

Right-click any `.md` file — in the Explorer, in the editor, or on the editor tab — and pick
**Flashcards**:

| #   | Menu entry                         | What it reviews                                                                                                         |
| --- | ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| 1   | Practice Section...                | Quick-pick of every heading that contains cards; the section at your cursor is listed first. Sub-headings are included. |
| 2   | Practice Whole File                | Every card in the file                                                                                                  |
| 3   | Practice All Due Cards (Workspace) | Every due card across all `.md` files in the workspace                                                                  |
| 4   | Show Card Count for File           | Cards / sections / due / new, without starting a session                                                                |

The same commands are on the Command Palette under `Flashcards:`.

**Practising a file or a section always covers every card in it** — nothing is dropped and
nothing is capped. Cards that are due (never-reviewed ones count as due) are shuffled to the
front, then the cards already scheduled for a later date follow, also shuffled. The
workspace-wide sweep is the exception: it takes due cards only and caps the run at
`mdFlashcards.sessionLimit`, since that pool spans every note you own.

The shuffle is **Fisher-Yates**, which makes every ordering equally likely. The common
`sort(() => Math.random() - 0.5)` one-liner is not used: it is measurably biased and tends to
leave cards near their original neighbours, so a note's list order would leak into the
session.

Notes and state are re-read from scratch at the start of every session — nothing is cached.
Edit a note, add a `::`, fix a typo, or `git pull` someone else's changes, and the very next
session sees it. Unsaved edits count too: if the note is open with unsaved changes the dirty
buffer is used, otherwise the bytes on disk are read directly. The only thing that needs a
window reload is a change to the extension's own source.

### 4.2. Keyboard Shortcuts

Number keys are the only keyboard input the panel accepts:

| #   | Key           | Action                                                        |
| --- | ------------- | ------------------------------------------------------------- |
| 1   | `0`           | Reveal the back                                               |
| 2   | `1`           | **Again** — forgot it; ease −0.20, due again today            |
| 3   | `2`           | **Hard** — recalled with effort; ease −0.15, interval × 1.2   |
| 4   | `3`           | **Good** — recalled; interval × ease                          |
| 5   | `4`           | **Easy** — instant; ease +0.15, interval × ease × 1.3         |
| 6   | anything else | Nothing at all — no key advances or grades a card by accident |

`1`-`4` are inert until the back is showing, key repeat is ignored so holding a number cannot
burn through the queue, and modifier combos (`Ctrl+3`) pass through to VS Code untouched.
Close the panel tab to end a session; everything graded so far is already saved.

Each grade button shows the interval it would produce, exactly like Anki.

A card you grade **below Good** does not leave the session: it is pushed back into the queue
four cards later and keeps returning until you finally grade it **Good** or **Easy**. So
*Again* and *Hard* both mean "show me this again today", and the session length grows as you
struggle. Change where that line sits with `mdFlashcards.repeatUntilGrade` — set it to `hard`
if only *Again* should repeat, `easy` if even *Good* should repeat, or `again` to switch
in-session repeats off entirely.

The file path in the top-right corner is a link: click it to jump straight to that card's
line in the note. The note opens in the column next to the panel, so the session stays on
screen — fix the typo, click back on the panel, and keep grading. Edits are picked up by the
next session.

---

## 5. Writing Cards

### 5.1. The `::` Rule

A card is any line where `::` is followed by whitespace or end-of-line:

```markdown
Ease factor:: multiplier applied to the interval after a "Good" answer
```

That lookahead is deliberate — `std::vector`, `https://`, and `A::B::C` are never mistaken
for cards. Lines inside fenced code blocks and headings are skipped entirely.

The back absorbs any following lines indented deeper than the card line, so nested bullets
and indented code fences stay with their answer. A deeper line that is *itself* a card stops
the absorption and becomes its own card:

```markdown
1. Punctuation rules
   1. Use `!` to express:: feeling, in informal email only
      1. I am so excited to meet you!
      2. I am thrilled to hear about your achievements!
   2. Use `;` to:: join two independent clauses
```

That yields two cards; the numbered examples become part of card one's back.

A card with an empty back (`Throw me 3 addition connectors::`) is kept — those are useful
self-test cues — and the panel simply shows *(no answer text)*.

### 5.2. Per-Section vs Per-File

Both modes read the same cards; they differ only in scope:

| #   | Mode        | Scope                                                                                                                          |
| --- | ----------- | ------------------------------------------------------------------------------------------------------------------------------ |
| 1   | Per-section | Cards whose enclosing heading chain contains the chosen heading, so picking `## 4. Writing` also reviews `### 4.5. Connectors` |
| 2   | Per-file    | Every card in the file, regardless of heading                                                                                  |

---

## 6. Scheduling

### 6.1. Algorithm

SM-2, the algorithm behind Anki's default scheduler, with intra-day learning steps dropped.

| #   | Option                    | Pros                                                           | Cons                                                                                   |
| --- | ------------------------- | -------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| 1   | **SM-2 (chosen)**         | Per-card ease adapts to difficulty; well understood; ~60 lines | Two numbers per card instead of one                                                    |
| 2   | Fixed ladder (1/3/7/21 d) | Trivial to reason about; one field of state                    | Every card moves at the same speed — hard cards under-drilled, easy cards over-drilled |
| 3   | FSRS                      | Best retention per review                                      | Needs a trained weight model and review history; far too much machinery here           |

SM-2 wins because the extra state is one float and the adaptivity is exactly what makes long
vocabulary lists (your `5.2. No Common Vocabulary` section) bearable.

Intervals are whole days; an interval of `0` means "still due today" and the session queue
handles the repeat. Ease is clamped to a 1.3 floor and intervals cap at 3650 days.

### 6.2. State Schema

One file per workspace, default `.flashcards/state.json`, keys sorted so git diffs stay
minimal. `note` and `front` exist purely so the file reads sensibly on its own.

```json
{
  "version": 1,
  "cards": {
    "3a1790bd5345": {
      "note": "PR/CELPIP.md",
      "front": "Template(ICC/R) to make simple sentence(s) into complex sentence",
      "due": "2026-08-14",
      "interval": 4,
      "ease": 2.3,
      "reps": 6,
      "lapses": 1,
      "reviewed": "2026-08-10"
    }
  }
}
```

The card id is the first 12 hex of `sha1(relativePath + "\0" + normalizedFront)`, where the
front is lowercased with list markers and emphasis stripped. Consequences worth knowing:

1. Rewording the **back** keeps all history.
2. Rewording the **front** starts a fresh card; the old entry is simply ignored.
3. Moving a card within a file keeps history; moving it to another file does not.
4. Two identical fronts in one file get `#2`, `#3` suffixes based on document order.

### 6.3. Worked Example

Starting from a brand-new card on 2026-08-10 (verified output of `scheduler.review`):

| #   | Grade | Interval  | Ease | Due        | Reps | Lapses |
| --- | ----- | --------- | ---- | ---------- | ---- | ------ |
| 1   | Good  | 1         | 2.50 | 2026-08-11 | 1    | 0      |
| 2   | Good  | 3         | 2.50 | 2026-08-13 | 2    | 0      |
| 3   | Again | 0 (today) | 2.30 | 2026-08-10 | 3    | 1      |
| 4   | Good  | 1         | 2.30 | 2026-08-11 | 4    | 1      |
| 5   | Easy  | 3         | 2.45 | 2026-08-13 | 5    | 1      |
| 6   | Hard  | 4         | 2.30 | 2026-08-14 | 6    | 1      |

Row 3 is the important one: a lapse wipes the interval, drops the ease, and the card returns
inside the same session — after which it climbs again from a permanently lower ease.

---

## 7. Settings

| #   | Setting                         | Default                                          | Purpose                                                                                                 |
| --- | ------------------------------- | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------- |
| 1   | `mdFlashcards.stateFile`        | `.flashcards/state.json`                         | Workspace-relative path of the state file                                                               |
| 2   | `mdFlashcards.sessionLimit`     | `30`                                             | Cap on the **workspace-wide** sweep only; `0` disables it. File and section sessions are never capped   |
| 3   | `mdFlashcards.repeatUntilGrade` | `good`                                           | Keep re-showing a card in the session until it is graded at least this well (`again` turns repeats off) |
| 4   | `mdFlashcards.exclude`          | `**/node_modules/**`, `**/.git/**`, `**/Hide/**` | Globs skipped by the workspace-wide scan                                                                |

Commit `.flashcards/state.json` to git — that is the whole sync story across machines.

---

## 8. Troubleshooting

| #   | Symptom                                | Fix                                                                                                                                                                 |
| --- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | No **Flashcards** entry on right-click | Run **Developer: Reload Window**; confirm the folder exists under `~/.vscode/extensions`                                                                            |
| 2   | "No `::` cards found"                  | The `::` needs a space or line end after it; check the line is not inside a fence                                                                                   |
| 3   | A card lost its history                | Its front text changed — expected; see [6.2](#62-state-schema)                                                                                                      |
| 4   | Junction/symlink refused               | Re-run the installer with `-Copy` / `--copy`, and re-run it after each `git pull`                                                                                   |
| 5   | Want to reset one card                 | Delete its entry from `.flashcards/state.json`                                                                                                                      |
| 6   | `0`-`4` do nothing                     | The panel needs keyboard focus — click once anywhere inside it. If it still ignores keys after **Developer: Reload Window**, the old extension code is still loaded |

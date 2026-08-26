---
name: deck-builder
description: "Turn a topic, a set of notes or an existing deck into a fully-editable PowerPoint .pptx using the deckforge package: content-only spec, theme tokens, harvested corporate template, reusable design artifacts, then a build-verify-inspect loop. Use whenever the user wants slides, a presentation or a deck, or wants design harvested out of an existing .pptx. Trigger phrases: 'make me a deck', 'build a presentation on', 'turn these notes into slides', 'create slides for', 'generate a pptx', 'extract the design from this pptx', 'harvest a template from this deck', 'reuse the diagram from that deck', 'make this deck on-brand', 'add a slide to the deck'. Also trigger when the user points at a .pptx file and asks for its structure, palette, layouts or reusable graphics."
---

# Deck Builder

Take a raw topic and produce a `.pptx` that a human can open, select any shape, retype
it and restyle it. Content comes from the user; every colour, coordinate and type size
comes from theme tokens; the design vocabulary comes from decks that already exist.

## Table of Contents

- [1. Three Hard Rules](#1-three-hard-rules)
- [2. Locate the Toolchain](#2-locate-the-toolchain)
- [3. Workflow](#3-workflow)
- [4. Writing the Spec](#4-writing-the-spec)
- [5. Archetypes](#5-archetypes)
- [6. Reusing Harvested Design](#6-reusing-harvested-design)
- [7. Verify and Inspect](#7-verify-and-inspect)
- [8. Anti-Patterns](#8-anti-patterns)
- [9. Validation Checklist](#9-validation-checklist)

## 1. Three Hard Rules

These override everything else.

**Rule 1 — Ask where the deck should land, then default.** Before the first build, ask
the user which directory the finished `.pptx` belongs in. If they do not name one, use
`PRESENTATION/` in the current workspace and say so. Pass it as `--out`; never scatter
decks into the repository root.

**Rule 2 — Never invent a fact to fill a slide.** No price, benchmark, percentage or
committed date that the user did not supply. An unknown is written as an unknown, with
a named owner and a written deliverable attached, and it renders as an explicit marker.
A slide that looks complete because you guessed is worse than a slide with a gap.

**Rule 3 — Nothing is done until you have looked at it.** Build, verify, rasterise,
inspect the images, fix, repeat. "The build passed" is not "the deck is good": overflow,
collisions and dead whitespace do not appear in the XML.

> **Bottom line —** Ask where it goes, never fabricate, and always look at what you made.

## 2. Locate the Toolchain

The package ships inside this workflow bundle, which loads from one of two layouts. Do
not hardcode a path — find the launcher first:

- **Submodule layout**: `.github/shared/scripts/deck.py`
- **Machine-wide layout**: the standalone clone, e.g. `~/copilot-workflow-base/scripts/deck.py`

```bash
DECK="$(find "$HOME/copilot-workflow-base/scripts" .github/shared/scripts -name deck.py 2>/dev/null | head -n1)"
python "$DECK" doctor
```

```powershell
$deck = Get-ChildItem "$HOME\copilot-workflow-base\scripts", ".github\shared\scripts" -Filter deck.py -ErrorAction SilentlyContinue | Select-Object -First 1
python $deck.FullName doctor
```

`doctor` reports the render tiers, the discoverable themes and the default output
directory. Run it first: it tells you whether you will get a visual pass or only a
structural one. If `python-pptx` or `PyYAML` is missing, install both before going on.

> **Bottom line —** Resolve the launcher dynamically and let `doctor` tell you what this
> machine can do before you promise the user a rendered deck.

## 3. Workflow

1. **Scope the argument, not the slide count.** Ask at most two questions: who is in the
   room and what decision you want out of them. Never ask the user to describe layout.
2. **Get a template.** If the user has a branded deck, harvest it — that is the only way
   to get their master, layouts, fonts and logo. If they have none, use the shipped
   neutral theme and its generated base template, and say the deck is unbranded.
3. **Mine it for design.** Run `extract` on the same deck to build an artifact library,
   then read its `outline.md`, `colors.json` and `fonts.json` before writing a spec.
   Decks built against a real library look like the user's other decks; decks built
   against guesses do not.
4. **Outline as a chain of questions.** Each section states the question it answers and
   raises the next one. Motivation before mechanism, always. Close on one picture of the
   whole argument.
5. **Write the spec.** Content only. See [4. Writing the Spec](#4-writing-the-spec).
6. **Build.** One command builds, verifies and rasterises.
7. **Inspect and fix.** See [7. Verify and Inspect](#7-verify-and-inspect).
8. **Report.** Say where the deck is, which renderer tier ran, what you could not verify,
   and every unknown still marked in the deck.

```bash
python "$DECK" harvest "/path/to/their deck.pptx" --name acme --out ~/decks
python "$DECK" extract "/path/to/their deck.pptx" --library ~/decks/artifacts/acme
python "$DECK" build ~/decks/specs/topic.deck.yaml --theme acme --out ~/decks
```

```powershell
python $deck.FullName harvest "C:\path\to\their deck.pptx" --name acme --out $HOME\decks
python $deck.FullName extract "C:\path\to\their deck.pptx" --library $HOME\decks\artifacts\acme
python $deck.FullName build $HOME\decks\specs\topic.deck.yaml --theme acme --out $HOME\decks
```

Harvesting reports the theme colours with their theme slots, the major and minor fonts,
and every layout with its index. Copy those into a new theme token file to make the
brand available to every future spec.

> **Bottom line —** Harvest first, mine second, outline third; the spec is the last thing
> you write, not the first.

## 4. Writing the Spec

The spec is YAML and carries narrative only. A colour, a size or a coordinate in a spec
is a validation error, not a style choice.

```yaml
deck:
  title: Shrinking the feedback loop
  subtitle: Why a two-day review cycle is a design problem
  theme: acme
  agenda: true
  artifacts: acme

entities:                       # one colour per recurring entity, held deck-wide
  Handoff: alert
  Automation: primary

sections:
  - name: Where the time goes
    question: If everyone is working flat out, what is the loop waiting on?
    slides:
      - archetype: bullets
        title: A change waits far longer than it runs
        entity: Handoff
        takeaway: The loop is dominated by waiting, not by work.
        content:
          bullets:
            - Writing the change takes under an hour
            - The first automated signal arrives the next morning
        unknowns:
          - item: Machine cost per change
            owner: Platform owner
            deliverable: Costed estimate before the trial starts
        notes: |
          What to say, which objection to expect, what not to promise.
```

Writing rules the builder enforces, so write to them from the start:

| #   | Rule                    | Why                                                                  |
| --- | ----------------------- | -------------------------------------------------------------------- |
| 1   | Short bullets, few      | Surplus is routed into the notes; long ones are rejected             |
| 2   | One takeaway per slide  | It renders as the callout; it is the slide's whole point             |
| 3   | Notes on every slide    | The argument lives here, not on the slide                            |
| 4   | Titles never wrap       | An over-long title is rejected rather than shrunk                    |
| 5   | Declare entities once   | The colour code must still read on the last slide                    |
| 6   | Unknowns carry an owner | An owner and a deliverable are what keep a gap from becoming a guess |

Prefer the visual archetype over the bullet list. If a slide is a list of three parallel
things, it is `cards`. If it is a sequence, it is `process`. If it is a contrast, it is
`panels`. Reach for `bullets` when the content is genuinely one short argument.

> **Bottom line —** Write the argument and the notes; let the archetype and the theme
> decide everything that is visible.

## 5. Archetypes

| #   | Archetype   | Use when                                                   |
| --- | ----------- | ---------------------------------------------------------- |
| 1   | `title`     | Slide 1 only                                               |
| 2   | `agenda`    | Generated from the sections; override only to reword it    |
| 3   | `section`   | Divider showing the section question and agenda progress   |
| 4   | `bullets`   | One short argument, optionally under a lead line           |
| 5   | `cards`     | Two to five parallel ideas                                 |
| 6   | `process`   | A left-to-right sequence, five steps at most               |
| 7   | `panels`    | A versus B, or blockers versus enablers                    |
| 8   | `checklist` | Do and do-not, review gates                                |
| 9   | `table`     | Comparison or rubric; add a legend if it carries scores    |
| 10  | `artifact`  | A harvested diagram, table or SmartArt, retargeted         |
| 11  | `statement` | One line, full bleed; closing only                         |
| 12  | `summary`   | The closing picture of the whole argument — always include |

`process`, `cards` and `panels` **rebuild** SmartArt-style layouts from native
autoshapes, which is what makes them recolourable by theme. Only `artifact` can place
real SmartArt, by cloning a harvested `graphicFrame` with its `dgm` parts. Never tell a
user a rebuilt chevron chain is SmartArt.

> **Bottom line —** Pick the archetype that matches the shape of the thought, and say
> honestly which ones are true SmartArt.

## 6. Reusing Harvested Design

This is what makes consecutive decks look like one family, so treat it as the first
tool, not the last.

```bash
python "$DECK" artifacts --library ~/decks/artifacts/acme --search roadmap
```

```powershell
python $deck.FullName artifacts --library $HOME\decks\artifacts\acme --search roadmap
```

Search the library by text before drawing anything new. When you find one, place it and
retarget its text in slot order:

```yaml
- archetype: artifact
  title: The same picture, one deck later
  content:
    artifact: group-11-the-same-picture-reused-from
    text: [Author, Signal, Review, Merge]
    caption: Placed from the artifact library, recoloured to the active theme.
```

The shape tree is deep-copied so everything stays native, the text slots are retargeted
in order, and explicit colours are remapped to the active theme while theme-colour
references are left alone, because those already follow the new theme.

> **Bottom line —** Search the library first; a reused artifact carries the brand better
> than anything you can draw from scratch.

## 7. Verify and Inspect

`build` verifies automatically and rasterises when a renderer is present. Read the
report, fix every finding, rebuild. Then look at the slides — that step is not optional
and it is not satisfied by the structural pass.

Inspecting a fifteen-slide deck one image at a time is wasteful. Tile the rendered PNGs
into a few downscaled contact sheets and read those instead; it costs a fraction as much
and still shows overflow, collisions, misalignment and dead whitespace. Zoom into a
single slide only when a sheet shows something suspicious.

What to look for, in order:

1. Text crossing a card, panel or table edge.
2. Two shapes overlapping where they should not.
3. A block floating in the middle of the slide with a dead band above the callout.
4. Rows of cards whose labels or body text do not share a baseline.
5. A title that wrapped, or a label clipped by a chevron notch.
6. Any element drawn over the logo or the footer band.

If no renderer is available, say so explicitly in the final report and list what the
structural pass could not cover. Do not imply you looked at slides you never saw.

> **Bottom line —** Contact-sheet the render, fix what you see, and never claim a visual
> pass you did not perform.

## 8. Anti-Patterns

| #   | Trap                                  | Do instead                                            |
| --- | ------------------------------------- | ----------------------------------------------------- |
| 1   | Starting from a bare `Presentation()` | Harvest a template, or use the generated neutral base |
| 2   | Putting a colour in the spec          | Declare an entity and let the theme colour it         |
| 3   | Shrinking type so content fits        | Cut the content or move it to the notes               |
| 4   | Ten bullets on one slide              | Split the slide, or route the surplus into the notes  |
| 5   | Guessing a number to fill a table     | Mark it unknown with an owner and a deliverable       |
| 6   | Pasting an image of a diagram         | Build it from native shapes or reuse an artifact      |
| 7   | Declaring done after a clean build    | Rasterise and inspect first                           |

> **Bottom line —** Every trap here is a shortcut that trades an invisible failure now
> for a visible one in front of an audience.

## 9. Validation Checklist

- [ ] The output directory was agreed with the user, or defaulted to `PRESENTATION/`
      and stated.
- [ ] The deck was built from a harvested template, or the user was told it is unbranded.
- [ ] The artifact library was searched before any new diagram was drawn.
- [ ] The spec contains no colour, size or coordinate.
- [ ] Every slide has one takeaway and speaker notes.
- [ ] Motivation slides precede mechanism slides, and the deck closes on one picture.
- [ ] Entity colours are declared once and are consistent to the last slide.
- [ ] No number, date or benchmark was invented; every unknown carries an owner and a
      deliverable.
- [ ] Verification reports no findings.
- [ ] The rendered slides were inspected, or the missing renderer was reported.
- [ ] The final report states the deck path, the renderer tier and every known
      limitation.

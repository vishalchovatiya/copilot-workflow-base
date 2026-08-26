---
description: "Rules for generating fully-editable PowerPoint decks with the deckforge package: content-only specs, theme tokens, the alignment grid, slide archetypes, artifact reuse, the content budget and the build-verify loop. Applies to deck specs, theme token files and deck builder code."
applyTo: "**/*.deck.yaml,**/*.deck.yml,**/deckforge/**,**/PRESENTATION/**,**/*deck*.py"
---

# Deck Design Rules

Rules for building presentation decks programmatically so they come out on-brand,
editable and defensible without manual cleanup in PowerPoint. They encode the
separation between content and design, the content budget, and the verification loop.

## Table of Contents

- [1. Non-Negotiable](#1-non-negotiable)
- [2. Content and Design Never Mix](#2-content-and-design-never-mix)
- [3. Content Budget](#3-content-budget)
- [4. Narrative Shape](#4-narrative-shape)
- [5. Colour and Type](#5-colour-and-type)
- [6. Diagrams and SmartArt](#6-diagrams-and-smartart)
- [7. Honesty Rules](#7-honesty-rules)
- [8. Build and Verify](#8-build-and-verify)
- [9. Extending the System](#9-extending-the-system)
- [10. Validation Checklist](#10-validation-checklist)

## 1. Non-Negotiable

- **Everything stays editable.** Every element is a native shape, text frame or table.
  A rasterised diagram, a screenshot of a chart or a flattened image of text is a
  failure, not a shortcut.
- **Always build from a template file.** `Presentation()` with no argument yields the
  stock Office template: no branding, no corporate fonts, no logo. Load a harvested
  template, or the generated neutral base, every time.
- **No hex value and no coordinate in Python.** Colour, geometry, spacing and type
  sizes come from the theme token file. A literal in the builder is a bug.
- **No styling in a spec.** A spec carries sections, slide intents, bullets, takeaways
  and speaker notes. A colour, size or coordinate in a spec is rejected by validation.
- **Every slide carries speaker notes.** The notes pane holds the argument, the
  objection to expect and what not to promise. An empty notes pane fails validation.
- **Every slide states one takeaway.** One claim per slide, rendered as the visually
  distinct callout. If a slide has no takeaway worth one sentence, delete the slide.
- **Never ship unverified.** Run the build's verification pass, and look at the
  rasterised slides when a renderer is available. Overflow and collisions are invisible
  in the XML.

## 2. Content and Design Never Mix

Three files decide what a deck looks like, and none of them is the spec:

| #   | File                     | Owns                                                       |
| --- | ------------------------ | ---------------------------------------------------------- |
| 1   | `themes/<name>.yaml`     | Palette, semantic roles, type scale, grid, spacing, budget |
| 2   | `templates/<name>.pptx`  | Master, layouts, theme part, fonts, logo                   |
| 3   | `specs/<name>.deck.yaml` | Sections, slides, bullets, takeaways, notes                |

The test of a good spec: render it against a second theme token file and you get the
same argument, on a different brand, with no edit to the spec. If that is not true,
styling has leaked into the content.

Adding a corporate look is a drop-in, never a code change: harvest the template, copy
the reported palette and layout indices into a new token file, and build with
`--theme <brand>`.

## 3. Content Budget

The budget lives in the theme tokens and the builder enforces it. Do not raise a limit
to make content fit; cut the content or move it into the notes.

| #   | Limit                | Behaviour when exceeded                            |
| --- | -------------------- | -------------------------------------------------- |
| 1   | Bullets per slide    | Surplus routed into the speaker notes, or rejected |
| 2   | Words per bullet     | Rejected — rewrite the bullet, do not shrink type  |
| 3   | Title length         | Rejected — shorten the title, do not let it wrap   |
| 4   | Takeaway length      | Rejected — one sentence, not two                   |
| 5   | Minimum notes length | Rejected — the argument belongs in the notes       |

Slides are visual-first and text-minimal: the text on the slide anchors a visual, and
everything else goes to the notes pane. Never let type shrink silently to accommodate
overflow — a title steps down through the measured type scale, and anything else fails
loudly.

## 4. Narrative Shape

The deck is one gradual reveal, exactly like the knowledge-doc story spine:

- **Each slide answers the question the previous slide raised.** Sections declare that
  question explicitly, and the section divider shows it.
- **Motivation precedes mechanism.** Problem and cost slides come before the slides
  that explain how anything works. A mechanism slide that arrives before its motivation
  is in the wrong place.
- **The agenda is explicit and generated.** One agenda slide from the section list, one
  divider per section showing progress through it.
- **The deck closes on one picture.** A single visual summary slide that shows the
  whole argument at once, built from the entities the deck already taught.

## 5. Colour and Type

- **One palette, one type scale, whole deck.** Both come from the theme tokens.
- **Semantic colour coding is declared once and applied everywhere.** A recurring
  entity declared in the spec keeps its colour in cards, panels, tables, diagrams and
  the summary. A reader who learns the code early must be able to read the last slide
  without a legend.
- **Colour codes through fills, bars and borders — never through font colour.** Body
  text is the ink colour, secondary text is the muted colour, and text on a
  full-strength ground is white. No other font colour is permitted.
- **Large fills are tints; saturated colour is reserved for accents.** A large shape
  takes a light tint of a role colour; full strength appears in thin bars, borders and
  connectors. The tint and its full-strength partner always appear together.
- **Everything snaps to one grid with one left margin.** Alignment, gutters, padding
  and block heights all come from tokens. Nothing is placed by eye.

## 6. Diagrams and SmartArt

- **Native autoshapes and connectors only.** No images of diagrams.
- **`python-pptx` cannot author SmartArt.** Real SmartArt is a `graphicFrame` pointing
  at `dgm` data, layout, style and colour parts. Two honest options exist, and the
  archetype documentation must say which one it uses:
  1. **Rebuild** the layout from native autoshapes — fully recolourable from tokens,
     and the default for process chains, card rows and comparison panels.
  2. **Clone** a harvested SmartArt frame together with its `dgm` parts and retarget
     its text — the only way to get true SmartArt, and it keeps its source colours.
- **Never claim SmartArt where none exists.** A rebuilt chevron chain is a chevron
  chain, not SmartArt.
- **Kill the inherited shadow on every shape and connector.** The default theme shadow
  makes a generated diagram look like clip art.
- **Inset labels past a notch.** Chevrons, pentagons and similar shapes have a notch
  whose depth follows the shape adjustment; a label that ignores it clips.
- **Keep diagrams legible, not complete.** Cap a chain at five steps and push the
  detail into the notes.

## 7. Honesty Rules

- **Never fabricate a number.** Prices, benchmarks, percentages and committed dates are
  either sourced or unknown. An unknown is rendered as an explicit placeholder paired
  with a named owner and a written deliverable — never invented to fill a cell.
- **Label a claim as a claim.** "Vendor-claimed, unverified" is acceptable; presenting
  it as a measurement is not.
- **A scored table carries a legend** defining every symbol and stating the evidence
  basis.

## 8. Build and Verify

Build, verify and rasterise in one command, then look at the slides. The renderer is
tiered and the report names the tier it used: a pure-Python structural pass always
runs, LibreOffice headless is the portable raster path, and PowerPoint automation is an
optional faster path when present.

The structural pass catches bounds, budget, notes, alignment, missing slide-number
fields, predicted overflow and non-native shapes. The visual pass catches what it
cannot: real overflow, collisions, cramped labels and dead whitespace. Fix every
finding and re-run before calling a deck done.

Two traps that silently produce a broken package:

- Stripping slides means removing each entry from the slide id list **and** dropping its
  relationship, or the package keeps dangling parts.
- Copy a source file to a local temporary path before parsing it: files synced from
  cloud storage are often on-demand placeholders that fail to open until hydrated.

## 9. Extending the System

- **A new visual pattern is a new archetype function**, built only from the shared
  primitives, reading only from tokens, and registered in the archetype table. It must
  not import a colour or a coordinate.
- **A new size or proportion is a new token**, added to the token dataclass and to every
  theme file, never a literal at the call site.
- **A new theme is a token file plus a template**, and no Python at all.
- **Shared measurements belong to the row, not the shape.** Cards and panels laid out
  side by side share one measured height so a longer label in one box cannot push its
  neighbour's text out of line.
- **Table cell borders are written into `tcPr` in schema order**, and the built-in
  table style flags are disabled before explicit fills are applied, or PowerPoint's
  default style fights them.
- **Inject a live `slidenum` field**: `python-pptx` does not clone the master's
  slide-number placeholder, so a generated deck has no page numbers without it.

## 10. Validation Checklist

- [ ] The deck was built from a template file, never from a bare `Presentation()`.
- [ ] No hex value and no coordinate appears in Python; both come from theme tokens.
- [ ] No colour, size or coordinate appears in the spec.
- [ ] The same spec renders on a second theme with no edit.
- [ ] Every slide has one takeaway, rendered as the callout.
- [ ] Every slide has speaker notes over the minimum length.
- [ ] No slide exceeds the bullet budget or the words-per-bullet budget.
- [ ] No title wraps to a second line.
- [ ] Semantic entity colours are consistent from the first slide to the last.
- [ ] All text is the ink or muted colour, or white on a full-strength ground.
- [ ] Every shape is native; nothing is a picture of a diagram, chart or text.
- [ ] Inherited shadows are disabled on every shape and connector.
- [ ] A live slide-number field appears on every slide.
- [ ] Motivation slides precede mechanism slides.
- [ ] An agenda slide and per-section dividers exist, and the deck closes on one
      visual summary.
- [ ] No fabricated prices, benchmarks, percentages or committed dates appear.
- [ ] Every unknown carries a named owner and a written deliverable.
- [ ] The verification pass reports no findings, and the rendered slides were inspected.

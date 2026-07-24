---
description: 'Markdown formatting aligned to the CommonMark specification (0.31.2)'
applyTo: '**/*.md'
---

# CommonMark Markdown

Apply these rules per the [CommonMark spec 0.31.2](https://spec.commonmark.org/0.31.2/) when writing or reviewing `.md` files. CommonMark spec for reference only. Do not download CommonMark spec.

## Table of Contents

- [1. Non-Negotiable](#1-non-negotiable)
- [2. Preliminaries](#2-preliminaries)
- [3. Leaf Blocks](#3-leaf-blocks)
- [4. Container Blocks](#4-container-blocks)
- [5. Inlines](#5-inlines)
- [6. Validation Checklist](#6-validation-checklist)

## 1. Non-Negotiable

- **Hierarchical section numbering**: every heading below the document title (`##` and deeper) must carry a sequential dotted number that reflects its position in the hierarchy — `## 1. Section`, `### 1.1. Subsection`, `#### 1.1.1. Sub-subsection`, `### 1.2. Next Subsection`, `## 2. Next Section`, and so on. Numbers restart at `1` under each new parent (the first `###` under `## 3.` is `### 3.1.`, not `### 3.4.`), and no number may be skipped or repeated. When a section is added, removed, renamed, or reordered, renumber every affected sibling and descendant in the same change so the sequence stays gap-free and in document order.
- **Table of Contents**: a Table of Contents must appear at the top of the file (immediately after the introduction) and must list every numbered heading — top-level sections and all subsections — as nested bullets that mirror the heading hierarchy, with anchor links matching each heading's slug (for example, `[3.1. Leaf Blocks Overview](#31-leaf-blocks-overview)`). Update the TOC in the same change whenever a section is added, removed, renamed, or reordered.
- **Tables**: Format columns with aligned pipes and consistent cell padding so the raw Markdown stays well formatted and easy to edit by hand. Section numbering, the Table of Contents, and table alignment are all enforced in CI by [`check_markdown.py`](../scripts/check_markdown.py); after editing any file, run `python .github/shared/scripts/check_markdown.py --fix <file>` to renumber headings, rebuild the TOC, and align tables (the checker touches only heading lines, the TOC list, and table blocks — never other prose or `$…$` math).
- **Table row numbering**: every pipe table begins with a leading row-number column headed `#`, numbered sequentially from `1` down the table body (the separator row takes a `---` cell like every other column). It carries no data — it exists purely so individual rows can be cited unambiguously ("row 3 of the coverage table"). Never omit it, even on small or two-column tables; re-run `--fix` after adding the column so the numbers stay aligned.
- **Diagrams must be Mermaid**: any architecture, flow, sequence, state, or relationship diagram must be authored as a fenced ` ```mermaid ` code block — never an ASCII-art diagram, an embedded raster image (`.png`/`.jpg`), or an external diagramming tool. Mermaid renders natively on GitHub, stays diffable and reviewable in plain text, and lives next to the prose it documents. Prefer `flowchart`, `sequenceDiagram`, `stateDiagram-v2`, `erDiagram`, or `classDiagram`. Keep node labels short; put detail in the surrounding prose. Validate every diagram (it must parse) before committing.
- **Mermaid diagrams share one theme**: every Mermaid diagram in a document must read as one set — the same color palette, the same subgraph/container styling, and the same font — never ad-hoc per-diagram colors. Put a shared YAML `config` frontmatter block at the top of each ` ```mermaid ` fence (the `---` … `---` block before the diagram keyword) and reuse one role-based `classDef` palette so the same kind of node carries the same `fill`/`stroke` in every diagram. Keep it colorful but professional: muted container backgrounds, readable text contrast, accent fills for emphasis, and exploratory/optional nodes marked with `stroke-dasharray:6 4`. For PDF/print portability, set `flowchart.htmlLabels: false` and keep node labels plain — use `<br/>` for line breaks but avoid `<b>`/`<i>` inside labels, because HTML labels render as SVG `foreignObject`, which many PDF exporters (Puppeteer/headless-Chromium, Pandoc, wkhtmltopdf) drop or clip. Do not set a custom `fontFamily`: with `htmlLabels: false` a custom font makes the exporter mis-measure node widths and clip text — Mermaid's default font keeps measurement and rendering consistent. Recommended shared config and role palette:

  ```yaml
  config:
    flowchart:
      htmlLabels: false
    theme: base
    themeVariables:
      primaryColor: '#cfe2f3'
      primaryBorderColor: '#2f6fb3'
      primaryTextColor: '#0b2d4d'
      lineColor: '#5b6b7c'
      clusterBkg: '#f5f8fc'
      clusterBorder: '#bcccdc'
  ```

  Role-based `classDef` colors (`fill` / `stroke` / text) — same role, same colors across all diagrams:

  - Input / source: `#a2c4c9` / `#45818e` / `#06303a`
  - Process / data / IR: `#cfe2f3` / `#2f6fb3` / `#0b2d4d`
  - Generate / transform: `#f6b26b` / `#cc7a00` / `#3d2400`
  - Verify / test: `#ffe599` / `#bf9000` / `#3b2f00`
  - Govern / accent: `#d5a6e0` / `#8e44ad` / `#3a1745`
  - Output / result: `#b6d7a8` / `#538135` / `#1e3a12`
  - Human-in-the-loop: `#fff3cd` / `#d39e00` / `#663c00`
  - Neutral / container node: `#e8edf3` / `#9fb0c0` / `#27313a`
  - Containers: light `#f5f8fc` / `#bcccdc`; emphasis `#eef6ef` / `#6aa84f` (2px stroke).
- **Math formulas use the intuition → formula → breakdown layout**: every mathematical formula must be presented as exactly three parts, in this order:
  1. **One-line intuition** — a single blockquote line (`> …`) immediately above the formula that states in plain English what the formula buys you (for example, `> return per unit of risk`). No symbols, no second sentence.
  2. **Formula** — a display-math block delimited by `$$` on its own lines (inline `$…$` is only for referencing a symbol inside prose, never for the headline formula).
  3. **Variable breakdown** — a line reading `Where:` followed by a blank line and a bulleted list that defines *every* symbol that appears in the formula. Use `$…$` for each symbol, group the numerator and denominator (or other natural parts) under parent bullets, and nest any sub-formula (such as the expansion of a term) one level deeper.

  Define each symbol exactly once, keep symbols identical between the formula and the breakdown, and never leave a symbol undefined. Example:

  ```markdown
  > return per unit of risk

  $$
  \text{Sharpe Ratio} = \frac{R_p - R_f}{\sigma_p}
  $$

  Where:

  - $\text{Sharpe Ratio}$ = Sharpe Ratio of the portfolio
  - Numerator: extra return
    - $R_p$ = strategy return
    - $R_f$ = risk-free rate (often assumed to be 0 for short-term trading)
  - Denominator: risk (volatility of excess returns)
    - $\sigma_p$ = standard deviation of the portfolio's excess return
  ```

## 2. Preliminaries

- A line ends at a newline (`U+000A`), carriage return (`U+000D`), or end of file. A blank line contains only spaces or tabs.
- Tabs behave as 4-space tab stops for block structure but are not expanded in content.
- Replace `U+0000` with the replacement character `U+FFFD`.
- **Backslash escapes**: `\` before any ASCII punctuation character renders the literal character. Not recognized in code spans, code blocks, or autolinks.
- **Entity and numeric character references**: `&amp;`, `&#123;`, `&#x7B;` — valid HTML5 entities only. Not recognized in code spans or code blocks. Cannot replace structural characters.

## 3. Leaf Blocks

- **Thematic breaks**: 3+ matching `-`, `_`, or `*` characters on a line with 0–3 spaces indent. Only spaces or tabs allowed on the line otherwise. Can interrupt a paragraph.
- **ATX headings**: 1–6 `#` characters followed by a space or end of line. Optional closing `#` sequence (preceded by a space). 0–3 spaces indent allowed.
- **Setext headings**: Text underlined with `=` (level 1) or `-` (level 2). Cannot interrupt a paragraph — blank line required after a preceding paragraph.
- **Indented code blocks**: Lines indented 4+ spaces. Cannot interrupt a paragraph. Content is literal text, not parsed as Markdown.
- **Fenced code blocks**: Open with 3+ backticks or tildes (do not mix). Closing fence must use same character with at least the same count. Info string after backtick fence cannot contain backticks. Specify language identifier after the opening fence. Content is literal text.
- **HTML blocks**: Seven types defined by start/end tag conditions. Types 1–5 end at their matching end pattern. Type 6 ends at a blank line. Type 7 cannot interrupt a paragraph and ends at a blank line.
- **Link reference definitions**: `[label]: destination "title"`. Case-insensitive label matching (Unicode case fold). First definition wins for duplicate labels. Cannot interrupt a paragraph.
- **Paragraphs**: Consecutive non-blank lines not interpretable as other block constructs. Leading spaces up to 3 are stripped.
- **Blank lines**: Ignored between blocks; determine whether a list is tight or loose.

## 4. Container Blocks

- **Block quotes**: Lines prefixed with `>` (optionally followed by a space). Lazy continuation allowed for paragraph text only. A blank line separates consecutive block quotes.
- **List items**: Bullet markers (`-`, `+`, `*`) or ordered markers (1–9 digits + `.` or `)`). Content column determined by marker width + spaces to first non-whitespace (1–4 spaces after marker). Sublists must be indented to the content column. An ordered list interrupting a paragraph must start with `1`.
- **Lists**: Sequence of same-type list items. Changing bullet character or ordered delimiter starts a new list. A list is loose if any item is separated by a blank line.

## 5. Inlines

- **Code spans**: Backtick-delimited inline code. Line endings convert to spaces. Leading and trailing space stripped when both present (unless content is all spaces). Backslash escapes are literal inside code spans.
- **Emphasis and strong emphasis**: `*`/`_` for `<em>`, `**`/`__` for `<strong>`. `_` is not allowed for intraword emphasis. Left-flanking / right-flanking delimiter run rules apply. Delimiter run length sum must not be a multiple of 3 when one delimiter can both open and close (unless both lengths are multiples of 3).
- **Links**: Inline `[text](url "title")` or reference `[text][label]` / `[text][]` / `[text]`. Link text may contain inlines but not other links. Destination in `<…>` allows spaces; without angle brackets, balanced parentheses allowed. No whitespace between link text and `(` or `[`.
- **Images**: `![alt](src "title")` — same syntax as links prefixed with `!`. Alt text is the plain-string content of the description.
- **Autolinks**: `<URI>` or `<email>` in angle brackets. Scheme must be 2–32 characters starting with an ASCII letter. Bare URLs are not auto-linked in CommonMark (requires angle brackets).
- **Raw HTML**: Open/close tags, comments (`<!--` … `-->`), processing instructions (`<?` … `?>`), declarations (`<!` … `>`), CDATA (`<![CDATA[` … `]]>`) are passed through as literal HTML.
- **Hard line breaks**: Two+ trailing spaces or `\` before a line ending. Not recognized in code spans or HTML tags. Does not work at end of a block.
- **Soft line breaks**: A line ending not preceded by two+ spaces or `\`. Rendered as a space in browsers.

## 6. Validation Checklist

- [ ] Every `##`/`###`/`####` heading is prefixed with a dotted sequential number (`1.`, `1.1.`, `1.1.1.`) that is gap-free and in document order, with numbering restarting at `1` under each new parent.
- [ ] A Table of Contents sits at the top of the file and lists every numbered heading (sections and subsections) as nested bullets with correct anchor links.
- [ ] ATX headings use 1–6 `#` followed by a space.
- [ ] Fenced code blocks specify a language identifier and use matching fence characters and counts.
- [ ] Backtick fence info strings do not contain backtick characters.
- [ ] Indented code blocks are preceded by a blank line (they cannot interrupt a paragraph).
- [ ] Emphasis uses `*` for intraword; `_` only at word boundaries.
- [ ] Links use `[text](url)` or reference syntax with no whitespace before `(` or `[`.
- [ ] Images include non-empty alt text.
- [ ] Autolinks use angle brackets (`<URL>`); bare URLs are not CommonMark autolinks.
- [ ] No unbalanced parentheses in bare link destinations (use `<…>` or escape).
- [ ] HTML block type 7 (custom/inline-level tags) is preceded by a blank line when following a paragraph.
- [ ] Diagrams use a ` ```mermaid ` fenced block (not ASCII art or an image) and parse without error.
- [ ] Every Mermaid diagram in the document shares one theme: a `config` frontmatter block, a single role-based color palette, consistent container styling, and the same font.
- [ ] Flowchart labels are PDF-safe: `flowchart.htmlLabels: false` is set, node labels use `<br/>` only (no `<b>`/`<i>`), and no custom `fontFamily` is set — so PDF exporters neither drop nor clip text.
- [ ] Every pipe table has a leading `#` row-number column, numbered sequentially from 1.
- [ ] Every math formula has all three parts in order: a one-line `> ` intuition blockquote, a `$$` display block, and a `Where:` variable breakdown that defines every symbol exactly once.

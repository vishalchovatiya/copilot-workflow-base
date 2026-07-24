---
name: learning-dashboard
description: "Generate an interactive HTML+CSS knowledge dashboard from course material, transcripts, or any learning topic. Use when user wants to learn, study, summarize a course, create flashcards, build a knowledge graph, or produce study material. Trigger phrases: 'help me learn', 'create a dashboard for', 'summarize this course', 'make flashcards', 'study guide for', 'knowledge graph of'. Also trigger when user pastes lecture notes, transcripts, or topic names and asks for structured learning output. Output is always a single self-contained HTML file."
---

# Learning Dashboard Generator

Turn any learning material -- course transcripts, lecture notes, topic names, or documentation -- into a single interactive **HTML + CSS knowledge dashboard** with 7 tabs covering every cognitive format. No frameworks, no JS libraries -- pure HTML + CSS + vanilla JS.

## Two Hard Rules

These override everything else.

### Rule 1 -- Organize by domain, never by lecture order.

Group concepts by what they are, not when they were taught. Surface cross-topic connections. If you catch yourself mirroring a syllabus structure, reorganize.

### Rule 2 -- Philosophy before mechanics. Always.

Before explaining *how* something works, answer: *Why does it exist? What problem does it solve? What tradeoffs define it?* Every concept node starts with its reason for being.

## Workflow

1. **Ingest.** Read every piece of material the user provides (transcripts, notes, docs). Extract signal, discard filler. Use available tools to gather additional workspace context if relevant.
2. **Clarify if needed.** If the scope is unclear (e.g. "help me learn networking"), ask one targeted question about depth or focus area. Don't interrogate.
3. **Dissect.** Recursively decompose the material into depth levels:

   | Level | Name         | Purpose                                      |
   | ----- | ------------ | -------------------------------------------- |
   | L0    | Bird's eye   | What is it? Why does it exist? One sentence. |
   | L1    | Pillars      | 3–5 core sub-concepts that compose it.       |
   | L2    | Mechanics    | How each pillar works internally.            |
   | L3    | Edge cases   | Where it breaks, tradeoffs, gotchas.         |
   | L4+   | Rabbit holes | Deep-dives added on demand.                  |

   Start at L0–L4. Expand only when material warrants it. Tag unfinished branches with `🔲 TODO`.

4. **Structure.** Organize by domain/concept, surface cross-section connections, encode in multiple cognitive formats simultaneously.
5. **Build.** Produce the dashboard as a single self-contained HTML file following the template below.
6. **Host.** Create and host on <https://codepen.io/pen/>.

## Dashboard Template (7 Tabs)

Every dashboard contains exactly these tabs:

| Tab              | Content                                                                                                          |
| ---------------- | ---------------------------------------------------------------------------------------------------------------- |
| **Dissect**      | Recursive decomposition tree (L0→Ln) — collapsible levels, philosophy + mechanics at each node.                  |
| **Infographics** | Visual cards per concept — concise sentences, tables, pills, flow diagrams, icons.                               |
| **CheatSheet**   | Dense reference tables — specs, IDs, structures, abbreviations.                                                  |
| **Flashcards**   | Click-to-flip cards for every key term — question front, answer back. Scale quantity with material depth.         |
| **MindMap**      | Domain-based branches (not lecture order), colour-coded by category.                                             |
| **Quiz**         | ≥30+ MCQs (≥3 per key concept) — randomised order on every open; live auto-score; explanation after each answer. Shuffle & Restart button. |
| **Compare**      | Multi-column comparison tables; dropdown to switch topics; 🟢=better, 🔴=worse, ⚪=context-dependent.              |

### Bonus features

1. A **global search box** (top-right of tab bar, `Ctrl+Shift+F`) that indexes every tab; clicking a result switches to that tab, auto-expands collapsed sections / flips flashcards, then scrolls and flashes the match.
2. Print button — purple circle, bottom-right → PDF export.

## Core Principles

1. **Recursive dissection** -- split into layers until irreducible. Each level doubles resolution.
2. **80/20 extraction** -- extract core signal, discard noise. One dense visual card beats three paragraphs.
3. **Multi-format encoding** -- same knowledge in tree, cards, quiz, map simultaneously. Different retrieval paths strengthen memory.
4. **Scalable depth** -- new layers slot in without restructuring. Cross-link related branches across topics.
5. **Maximum reasoning** -- think before answering. Verify accuracy before committing to any tab.

## Visual Rules

1. Dark GitHub-style theme — background `#0d1117`, light text.
2. **Diagrams must be pure HTML + CSS — never Mermaid, never external JS libs.** Mermaid frequently fails to render (Obsidian preview, CSP, offline, version mismatches). Build flows as flex rows of color-coded boxes with `→` / `↓` arrows; build layer stacks as stacked colored bands; build mind maps as a CSS grid of color-coded branches with nested `<ul>`s.
4. Emojis for visual cues: ✅ correct, ❌ wrong, 🟢 better, 🔴 worse.
5. All content visible at once — no prev/next pagination.
6. No horizontal scrolling — tables must wrap or stack vertically.
7. Display layers or stack with color-coding.
8. Use numbered list(or nested numbered list, if needed) instead of bullet points.

## Output Format

Always exactly: a single fenced code block containing the complete HTML file. No preamble. No trailing explanation. If the user asks "what did you cover?" after receiving the dashboard, explain in a follow-up.

## Anti-patterns

1. **No text walls** — if a table or visual card would suffice, use it.
2. **No lecture-order sequencing** — always reorganize by domain/concept.
3. **No pagination** — display all content at once within each tab.
4. **No placeholder content** — every card, flashcard, and quiz question must contain real material from the source.
5. **No Mermaid / no external diagram libraries** — they break silently. All diagrams must be self-contained HTML+CSS.

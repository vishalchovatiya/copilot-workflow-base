---
applyTo: "**/README.md"
description: "Use when creating, updating, or reviewing README.md files. Covers structure, formatting, and content expectations for project documentation."
---

# README Guidelines

## Structure

Follow this section order (include only what's relevant):

1. **Table of Content** — optional for short READMEs, recommended for longer ones. Numbered headings with anchor links.
2. **Typical Sections**:
    1. **Overview** — 2–4 sentences: what it does, who it's for, key differentiator.
    2. **Repo Structure** — file/folder hierarchy with aligned inline descriptions. Use code blocks:
    ```
    RepoName/
    ├── model/
    │   ├── inc/                     # Public headers (API)
    │   ├── src/                     # Implementation files
    │   └── CMakeLists.txt           # Model-specific build
    ├── platform.json                # Runtime configuration
    ├── Submodule1/                  # External dependency (git submodule)
    ├── ...                          # Other files/folders
    ├── CMakeLists.txt               # Top-level build
    └── README.md                    # This file
    ```
    3. **Quick Start** — minimal steps to get running (install → configure → run).
    4. **Usage** — subsections for cloning, environment setup, prerequisites, build, run, test, debug, troubleshooting. Adjust order as needed.

## Formatting

- Headings start at H2 (`##`); be descriptive.
- Code blocks with language tag: ` ```bash `, ` ```cpp `, etc.
- Use `<!-- comments -->` for maintainer notes, not visible content.
- Relative links for internal docs (`[guide](docs/guide.md)`).
- One blank line between sections; no trailing whitespace.

## Principles

- **Concise**: every sentence earns its place; no filler.
- **Scannable**: headings, bullet lists, code blocks; no walls of text.
- **Copy-pasteable**: commands should work as-is.
- **Current**: document what exists now, not aspirational features.

## Anti-patterns

- Don't repeat what code already says (API docs belong in docstrings/headers).
- Don't include install steps for standard tooling (e.g., "install Git").
- Don't use screenshots as the only documentation — pair with text.
- Don't leave template placeholders (`TODO`, `Lorem ipsum`).
- One blank line between sections; no trailing whitespace.
- For all H2 heading ends use --- (three dashes) to visually separate sections and improve readability.
- Use well aligned tables for structured data, with headers and consistent formatting.
- Keep documentation DRY (link instead of duplicating)

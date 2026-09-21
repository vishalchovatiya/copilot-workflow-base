---
applyTo: "**"
description: "Use on every coding task. Behavioral guardrails that reduce common LLM coding mistakes: surface assumptions before implementing, keep the solution minimal, keep the diff surgical, and drive the work from verifiable success criteria."
---

# Engineering Discipline

Behavioral baseline for *how* a change is made, adapted from
[Andrej Karpathy's LLM coding guidelines](https://github.com/multica-ai/andrej-karpathy-skills/blob/main/CLAUDE.md).
The other `*.instructions.md` files in this bundle say *what* the code must look like; this
one says how to arrive at it.

These rules trade speed for caution. On a trivial, unambiguous task — a typo, a one-line
config change — use judgement and just do it.

## Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

- **State assumptions explicitly** before implementing; if an assumption is load-bearing and
  uncertain, ask instead of guessing.
- **Present competing interpretations**: when a request can be read more than one way, name
  the readings and let the user choose — never pick one silently.
- **Push back when a simpler approach exists**, even if the user asked for the complex one.
- **Stop when something is unclear**: name exactly what is confusing rather than producing
  plausible-looking code around the gap.

## Simplicity First

**The minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No flexibility, configurability, or extension points nobody requested.
- No error handling for states that cannot occur — validate at system boundaries only.
- If the result is 200 lines and could be 50, rewrite it.

The test: would a senior reviewer call this overcomplicated? If yes, simplify.

## Surgical Changes

**Touch only what you must. Clean up only your own mess.**

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor what isn't broken.
- Match the surrounding style even where you'd write it differently.
- Report unrelated dead code — don't delete it.
- Do remove the imports, variables, and helpers that *your* change orphaned.

The test: every changed line traces directly back to the request. The one standing exception
is the sync rule in [context-engineering.instructions.md](context-engineering.instructions.md)
— updating the `README.md` and `.github/` artifacts that a change invalidates is part of the
request, not scope creep.

## Goal-Driven Execution

**Define success criteria first, then loop until verified.**

- Restate a vague task as a verifiable goal before starting:
  - "add validation" -> "write tests for the invalid inputs, then make them pass"
  - "fix the bug" -> "write a test that reproduces it, then make it pass"
  - "refactor X" -> "tests pass unchanged before and after"
- For multi-step work, state a short plan in which every step carries its own check:

  ```text
  1. <step> -> verify: <check>
  2. <step> -> verify: <check>
  ```

- Run the verification yourself — build, test, or lint — and report the result. Strong
  criteria let you iterate independently; "make it work" forces the user to referee every
  step.

## Signals This Is Working

- Diffs contain fewer changes unrelated to the request.
- Fewer rewrites caused by overcomplication.
- Clarifying questions arrive before implementation rather than after a wrong turn.

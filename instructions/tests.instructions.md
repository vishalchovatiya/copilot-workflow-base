---
applyTo: "tests/**"
---

# Testing Rules

Baseline testing conventions that apply to any project. Domain-specific rules
(coverage targets per module, regression baselines, differential oracles) belong in the
consuming repository's own `tests.instructions.md`.

## Test Structure

- Separate tests into tiers by cost and I/O:
  - **unit** — pure logic, no network or disk, external services mocked; must stay fast.
  - **integration** — exercises real config and adapters; may touch cached external data.
  - **stateful / end-to-end** — long-running or persistence scenarios; use temp dirs, never
    shared machine state.
- Keep each tier in its own folder so a contributor can run the fast tier in a tight loop.

## Naming Convention

Name tests so the intent is readable without opening the body:

```
test_<unit-under-test>_<scenario>_<expected_outcome>
```

The three parts answer *what*, *under which condition*, and *what should happen*. Prefer a
long explicit name over a short cryptic one.

## Coverage Philosophy

- Set the coverage bar by **risk**, not by a uniform repo-wide percentage.
- Code that is pure and consequential (money math, security checks, state reconciliation)
  should approach full branch coverage; glue and I/O code can be lighter.
- Track coverage targets as an explicit, reviewed list in the consuming repo — do not let
  the number drift silently.

## Regression Tests

- Pin the observable output of expensive or non-obvious computations (numeric results,
  serialized snapshots) in a committed regression test.
- When a change moves a pinned value, the test **must fail** — treat it as a prompt to
  re-validate the change intentionally, never as noise to silence.

## Differential Tests

- When you hand-roll an algorithm that a mainstream library also implements, add a
  **tolerance-based differential test** that cross-checks your implementation against the
  reference library on a shared, deterministic input.
- Guard the reference import (e.g. `pytest.importorskip(...)`) so the suite skips cleanly
  when the dev-only dependency is absent.
- Choose the tolerance deliberately: **exact** for integer/exact primitives, and a small
  **steady-state** tolerance for smoothed/iterative results where seeding conventions
  differ. The test exists to catch your formula bugs, not to inherit the reference
  library's floating-point rounding.

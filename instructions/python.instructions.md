---
applyTo: "**/*.py,**/pyproject.toml,**/requirements*.txt,**/setup.cfg,**/setup.py,**/.env.example"
description: "Use when writing, reviewing, or refactoring Python code."
---


## Coding Principles [MUST]

1. ***Pythonic***: prefer idiomatic Python over patterns ported from other languages; leverage the data model.
2. ***Expressive***: self-explanatory code; intent clear without extra comments.
3. ***Concise***: simplest solution; fewer lines, but not at cost of expressiveness.
4. ***Extensible/Scalable***: new features via new components, not widespread edits.


## Environment Management

- **Always** use `venv` or `conda` isolated environments; never install into system Python.
- Prefer `pyproject.toml` as the single source of project metadata and tool config; avoid `setup.py` for new projects.
- Pin direct runtime dependencies with version ranges in `pyproject.toml`; lock with `pip-compile` or `uv lock`.
- Separate dev dependencies: `[project.optional-dependencies]` dev group or `requirements-dev.txt`.
- Store secrets and environment-specific values in `.env` files (loaded via `python-dotenv`); provide `.env.example` with dummy values — never commit `.env`.


## Project File Structure

```
project/
├── src/
│   └── mypackage/
│       ├── __init__.py       # Public API declarations only — keep thin
│       ├── core.py
│       └── utils.py
├── tests/
│   ├── conftest.py
│   └── test_core.py
├── docs/
├── .env.example              # Template; never commit .env
├── pyproject.toml            # Single source of metadata + tool config
└── requirements-dev.txt      # Dev/test/lint deps (pinned)
```

- Keep `__init__.py` files thin — they are public API declarations, not implementation.
- Mirror `src/` structure inside `tests/`; one test file per source module.


## Coding Style

### General

1. Constants: `ALL_CAPS` at module level, e.g. `MAX_RETRIES`, `DEFAULT_TIMEOUT`.
2. Test naming: `test_<module>_<behavior>` e.g. `test_parser_handles_empty_input`.
3. Files: `lower_snake_case`, e.g. `data_loader.py`, `signal_utils.py`.
4. Indent: 4 spaces, no tabs (PEP 8).
5. Max line length: 88 characters (Black default); wrap at logical boundaries.
6. Avoid deep nesting; use early returns, guard clauses, or extract helpers.
7. One blank line between methods; two blank lines between top-level definitions.

### Python Naming

- Descriptive names, not abbreviations (`compute_checksum` not `cmp_chk`); exception: loop vars like `i`, `idx`, `k`.
- Types/classes: `PascalCase` (`class DataParser`, `class RetryPolicy`).
- Functions/methods/variables: `snake_case` (`retry_count`, `parse_frame()`).
- Constants: `ALL_CAPS` (`MAX_BUFFER_SIZE`, `DEFAULT_PORT`).
- Private: prefix `_single_underscore`; name-mangled dunder `__double` only when strictly needed.
- Dunder methods: `__init__`, `__repr__`, `__enter__` — never invent custom ones.
- Files: `foo_bar.py`; packages: `lower_no_underscores/` when possible.

### Comments and Docstrings

- Explain *why*, not *what*; skip obvious code.
- Use `#` inline; block comments for file/section headers.
- All public modules, classes, and functions: Google-style docstrings.
- Document ownership, thread-safety, non-trivial APIs, and known limitations.
- `# TODO(name): actionable description` — never vague `# TODO: fix this`.

```python
def parse_frame(data: bytes, offset: int = 0) -> Frame:
    """Parse a single CAN frame from a raw byte buffer.

    Args:
        data: Raw byte buffer containing one or more frames.
        offset: Byte offset at which to begin parsing.

    Returns:
        Parsed Frame with id, dlc, and payload fields populated.

    Raises:
        FrameParseError: If the buffer is shorter than the minimum frame size.
    """
```

### Imports

- Standard order: stdlib → third-party → local (blank line between groups).
- Never `from module import *`; import what you use directly.
- Prefer `import module` over `from module import name` for large namespaces.
- No circular imports; restructure to break cycles via a shared `interfaces.py`.
- Use `__all__` in library modules to define the public API.

```python
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from myproject.core import Frame
from myproject.utils import compute_checksum
```


## Language Features

### Type Annotations

- Annotate all public function signatures (args + return type). No bare `-> None` exceptions.
- Use built-in generics (`list[str]`, `dict[str, int]`, `tuple[int, ...]`) — no `typing.List` post-3.9.
- Use `X | Y` union syntax (Python 3.10+); for 3.9 use `Union[X, Y]` or `from __future__ import annotations`.
- Prefer `Sequence`, `Mapping`, `Iterable` (from `collections.abc`) for input params; concrete types for return values.
- Use `TypeAlias` for complex reusable types; `TypeVar` for generics.
- Avoid `Any`; use `object` when a function accepts any value. Reserve `Any` for truly untyped boundaries.
- Add `py.typed` marker file to typed packages.

```python
from collections.abc import Iterable, Sequence
from typing import TypeAlias

SignalMatrix: TypeAlias = list[list[float]]

def normalize(signals: Sequence[float], *, scale: float = 1.0) -> list[float]:
    return [s / scale for s in signals]
```

### Error Handling

- Catch specific exceptions, never bare `except:` or `except Exception:` unless re-raising.
- Create domain-specific exception hierarchies (`class AppError(Exception)` → `class ParseError(AppError)`).
- Use `raise ... from err` to preserve exception chains.
- Never swallow errors silently; log before ignoring.
- Prefer EAFP (try/except) over LBYL (check-then-act) for Python-idiomatic flow.
- For async code: always capture task handles; never fire-and-forget without an error callback.

```python
class PipelineError(Exception):
    """Base for all pipeline-layer errors."""

class FrameParseError(PipelineError):
    """Raised when a byte buffer cannot be decoded as a valid frame."""

try:
    frame = parse_frame(raw)
except FrameParseError as err:
    logger.error("Bad frame at offset %d: %s", offset, err)
    raise
```

### Data Classes and Structs

- `@dataclass` for plain data containers; `@dataclass(frozen=True)` for value objects.
- `dataclass` over raw dicts for anything with more than 2 fields that crosses function boundaries.
- `NamedTuple` when immutability + tuple unpacking semantics are needed.
- `TypedDict` only for typed dict-shaped data (e.g. JSON schemas, config blobs).
- Avoid `__post_init__` for heavy logic; use a `@classmethod` factory instead.

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class CanFrame:
    frame_id: int
    dlc: int
    payload: bytes = field(default=b"")
```

### Functions and Lambdas

- Short, single-responsibility; aim for ≤ 30 lines. Exception: FSMs, performance-critical code.
- Return values over output params; prefer a `Result` dataclass over tuples of 3+.
- Use keyword-only args (`*`) to prevent positional misuse for 3+ argument functions.
- Avoid mutable default arguments (`def f(items=[])` is a bug); use `None` + guard.
- `lambda` only for trivial, single-expression callables (e.g. sort keys). Name complex ones.
- Prefer list/dict/set comprehensions over `map`/`filter`; use generator expressions for lazy evaluation.

```python
# Bad: mutable default, positional-only misuse
def retry(fn, attempts=3, delay=[]):
    ...

# Good: keyword-only, immutable default
def retry(fn: Callable, *, attempts: int = 3, delay_s: float = 0.5) -> Any:
    ...
```

### Classes

- Simple constructors; move failable or async work to `create()` / `from_*()` class methods.
- `__repr__` always; `__str__` only if human-readable output differs from repr.
- Prefer `@property` over getter methods; prefer direct attribute access over trivial properties.
- `Protocol` (structural subtyping) over ABC for interfaces that third parties implement.
- `ABC` only for framework base classes with shared default implementations.
- Composition over inheritance; use mixins sparingly and document their assumptions.
- `__slots__` on hot-path or memory-critical objects.
- Operator overloads only for obvious semantics (math types, comparison).
- `@classmethod` for alternate constructors; `@staticmethod` only when the logic is purely utility and has no reason to be at module level.

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Encoder(Protocol):
    def encode(self, data: bytes) -> bytes: ...
    def decode(self, data: bytes) -> bytes: ...
```

### Generators and Iterators

- Prefer generators over building full lists when the consumer doesn't need random access.
- Use `yield from` to delegate sub-iterators cleanly.
- Implement `__iter__` + `__next__` only when generator syntax is insufficient (stateful iteration).

### Context Managers

- Use `contextlib.contextmanager` for simple resource management.
- Implement `__enter__` / `__exit__` on classes that own resources (files, sockets, locks).
- `contextlib.suppress`, `contextlib.nullcontext`, and `contextlib.ExitStack` for composition.

### Async / Concurrency

- Prefer `asyncio` for I/O-bound concurrency; use `concurrent.futures.ThreadPoolExecutor` / `ProcessPoolExecutor` for CPU-bound.
- Never call blocking I/O inside a coroutine directly; use `loop.run_in_executor()`.
- Always capture task handles from `asyncio.create_task()`; attach an error callback.
- Use `asyncio.TaskGroup` (3.11+) for structured concurrency over raw `gather`.
- Protect shared mutable state with `asyncio.Lock`; prefer message-passing over shared state.
- Use `contextvars.ContextVar` for request-scoped context in async services.

```python
async def fetch_all(urls: list[str]) -> list[bytes]:
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(fetch(url)) for url in urls]
    return [t.result() for t in tasks]
```


## Performance and Profiling

- Profile **before** optimizing: use `cProfile`, `line_profiler`, or `timeit`; never guess at bottlenecks.
- Prefer built-in data structures over custom implementations: `heapq` for priority queues, `deque` for O(1) pop-left, `bisect` for sorted insertion.
- Use generators and `itertools` for large sequences — avoid materializing full lists in memory.
- Avoid repeated attribute lookups inside hot loops; cache to a local variable (`fn = obj.method`).
- `functools.cache` / `lru_cache` for pure, deterministic memoization.
- Minimize third-party imports on the hot path: every import is startup cost and an attack surface.

```python
import cProfile
import pstats

with cProfile.Profile() as pr:
    run_pipeline(data)

stats = pstats.Stats(pr).sort_stats("cumulative")
stats.print_stats(20)
```


## Design Principles

### DRY, KISS, YAGNI

- DRY: one source of truth; share knowledge (tables/config), not just helpers.
- KISS: simplest design that works now; add complexity only for proven constraints.
- YAGNI: no speculative abstractions; one concrete implementation before generic extension points.

### Functional Style

- Pure domain logic: state in, state out, no hidden mutation; I/O at edges.
- Pipelines: `parse → normalize → validate → emit`.
- Prefer `functools.reduce`, `itertools`, `operator` over hand-rolled loops for standard transforms.
- Use `functools.cache` / `functools.lru_cache` for pure, deterministic memoization.

### OO Design

- Classes for ownership and lifecycle; module-level functions for stateless helpers.
- Composition over inheritance; stable base interfaces only for long-lived contracts.
- `struct`-style: `@dataclass` for passive data; `class` for behavior + invariants.

### SOLID

- **SRP**: one reason to change per module.
- **OCP**: extend via composition/`Protocol`, not editing stable code.
- **LSP**: subtypes honor base contracts; diverge → new interface.
- **ISP**: small focused `Protocol`s; no god interfaces.
- **DIP**: depend on abstractions; inject concretes via constructors or factory functions.


## Logging

- In **chandoo**, never use `print()` or the bare `logging` module directly. Always log through `structlog` via the helpers in `chandoo.utils.logging`: `get_impl_logger(__name__)` for infra/adapter/debug traces, `get_trade_logger(__name__)` for signals, order lifecycle, fills, P&L, and risk actions, and `get_auth_logger(__name__)` for Kite login / daily token refresh.
- The `impl`, `trade`, and `auth` streams are independent and must never cross-write.
- **Logs are the system's black box.** Production runs overnight (IST) and is reviewed from logs the next morning, so every decision must be reconstructable from the trade stream alone: log the *input*, the *output*, and the *reason* at each step (signal → per-guardrail risk trace → order lifecycle → fill → closed-trade P&L). Prefer one structured event per decision over a terse summary. `configure_logging(env, log_dir=...)` persists each stream durably to `<log_dir>/{impl,trade,auth}.log`; `run_live` writes a dated folder under `logs/sessions/<IST-date>/`.
- Bind structured context as key-value pairs (`log.info("order_filled", symbol=sym, qty_paise=qty)`) instead of interpolating into the message string.
- **Never lose the money**: monetary fields in logs stay integer **paise** — never `float`, never a pre-divided rupee value.
- Structured logging (JSON) for production services; use `structlog` or `python-json-logger`.
- Log levels: `DEBUG` for trace-level dev info; `INFO` for lifecycle events; `WARNING` for recoverable anomalies; `ERROR` for failures requiring attention; `CRITICAL` for unrecoverable states.
- Never log secrets, PII, tokens, or raw payloads at INFO+.

```python
import logging
logger = logging.getLogger(__name__)

def process(frame: CanFrame) -> Result:
    logger.debug("Processing frame id=0x%X dlc=%d", frame.frame_id, frame.dlc)
    ...
```


## Security

- API keys, tokens, and credentials go in environment variables — **never** in source code or committed config files.
- Sanitize all external input before use; validate types, ranges, and formats explicitly before processing.
- Use the `secrets` module (not `random`) for cryptographic tokens, session IDs, and nonces.
- Parameterize all database queries; never format SQL strings with user-supplied input.
- Audit third-party dependencies before adding: check last commit date, open CVEs (`pip-audit`), license compatibility, and maintenance status.
- Rotate secrets via environment; use `.env.example` to document required vars without values.


## Testing Principles

- Test one behavior per test case; avoid multiple unrelated assertions in a single test.
- Use descriptive test names: `test_<unit>_<condition>_<expected_outcome>`.
- Add a module-level docstring or comment block per test file describing scope and assumptions.
- Fixtures in `conftest.py`; keep test files thin (arrange → act → assert).
- Mock at system boundaries (I/O, time, network); never mock the unit under test itself.
- Parametrize over duplicated test bodies: `@pytest.mark.parametrize`.
- Prefer real objects over mocks wherever construction is cheap.
- Target meaningful coverage, not vanity %: branch coverage > line coverage.

```python
@pytest.mark.parametrize("dlc,expected_len", [(0, 0), (4, 4), (8, 8)])
def test_can_frame_payload_length_matches_dlc(dlc: int, expected_len: int) -> None:
    frame = CanFrame(frame_id=0x100, dlc=dlc, payload=bytes(dlc))
    assert len(frame.payload) == expected_len
```


## Architectural Principles

- OO for boundaries/lifecycle; FP for data transforms. Classes own resources; pure functions transform data.
- New features = new components, not widespread edits. Decoupled modules, clear interfaces.
- Keep `__init__.py` files thin — they are public API declarations, not implementation.
- Separate concerns: I/O, domain logic, and serialization in distinct layers.
- Configuration via environment variables or config files, never hardcoded; use `pydantic.BaseSettings` or `dataclasses` + `os.environ`.


## Design Patterns

- **Strategy**: pluggable algorithms via `Protocol`.
- **Factory/Builder**: complex invariant-heavy construction (`@classmethod` or dedicated factory module).
- **Adapter**: external system boundaries (wrap third-party types).
- **Pipeline/Chain**: staged transforms (generator chains or explicit step functions).
- **State/Tables**: explicit FSMs via `enum` + `dict` dispatch, not sprawling `if/elif`.
- **Observer**: `asyncio.Queue` or callback registration — not raw global event lists.
- **Decorator**: cross-cutting concerns (logging, retry, timing) via `functools.wraps`-preserving wrappers.

```python
import enum
from typing import Callable

class State(enum.Enum):
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"

# Table-driven FSM transition: State → {Event → (handler, next_state)}
Transitions: dict[State, dict[str, tuple[Callable, State]]] = {
    State.IDLE: {
        "start": (on_start, State.RUNNING),
    },
    State.RUNNING: {
        "stop": (on_stop, State.IDLE),
        "error": (on_error, State.ERROR),
    },
}
```


## Tooling [MUST]

| Tool               | Purpose                                             |
| ------------------ | --------------------------------------------------- |
| `black`            | Auto-formatter (line length 88)                     |
| `ruff`             | Fast linter + import sorter (replaces flake8/isort) |
| `mypy` / `pyright` | Static type checker                                 |
| `pytest`           | Test runner with rich fixture model                 |
| `pytest-cov`       | Coverage reporting                                  |
| `pip-audit`        | Dependency CVE scanning                             |
| `pre-commit`       | Enforce formatting/lint before every commit         |

- Run `black`, `ruff`, `mypy`, and `pytest` in CI; block merges on failures.
- One-liner quality gate:

```bash
black . && ruff check . && mypy src/ && pytest --tb=short -q
```

- `pyproject.toml` is the single source of project metadata and tool config.
- Pin direct dependencies with version ranges in `pyproject.toml`; lock with `pip-compile` or `uv lock`.
- One virtual environment per project; never install into system Python.


## Response Format

- Start with the semantic or correctness issue.
- Provide the smallest correct change first.
- Mention type safety, error handling, performance, or security implications when relevant.
- If a cleaner alternative exists, present it after the minimal fix.
- Ask before generating test scripts or exporting `requirements.txt` — don't assume scope.


## References [NOT FOR AI USE]

1. [PEP 8 – Style Guide for Python Code](https://peps.python.org/pep-0008/)
2. [PEP 484 – Type Hints](https://peps.python.org/pep-0484/)
3. [PEP 257 – Docstring Conventions](https://peps.python.org/pep-0257/)
4. [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
5. [The Hitchhiker's Guide to Python](https://docs.python-guide.org/)
6. [Python Typing Best Practices](https://typing.python.org/en/latest/reference/best_practices.html)

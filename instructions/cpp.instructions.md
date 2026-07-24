---
applyTo: "**/*.{c,cc,cpp,h,hpp}"
description: "Use when writing, reviewing, or refactoring code."
---


## Coding Principles [MUST]

1. ***Expressive***: self-explanatory code; intent clear without extra comments.
2. ***Concise***: simplest solution; fewer lines, but not at cost of expressiveness.
3. ***Extensible/Scalable***: new features via new components, not widespread edits.

## Coding Style

### General

1. Constants: UPPER_CASE (includes macros, enum values), e.g. MAX_BUFFER_SIZE.
2. Test naming: `TC_<module>_<date>_<behavior>` e.g. `TC_SPI_20240427_fault_handling`.
3. Files: lower_snake_case, e.g. model.cc, utils.c.
4. Indent: 2 spaces, no tabs.
5. Opening brace on same line: `if (x) {`, `void Func() {`.
6. Avoid deep nesting; use early returns, guard clauses, or extract helpers.

### C/C++

#### Naming

- Descriptive names, not abbreviations (`ComputeChecksum` not `CmpChk`); exception: loop vars like `idx`.
- Types: `PascalCase` (`class FileReader`).
- Variables/members: `snake_case` (`retry_count`).
- Constants: `kCamelCase` (`kMaxRetries`); macros: `ALL_CAPS`.
- Files: `foo_bar.h` / `foo_bar.cc`.

#### Comments

- Explain *why*, not *what*; skip obvious code.
- Use `//`; block comments for file/section headers.
- Document ownership, thread-safety, non-trivial APIs.
- `TODO(name): actionable description`.

#### Formatting

- Wrap at logical boundaries; break long param lists across lines.
- Always use braces, even for single-line blocks.
- Consistent pointer/ref style: `const Foo* ptr`, `Bar& ref`.

#### Language Features

- Prefer `enum`/`enum class` over macros for constants (type safety).
- Use fixed-width types (`int32_t`, `uint8_t`) instead of `int`/`long`.
- Use `const`/`constexpr`/`constinit` to express immutability.
- Smart pointers for ownership (`unique_ptr`, `shared_ptr`); raw ptr = non-owning.
- `nullptr` always (never `0`/`NULL`).
- Avoid macros; prefer `constexpr`/inline functions. Exception: include guards.
- `auto` when type is obvious from context; spell out when type matters to reader.
- No hardcoded values or opaque conditions that require reverse-engineering; extract into named `constexpr`, inline helpers, or macros (e.g. `IsRetryableError(code)` over `code == 3 || code == 7`).

#### Functions

- Short, single-responsibility; exception: FSMs or perf-critical code.
- Return values over output params; e.g. return `Result` struct.
- Default args only when obvious and stable; avoid in virtual functions.

#### Classes

- Simple constructors; move failable work to `Create()`/init.
- `explicit` on single-arg constructors.
- Clear ownership: `unique_ptr` for owned, raw ptr for observed.
- Copy/move only with clear semantics; delete copy for unique-resource types.
- `struct` = passive data; `class` = behavior + invariants.
- Composition over inheritance; one interface base + helpers.
- Operator overloads only for obvious semantics (e.g. math types).

#### Header Files

- Each `.cc` has matching `.h`; exception: small `main()` or unit tests.
- Headers self-contained (compile alone); include what you use directly.
- Include guard: `PROJECT_PATH_FILE_H_`.
- Prefer `#include` over forward decl; exception: heavy deps where fwd-decl cuts compile time.
- Inline defs: trivial getters/`constexpr` only.
- Include order: own header → C → C++ → third-party → project (alpha within each).

### SystemC

1. Pins: `p_<name>_<dir>` (`p_fault_out`, `p_gpio_inout`)
2. Callbacks: `on_<pin>_change` (`on_fault_out_change`)
3. Wires: `w_<name>_<src>_to_<dst>` (`w_enable_moda_to_modb`); `to` = data-flow direction.
4. Events: `ev_<name>` (`ev_fault_event`)

## Design Principles

### DRY, KISS, YAGNI

- DRY: one source of truth; share knowledge (tables/config), not just helpers.
- KISS: simplest design that works now; add complexity only for proven constraints.
- YAGNI: no speculative features; one concrete impl before generic extension points.

### Functional Style

- Pure domain logic: state in, state out, no hidden mutation; IO at edges.
- Pipelines: parse → normalize → validate → emit.

### OO Design

- Classes for ownership/boundaries; avoid classes for stateless helpers.
- Composition over inheritance; stable base interfaces only for long-lived contracts.

### SOLID

- SRP: one reason to change per module.
- OCP: extend via composition/polymorphism, not editing stable code.
- LSP: subtypes honor base contracts; diverge → new interface.
- ISP: small focused interfaces, no “god” interfaces.
- DIP: depend on abstractions; inject concretes.

## Testing Principles

- Add multiline comment block describing test purpose, setup, and expected behavior.
- Use descriptive test case names following `TC_<module>_<date>_<behavior>` format.
- Test one behavior per test case; avoid multiple assertions testing different things.

## Architectural Principles

- OO for boundaries/lifecycle; FP for data transforms. Classes own resources, pure functions transform data.
- New features = new components, not widespread edits. Decoupled modules, clear interfaces.

## Design Patterns

- Strategy: pluggable algorithms.
- Factory/Builder: complex invariant-heavy construction.
- Adapter: external boundaries.
- Pipeline/Chain: staged transforms.
- State/tables: explicit FSMs.

## References[NOT FOR AI USE]

1. [Google C++ Style Guide](https://google.github.io/styleguide/cppguide.html)

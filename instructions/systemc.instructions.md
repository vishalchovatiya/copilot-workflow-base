---
applyTo: "**/*systemc*/**/*.h,**/*systemc*/**/*.hpp,**/*systemc*/**/*.hh,**/*systemc*/**/*.c,**/*systemc*/**/*.cc,**/*systemc*/**/*.cpp,**/*systemc*/**/*.cxx,**/model/**/*.h,**/model/**/*.hpp,**/model/**/*.cpp,**/models/**/*.h,**/models/**/*.hpp,**/models/**/*.cpp,**/tb/**/*.cpp,**/testbench/**/*.cpp"
---

# SystemC Instructions for GitHub Copilot

## Scope
These instructions apply to SystemC models, simulation glue, transactors, testbenches, and related C/C++ source files. Optimize for simulation correctness, determinism, and maintainable model structure.

## Modeling priorities
- Preserve simulation semantics first; do not make changes that alter scheduling behavior unless explicitly requested.
- Be careful with delta cycles, event ordering, reset behavior, and process sensitivity.
- Prefer simple, explicit model behavior over overly generic helper abstractions.
- Keep the code readable for engineers debugging timing, state transitions, and signal interactions.

## Process selection
- Use `SC_METHOD` for combinational or event-triggered logic that should not block.
- Use `SC_THREAD` or `SC_CTHREAD` only when waits, clocked sequencing, or reset-driven procedural behavior are truly needed.
- Do not add `wait()` inside `SC_METHOD`.
- When modifying sensitivity, state clearly whether the process is static-sensitive, clocked, or reset-aware.

## Timing and event behavior
- Treat timing changes as functional changes.
- Do not insert `wait(SC_ZERO_TIME)` or extra notifications casually.
- Be explicit about immediate vs delayed notification semantics when using `sc_event`.
- Keep clock, reset, and handshake behavior easy to trace.
- When suggesting TLM timing or quantum changes, explain the simulation consequence.

## Signals, ports, and interfaces
- Prefer explicit port and signal types that match the abstraction level of the model.
- Preserve existing conventions for `sc_in`, `sc_out`, `sc_signal`, `sc_fifo`, sockets, and custom channels.
- Do not widen or narrow signal types without calling out serialization, tracing, and ABI implications.
- Keep port binding and constructor wiring clear and local.

## State and concurrency
- Minimize shared mutable state between processes.
- When multiple processes interact, make data flow and synchronization explicit.
- Avoid hidden dependencies through global objects or file-scope mutable state.
- Be cautious when introducing containers or ownership models that may outlive simulation objects incorrectly.

## Reset behavior
- Preserve reset semantics exactly unless the task is specifically about reset changes.
- Distinguish synchronous and asynchronous reset behavior clearly.
- Ensure internal state, events, FIFOs, and outputs are initialized consistently with existing model expectations.

## TLM guidance
- If the code uses TLM-2.0, preserve the existing abstraction level and socket conventions.
- Respect blocking vs non-blocking transport semantics.
- Do not invent timing annotations, DMI handling, or payload extension behavior.
- Keep initiator/target responsibilities explicit.

## Testbench guidance
- Prefer deterministic stimulus and reproducible end conditions.
- Keep monitors, scoreboards, and checks simple and targeted.
- When proposing a test, include expected signal or transaction outcomes.
- Avoid sleeps or waits that only “seem long enough”; synchronize on meaningful events where possible.

## Tracing and debug
- Preserve existing tracing style for VCD, waveform, and log output.
- When adding debug output, avoid flooding the simulation hot path.
- Prefer diagnostics that help isolate ordering, timing, reset, and handshake issues.

## Performance guidance
- Assume simulation throughput matters.
- Avoid unnecessary dynamic allocation, string formatting, container churn, and repeated work inside frequently triggered processes.
- Prefer lightweight data movement and stable ownership.

## Build and ABI cautions
- Keep suggestions compatible with the SystemC library build, compiler version, and C++ standard used by the project.
- Do not suggest changes that could create ABI mismatches between the project and the SystemC installation.
- Be careful with compile definitions, link ordering, and transitive include assumptions on simulation targets.

## Response format
- Start with the semantic risk or modeling issue.
- Then provide the smallest correct code change.
- Mention timing, delta-cycle, reset, or TLM implications when relevant.
- If there is a cleaner alternative, present it after the minimal fix.

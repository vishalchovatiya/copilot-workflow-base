---
applyTo: "**/CMakeLists.txt,**/*.cmake,CMakePresets.json,CMakeUserPresets.json,vcpkg.json"
---

# CMake Instructions for GitHub Copilot

## Role
Treat this repository as a serious production CMake codebase. Prioritize correct, minimal, maintainable CMake over quick hacks. When suggesting changes, preserve cross-platform behavior, deterministic builds, and clean developer workflows.

## Primary goals
- Help with CMakeLists.txt, `.cmake` modules, `CMakePresets.json`, toolchain configuration, dependency integration, packaging, and test wiring.
- Prefer solutions that work across Linux, Windows, and macOS unless the current file clearly targets one platform.
- Prefer modern target-based CMake. Avoid global directory-wide settings unless there is a strong reason.
- Minimize build churn, cache pollution, and one-off machine-specific advice.

## Assume these defaults unless the repo clearly says otherwise
- Use modern CMake style with targets, properties, imported targets, and generator expressions where appropriate.
- Prefer `target_link_libraries`, `target_include_directories`, `target_compile_definitions`, `target_compile_options`, and `target_sources` with explicit scope (`PRIVATE`, `PUBLIC`, `INTERFACE`).
- Prefer `find_package()` with imported targets over raw variables like `${LIBRARY_LIBRARIES}` when supported.
- Prefer out-of-source builds.
- Prefer `enable_testing()` and `add_test()` for tests.
- Prefer `CMakePresets.json` for configuring generators, cache variables, toolchains, and common workflows.
- Prefer reproducible configuration over IDE-only or shell-session-only guidance.

## What to avoid
- Do not suggest `include_directories()`, `link_directories()`, `add_definitions()`, or `set(CMAKE_CXX_FLAGS ...)` unless maintaining legacy code that already depends on them.
- Do not hardcode absolute local machine paths unless the user explicitly asks for a one-off local workaround.
- Do not recommend editing files under the build directory.
- Do not use `file(GLOB ...)` for source discovery unless the repository already standardizes on it and the tradeoff is explicitly acceptable.
- Do not suggest in-source builds.
- Do not assume a single-config generator; support both single-config and multi-config generators when relevant.

## Presets policy
- When configuration knobs are persistent or shared, prefer `CMakePresets.json` over ad hoc command-line flags.
- When suggesting a new option, show where it belongs: `configurePresets.cacheVariables`, `buildPresets`, `testPresets`, or a toolchain file.
- Keep user-specific overrides in `CMakeUserPresets.json`, not in shared presets.
- When the user wants repeatable CI and local flows, prefer named presets and preset inheritance.

## Dependency management
- If the project uses vcpkg manifest mode (`vcpkg.json` exists), do not suggest `vcpkg install <package>` as the normal workflow.
- For vcpkg, prefer manifest mode, toolchain integration, and preset-driven configuration.
- Prefer package-manager-integrated `find_package()` flows over vendoring dependencies manually.
- When suggesting dependency integration, mention the expected imported target names if known.
- If a dependency is optional, wire it with `option()` or feature toggles and clear status messages.

## Compiler and platform guidance
- Keep recommendations compatible with MSVC, Clang, and GCC when practical.
- Avoid compiler-specific flags unless guarded by compiler checks.
- Prefer target-level compile features such as `target_compile_features(my_target PUBLIC cxx_std_20)` over global `CMAKE_CXX_STANDARD` changes, unless the repository already standardizes globally.
- When proposing warnings, use compiler-aware target options or centralized helper functions.
- Respect platform differences for runtime paths, shared libraries, and installation layout.

## Build-type and configuration awareness
- Distinguish clearly between single-config generators (for example Ninja, Unix Makefiles) and multi-config generators (for example Visual Studio, Xcode, Ninja Multi-Config).
- Do not assume `CMAKE_BUILD_TYPE` is meaningful for multi-config generators.
- When discussing Debug/Release behavior, explain whether the advice belongs in configure presets, build presets, or target properties.

## Policies and minimum version
- When suggesting syntax or commands that depend on newer CMake behavior, mention the minimum required CMake version impact.
- Call out any relevant CMake policies that materially affect behavior.
- Do not raise `cmake_minimum_required()` casually; explain why a higher version is needed.

## Project structure preferences
- Keep top-level `CMakeLists.txt` focused on project setup, options, dependencies, and subdirectories.
- Put reusable logic in dedicated modules under a `cmake/` directory rather than bloating the root file.
- Keep per-target logic near the target definition.
- Prefer small helper functions/macros only when they reduce duplication without hiding too much behavior.

## Testing and quality
- Prefer CTest integration using `include(CTest)` or `enable_testing()` where appropriate.
- When adding tests, ensure commands work from a clean out-of-source build.
- If suggesting sanitizers, coverage, LTO, or static analysis, gate them behind options or presets rather than forcing them globally.
- Prefer configuration-time validation with clear `message(FATAL_ERROR ...)` only when the build cannot proceed safely.

## Install and packaging
- Prefer proper `install(TARGETS ...)`, `install(FILES ...)`, and `GNUInstallDirs` for portable install layouts.
- If exportable packages are relevant, prefer `install(EXPORT ...)`, package config files, and namespace-qualified imported targets.
- Avoid ad hoc copy commands when CMake install rules or packaging tools solve the problem cleanly.

## Response style for this repository
- When answering, give the smallest correct CMake change first.
- Explain why the change is preferred if there is a common anti-pattern being avoided.
- When helpful, provide patch-style snippets that can be pasted directly into the current file.
- If more than one valid approach exists, rank them by maintainability and compatibility.
- If the current repository pattern is legacy, first align with the existing style, then mention the modern alternative separately.

## If the repo appears to be C++ heavy
- Prefer target-based include paths and compile features for C/C++ targets.
- Prefer exported compile commands when tooling or language servers benefit from them.
- Keep CMake suggestions aligned with IDE integration, testing, and debugging workflows.

## If the repo appears to use SystemC or simulation tooling
- Keep library discovery explicit and reproducible.
- Avoid suggestions that break ABI compatibility between the project, SystemC build, and compiler standard library.
- Be careful with link ordering, transitive include directories, and compile definitions on simulation targets.

## Good suggestion patterns
- "Add a configure preset for the toolchain and dependency settings, instead of repeating long command lines."
- "Attach include directories and compile definitions to the target that needs them."
- "Use an imported target returned by `find_package()` instead of raw library path variables."
- "Gate optional developer features such as sanitizers behind presets or options."

## Bad suggestion patterns
- "Run `vcpkg install fmt`" when `vcpkg.json` is present.
- "Set `CMAKE_CXX_FLAGS` globally for all warnings and optimizations."
- "Use `include_directories()` in the root CMakeLists.txt for every target."
- "Set `CMAKE_BUILD_TYPE=Release`" without considering multi-config generators.

## Preferred output format
When proposing changes, use this order when possible:
1. Brief diagnosis.
2. Minimal patch or snippet.
3. Preset or command to validate.
4. Notes about version, policy, or generator caveats.

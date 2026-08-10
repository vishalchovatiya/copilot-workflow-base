#!/usr/bin/env bash
# bootstrap.sh — onboard a repository that consumes copilot-workflow-base.
#
# Idempotent and safe to re-run. It:
#   1. installs the VS Code extensions vendored in extensions/ (skip with --no-extensions),
#   2. initializes/updates the .github/shared submodule (and any nested ones),
#   3. sets `git config submodule.recurse true` so future pulls stay in sync,
#   4. (optional, --copy-skills) copies shared skills into .github/skills/ as a
#      fallback for VS Code builds that lack the `chat.agentSkillsLocations` setting.
#
# Run it from anywhere; it locates the consuming repo root itself:
#   bash .github/shared/bootstrap.sh [--copy-skills] [--no-extensions] [--copy-extensions]
#
# Rollback: the copy fallback writes only into .github/skills/shared-*/ ; delete those
# folders to undo. Extensions are removed with `extensions/install.sh --uninstall`.
# Everything else is standard git submodule state.
set -euo pipefail

COPY_SKILLS=0
NO_EXTENSIONS=0
COPY_EXTENSIONS=0
for arg in "$@"; do
  case "$arg" in
    --copy-skills) COPY_SKILLS=1 ;;
    --no-extensions) NO_EXTENSIONS=1 ;;
    --copy-extensions) COPY_EXTENSIONS=1 ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) echo "bootstrap.sh: unknown argument '$arg'" >&2; exit 2 ;;
  esac
done

# This script lives at <repo>/.github/shared/bootstrap.sh → repo root is two levels up.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

# Extensions are installed per machine, so this runs before any repo detection - it works
# the same whether this clone is a submodule or a standalone machine-wide checkout.
EXT_INSTALLER="$SCRIPT_DIR/extensions/install.sh"
if [ "$NO_EXTENSIONS" -eq 0 ] && [ -f "$EXT_INSTALLER" ]; then
  echo "==> installing vendored VS Code extensions"
  if [ "$COPY_EXTENSIONS" -eq 1 ]; then bash "$EXT_INSTALLER" --copy; else bash "$EXT_INSTALLER"; fi
fi

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if ! git -C "$REPO_ROOT" rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "bootstrap.sh: '$REPO_ROOT' is not inside a git repository — nothing to do." >&2
  exit 0
fi
REPO_ROOT="$(git -C "$REPO_ROOT" rev-parse --show-toplevel)"

echo "==> copilot-workflow-base bootstrap"
echo "    repo: $REPO_ROOT"

if [ -f "$REPO_ROOT/.gitmodules" ]; then
  echo "==> syncing submodules"
  git -C "$REPO_ROOT" submodule sync --recursive
  git -C "$REPO_ROOT" submodule update --init --recursive
else
  echo "    no .gitmodules found — skipping submodule update"
fi

echo "==> setting submodule.recurse = true"
git -C "$REPO_ROOT" config submodule.recurse true

COPIED=0
if [ "$COPY_SKILLS" -eq 1 ]; then
  SHARED_SKILLS="$REPO_ROOT/.github/shared/skills"
  DEST_SKILLS="$REPO_ROOT/.github/skills"
  if [ -d "$SHARED_SKILLS" ]; then
    echo "==> copying shared skills (fallback for VS Code without chat.agentSkillsLocations)"
    mkdir -p "$DEST_SKILLS"
    for skill in "$SHARED_SKILLS"/*/; do
      [ -d "$skill" ] || continue
      name="$(basename "$skill")"
      dest="$DEST_SKILLS/shared-$name"
      rm -rf "$dest"
      cp -R "$skill" "$dest"
      echo "    -> .github/skills/shared-$name"
      COPIED=$((COPIED + 1))
    done
  else
    echo "    no shared skills directory at $SHARED_SKILLS — skipping copy"
  fi
fi

echo ""
echo "==> done."
echo "    submodules initialized/updated, submodule.recurse enabled."
if [ "$COPY_SKILLS" -eq 1 ]; then
  echo "    shared skills copied: $COPIED (remove .github/skills/shared-* to undo)."
else
  echo "    skills are loaded from the submodule via chat.agentSkillsLocations"
  echo "    (re-run with --copy-skills only on older VS Code builds)."
fi

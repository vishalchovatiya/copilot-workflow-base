#!/usr/bin/env bash
# Install the VS Code extensions vendored in this folder (Linux / macOS / Git-Bash).
#
# Every subfolder holding a package.json that declares publisher, name, version and
# engines.vscode is treated as an extension. Drop a new folder in and it is picked up
# automatically - this script never needs editing.
#
# Each extension is symlinked into the VS Code extensions folder so `git pull` updates it
# in place. --copy falls back to a plain copy (re-run after every pull in that case).
#
#   bash extensions/install.sh                  # all extensions
#   bash extensions/install.sh md-flashcards    # one, by folder name
#   bash extensions/install.sh --list           # show what would be installed
#   bash extensions/install.sh --uninstall      # remove them again
#
# Rollback: --uninstall, or delete the target folders printed at the end.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
EXT_DIR="$HOME/.vscode/extensions"
MODE="link"
NAMES=()

for arg in "$@"; do
  case "$arg" in
    --insiders)  EXT_DIR="$HOME/.vscode-insiders/extensions" ;;
    --copy)      MODE="copy" ;;
    --uninstall) MODE="uninstall" ;;
    --list)      MODE="list" ;;
    -h|--help)   grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*)          echo "install.sh: unknown option '$arg'" >&2; exit 2 ;;
    *)           NAMES+=("$arg") ;;
  esac
done

# Read a top-level string field from a package.json without needing node or jq.
field() { sed -n "s/.*\"$2\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p" "$1" | head -1; }

wanted() {
  [ ${#NAMES[@]} -eq 0 ] && return 0
  for n in "${NAMES[@]}"; do [ "$n" = "$1" ] && return 0; done
  return 1
}

# Not an error: the repo is often cloned on machines without VS Code (servers, CI).
if [ "$MODE" != "list" ] && [ ! -d "$EXT_DIR" ]; then
  echo "    VS Code extensions folder not found ($EXT_DIR) - skipping extension install." >&2
  exit 0
fi

FOUND=0
for dir in "$ROOT"/*/; do
  MANIFEST="$dir/package.json"
  [ -f "$MANIFEST" ] || continue

  FOLDER="$(basename "$dir")"
  wanted "$FOLDER" || continue

  PUBLISHER="$(field "$MANIFEST" publisher)"
  NAME="$(field "$MANIFEST" name)"
  VERSION="$(field "$MANIFEST" version)"
  if [ -z "$PUBLISHER" ] || [ -z "$NAME" ] || [ -z "$VERSION" ] || ! grep -q '"vscode"' "$MANIFEST"; then
    echo "    skipping $FOLDER: package.json needs publisher, name, version and engines.vscode" >&2
    continue
  fi

  FOUND=$((FOUND + 1))
  ID="$PUBLISHER.$NAME"
  TARGET="$EXT_DIR/$ID-$VERSION"

  if [ "$MODE" = "list" ]; then
    printf '%-20s %-30s %-10s %s\n' "$FOLDER" "$ID" "$VERSION" "$([ -e "$TARGET" ] && echo installed || echo -)"
    continue
  fi

  echo "==> $FOLDER ($ID $VERSION)"
  # No trailing slash: this removes the symlink itself, never the source folder.
  rm -rf "$EXT_DIR/$ID"-*

  [ "$MODE" = "uninstall" ] && continue

  if [ "$MODE" = "link" ]; then
    ln -s "${dir%/}" "$TARGET"
    echo "    linked  -> $TARGET"
  else
    mkdir -p "$TARGET"
    cp -R "${dir%/}"/. "$TARGET/"
    echo "    copied  -> $TARGET   (re-run after every git pull)"
  fi
done

if [ "$FOUND" -eq 0 ]; then
  echo "no extensions found under $ROOT" >&2
  [ ${#NAMES[@]} -eq 0 ] || exit 1
  exit 0
fi

[ "$MODE" = "list" ] && exit 0

echo
if [ "$MODE" = "uninstall" ]; then
  echo "==> uninstalled. Run 'Developer: Reload Window' in VS Code."
else
  echo "==> done. Run 'Developer: Reload Window' in VS Code."
fi

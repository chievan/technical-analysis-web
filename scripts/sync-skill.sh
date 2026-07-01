#!/usr/bin/env bash
set -euo pipefail

# Sync skill files from source directory to backend/skill/
# Usage: ./scripts/sync-skill.sh /path/to/technical-analysis-pro

SRC="${1:?Usage: $0 <source-skill-dir>}"
DEST="$(cd "$(dirname "$0")/.." && pwd)/backend/skill"

if [ ! -d "$SRC" ]; then
  echo "Error: source directory does not exist: $SRC"
  exit 1
fi

echo "Syncing skill from $SRC to $DEST"

# SKILL.md
if [ -f "$SRC/SKILL.md" ]; then
  cp "$SRC/SKILL.md" "$DEST/SKILL.md"
  echo "  ✓ SKILL.md"
fi

# scripts/
if [ -d "$SRC/scripts" ]; then
  mkdir -p "$DEST/scripts"
  cp "$SRC/scripts"/*.py "$DEST/scripts/" 2>/dev/null || true
  echo "  ✓ scripts/ ($(ls "$SRC/scripts"/*.py 2>/dev/null | wc -l) files)"
fi

# references/
if [ -d "$SRC/references" ]; then
  mkdir -p "$DEST/references"
  cp "$SRC/references"/*.md "$DEST/references/" 2>/dev/null || true
  echo "  ✓ references/ ($(ls "$SRC/references"/*.md 2>/dev/null | wc -l) files)"
fi

echo "Done. Skill synced to $DEST"

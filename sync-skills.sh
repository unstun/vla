#!/usr/bin/env bash
set -euo pipefail

# Restore the exact Vendor Skill revision recorded in vendor-skills.lock, then
# expose project-owned and Vendor Skills to Codex, Claude Code, and Cursor.
# Re-running is safe. Real project/platform directories are never replaced.

ROOT="$(cd "$(dirname "$0")" && pwd)"
LOCK_FILE="$ROOT/vendor-skills.lock"
UPSTREAM="$ROOT/.skills-upstream"
AGENT_SKILLS="$ROOT/.agents/skills"
CLAUDE_SKILLS="$ROOT/.claude/skills"
CURSOR_SKILLS="$ROOT/.cursor/skills"
PLATFORM_DESTS=("$CLAUDE_SKILLS" "$CURSOR_SKILLS")
VENDOR_DESTS=("$CLAUDE_SKILLS" "$CURSOR_SKILLS" "$AGENT_SKILLS")

# Claude Code ships a built-in /code-review. Keep it instead of shadowing it
# with the Vendor Skill; Codex and Cursor still receive the Vendor version.
CLAUDE_EXCLUDE=" code-review "

if [ ! -f "$LOCK_FILE" ]; then
  echo "error: missing $LOCK_FILE" >&2
  exit 1
fi

VENDOR_URL="$(git config -f "$LOCK_FILE" --get vendor.repository || true)"
VENDOR_COMMIT="$(git config -f "$LOCK_FILE" --get vendor.commit || true)"

if [ -z "$VENDOR_URL" ]; then
  echo "error: vendor.repository is missing from $LOCK_FILE" >&2
  exit 1
fi
if ! [[ "$VENDOR_COMMIT" =~ ^[0-9a-fA-F]{40}$ ]]; then
  echo "error: vendor.commit must be a full 40-character Git commit" >&2
  exit 1
fi

if [ ! -d "$UPSTREAM/.git" ]; then
  if [ -e "$UPSTREAM" ]; then
    echo "error: $UPSTREAM exists but is not a Git checkout" >&2
    exit 1
  fi
  # Materialize the default worktree before the dirty-check below. A
  # --no-checkout clone reports every tracked path as deleted and would be
  # rejected as dirty on the very first synchronization.
  git clone --filter=blob:none "$VENDOR_URL" "$UPSTREAM"
fi

ACTUAL_URL="$(git -C "$UPSTREAM" remote get-url origin 2>/dev/null || true)"
if [ "$ACTUAL_URL" != "$VENDOR_URL" ]; then
  echo "error: Vendor origin mismatch" >&2
  echo "  expected: $VENDOR_URL" >&2
  echo "  actual:   ${ACTUAL_URL:-<missing>}" >&2
  exit 1
fi

if [ -n "$(git -C "$UPSTREAM" status --porcelain)" ]; then
  echo "error: Vendor checkout is dirty; preserve or discard its changes explicitly" >&2
  exit 1
fi

if ! git -C "$UPSTREAM" cat-file -e "$VENDOR_COMMIT^{commit}" 2>/dev/null; then
  git -C "$UPSTREAM" fetch --quiet origin
fi
if ! git -C "$UPSTREAM" cat-file -e "$VENDOR_COMMIT^{commit}" 2>/dev/null; then
  echo "error: pinned Vendor commit is unavailable: $VENDOR_COMMIT" >&2
  exit 1
fi

git -C "$UPSTREAM" checkout --quiet --detach "$VENDOR_COMMIT"
RESOLVED_COMMIT="$(git -C "$UPSTREAM" rev-parse HEAD)"
if [ "$RESOLVED_COMMIT" != "$VENDOR_COMMIT" ]; then
  echo "error: Vendor checkout did not resolve to the lock-file commit" >&2
  exit 1
fi

PLUGIN="$UPSTREAM/.claude-plugin/plugin.json"
if [ ! -f "$PLUGIN" ]; then
  echo "error: pinned Vendor checkout has no $PLUGIN" >&2
  exit 1
fi

for DEST in "${VENDOR_DESTS[@]}"; do
  mkdir -p "$DEST"
done

ensure_project_link() {
  local dest="$1"
  local name="$2"
  local target="$dest/$name"

  if [ -e "$target" ] && [ ! -L "$target" ]; then
    return 0
  fi
  ln -sfn "../../.agents/skills/$name" "$target"
}

# Project-owned real directories are canonical. Mirror them into platform
# discovery folders unless a platform already owns a real directory there.
project_count=0
for PROJECT_SKILL in "$AGENT_SKILLS"/*; do
  [ -d "$PROJECT_SKILL" ] || continue
  [ -L "$PROJECT_SKILL" ] && continue
  [ -f "$PROJECT_SKILL/SKILL.md" ] || continue
  NAME="$(basename "$PROJECT_SKILL")"
  for DEST in "${PLATFORM_DESTS[@]}"; do
    ensure_project_link "$DEST" "$NAME"
  done
  project_count=$((project_count + 1))
done

vendor_count=0
while IFS= read -r REL; do
  SRC="$UPSTREAM/${REL#./}"
  NAME="$(basename "$SRC")"
  if [ ! -f "$SRC/SKILL.md" ]; then
    echo "skip (no SKILL.md): $REL" >&2
    continue
  fi

  # A real project-owned directory always wins over a Vendor Skill with the
  # same name. Its platform links were created above.
  PROJECT_SKILL="$AGENT_SKILLS/$NAME"
  if [ -d "$PROJECT_SKILL" ] && [ ! -L "$PROJECT_SKILL" ]; then
    continue
  fi

  for DEST in "${VENDOR_DESTS[@]}"; do
    TARGET="$DEST/$NAME"
    if [ "$DEST" = "$CLAUDE_SKILLS" ] && [[ "$CLAUDE_EXCLUDE" == *" $NAME "* ]]; then
      [ -L "$TARGET" ] && unlink "$TARGET"
      continue
    fi
    if [ -e "$TARGET" ] && [ ! -L "$TARGET" ]; then
      echo "skip (real platform entry wins): ${TARGET#$ROOT/}" >&2
      continue
    fi
    ln -sfn "../../.skills-upstream/${REL#./}" "$TARGET"
  done
  vendor_count=$((vendor_count + 1))
done < <(grep -oE '\./skills/[A-Za-z0-9_-]+/[A-Za-z0-9_-]+' "$PLUGIN" | sort -u)

echo "Vendor commit: $RESOLVED_COMMIT"
echo "Project Skills mirrored: $project_count"
echo "Vendor Skills linked: $vendor_count"
echo "Discovery directories:"
for DEST in "${VENDOR_DESTS[@]}"; do
  echo "  ${DEST#$ROOT/}"
done

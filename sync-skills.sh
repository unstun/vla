#!/usr/bin/env bash
set -euo pipefail

# Symlinks the "promoted" Matt Pocock skills (the curated set listed in the
# upstream repo's .claude-plugin/plugin.json) into this project's harness skill
# directories, so BOTH Claude Code and Codex can discover them:
#
#   .claude/skills   -> Claude Code (project-level skills)
#   .agents/skills   -> Codex (Agent-Skills standard, scanned from repo root)
#
# Each entry is a relative symlink into the live upstream clone at
# .skills-upstream/, so updating is:
#
#   git -C .skills-upstream pull   # get the author's latest
#   ./sync-skills.sh               # re-link (picks up any new promoted skills)
#
# Re-running is safe and idempotent.

ROOT="$(cd "$(dirname "$0")" && pwd)"
UPSTREAM="$ROOT/.skills-upstream"
PLUGIN="$UPSTREAM/.claude-plugin/plugin.json"
CLAUDE_SKILLS="$ROOT/.claude/skills"
DESTS=("$CLAUDE_SKILLS" "$ROOT/.agents/skills")

# Per-harness exclusions: space-delimited skill names NOT to link into a given
# directory. Claude Code ships a strong built-in /code-review, so we keep that
# and don't shadow it — while Codex (.agents/skills), which has no built-in
# code-review, still gets Matt's version. Add names between the spaces to skip.
CLAUDE_EXCLUDE=" code-review "

if [ ! -f "$PLUGIN" ]; then
  echo "error: $PLUGIN not found." >&2
  echo "Clone the upstream repo first: git clone https://github.com/mattpocock/skills.git .skills-upstream" >&2
  exit 1
fi

for DEST in "${DESTS[@]}"; do
  mkdir -p "$DEST"
done

count=0
# Extract promoted skill paths like ./skills/engineering/ask-matt from plugin.json.
while IFS= read -r rel; do
  src="$UPSTREAM/${rel#./}"
  name="$(basename "$src")"
  if [ ! -f "$src/SKILL.md" ]; then
    echo "skip (no SKILL.md): $rel" >&2
    continue
  fi
  # Project-owned skills are tracked as real directories under
  # .agents/skills. Never replace them with a vendor symlink if upstream later
  # promotes a skill with the same name.
  project_skill="$ROOT/.agents/skills/$name"
  if [ -d "$project_skill" ] && [ ! -L "$project_skill" ]; then
    continue
  fi
  for DEST in "${DESTS[@]}"; do
    target="$DEST/$name"
    # Honor per-harness exclusions (currently: code-review out of Claude Code).
    if [ "$DEST" = "$CLAUDE_SKILLS" ] && [[ "$CLAUDE_EXCLUDE" == *" $name "* ]]; then
      [ -L "$target" ] && rm -f "$target"
      continue
    fi
    # Replace a real dir/file left by an older vendor copy-based install.
    if [ -e "$target" ] && [ ! -L "$target" ]; then
      rm -rf "$target"
    fi
    # Both DESTS live exactly two levels under ROOT, so ../.. == ROOT.
    ln -sfn "../../.skills-upstream/${rel#./}" "$target"
  done
  count=$((count + 1))
done < <(grep -oE '\./skills/[A-Za-z0-9_-]+/[A-Za-z0-9_-]+' "$PLUGIN" | sort -u)

echo "Linked $count skills into:"
for DEST in "${DESTS[@]}"; do
  echo "  ${DEST#$ROOT/}"
done

#!/usr/bin/env bash
# ============================================================================
# Codex PostToolUse hook: reset reviewed:true after apply_patch edits
# ----------------------------------------------------------------------------
# Claude Code's hook receives file_path for Edit/Write. Codex reports
# apply_patch, so this wrapper scans changed trusted-knowledge Markdown files.
# 扫描范围包含 unstaged、staged 和 untracked,避免新建/已暂存文档漏掉。
# ============================================================================
set -euo pipefail

cat >/dev/null || true

git_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$git_root"

python3 - <<'PY'
import subprocess
from pathlib import Path

prefixes = (
    ".pipeline/survey/",
    ".pipeline/experiments/",
    "bigmemory/冷区/调研记录/",
)

def git_lines(*args: str) -> set[str]:
    try:
        out = subprocess.check_output(
            ["git", *args],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return set()
    return {line.strip() for line in out.splitlines() if line.strip()}

changed_paths = set()
changed_paths |= git_lines("diff", "--name-only")
changed_paths |= git_lines("diff", "--cached", "--name-only")
changed_paths |= git_lines("ls-files", "--others", "--exclude-standard")

for raw in sorted(changed_paths):
    if not raw.endswith(".md"):
        continue
    if not raw.startswith(prefixes):
        continue

    path = Path(raw)
    if not path.exists():
        continue
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        continue
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        continue
    frontmatter, body = parts[1], parts[2]
    if "reviewed: true" not in frontmatter:
        continue
    frontmatter = frontmatter.replace("reviewed: true", "reviewed: false", 1)
    path.write_text(f"---\n{frontmatter}---\n{body}", encoding="utf-8")
PY

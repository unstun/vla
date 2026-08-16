#!/usr/bin/env bash
# PostToolUse hook: AI 编辑试点目录内 reviewed:true 的文档时自动重置为 false
# 试点目录: .pipeline/survey/, .pipeline/experiments/,
#           bigmemory/冷区/调研记录/
set -euo pipefail

payload="$(cat)"
file_path="$(printf '%s' "$payload" | python3 -c 'import json,sys; d=json.load(sys.stdin); print((d.get("tool_input") or {}).get("file_path",""))')"

# ---- 白名单：只处理试点目录 ----
case "$file_path" in
  */.pipeline/survey/*.md|\
  */.pipeline/experiments/*.md|\
  */bigmemory/冷区/调研记录/*.md)
    ;;
  *)
    exit 0
    ;;
esac

# ---- 检测并重置 reviewed: true ----
python3 - "$file_path" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
if not path.exists():
    raise SystemExit(0)

text = path.read_text(encoding="utf-8")
if not text.startswith("---\n"):
    raise SystemExit(0)

parts = text.split("---\n", 2)
if len(parts) < 3:
    raise SystemExit(0)

frontmatter = parts[1]
body = parts[2]
if "reviewed: true" not in frontmatter:
    raise SystemExit(0)

frontmatter = frontmatter.replace("reviewed: true", "reviewed: false", 1)
path.write_text(f"---\n{frontmatter}---\n{body}", encoding="utf-8")
PY

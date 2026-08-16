#!/usr/bin/env bash
# ============================================================
# UserPromptSubmit hook  --  热区新鲜度按需注入
# ------------------------------------------------------------
# 触发条件 : 用户 prompt 中含"上下文/进度/状态/记忆"类关键词
# 目的     : 迁出 SessionStart,避免每次会话启动都注入
#            (硬规则 #2 注意事项 Context Is All You Need)
# 对照     : 原 session-start-lite.sh 无条件注入热区检查
# ============================================================
set -euo pipefail

# ------------------------------------------------------------
# 读 stdin  --  Claude Code UserPromptSubmit 注入的 JSON
# ------------------------------------------------------------
INPUT=$(cat)

PROMPT=$(python3 -c "
import json, sys
try:
    d = json.loads(sys.stdin.read())
    print(d.get('prompt') or d.get('user_prompt') or d.get('message') or '')
except Exception:
    pass
" <<< "$INPUT" 2>/dev/null || echo "")

# ------------------------------------------------------------
# 关键词匹配  --  中英混合,触发记忆/状态类查询时才拉热区
# ------------------------------------------------------------
KEYWORDS='进度|现在|状态|未关闭|上次|最近|记忆|热区|项目|recall|memory|status|progress'

if ! echo "$PROMPT" | grep -qiE "$KEYWORDS"; then
  exit 0
fi

# ------------------------------------------------------------
# 热区新鲜度检查  --  超过 24h 未更新则提醒 /archive
# ------------------------------------------------------------
STALE_HOURS=24
HOT_FILES=(
  "bigmemory/热区/状态简报.md"
  "bigmemory/热区/未关闭决策.md"
  "bigmemory/热区/近期改动.md"
)

mtime_epoch() {
  if stat -f %m "$1" >/dev/null 2>&1; then
    stat -f %m "$1"
  else
    stat -c %Y "$1"
  fi
}

now=$(date +%s)
stale_found=false
echo "=== 热区检查 (auto-injected on memory-keyword) ==="
for f in "${HOT_FILES[@]}"; do
  if [ ! -f "$f" ]; then
    echo "⚠ 热区缺失: $f"
    stale_found=true
    continue
  fi
  mtime=$(mtime_epoch "$f")
  age_hours=$(( (now - mtime) / 3600 ))
  if [ "$age_hours" -ge "$STALE_HOURS" ]; then
    echo "⚠ 热区过期: $f (${age_hours}h 未更新)"
    stale_found=true
  fi
done
if [ "$stale_found" = true ]; then
  echo "建议: 运行 /archive 刷新热区"
else
  echo "✓ 热区 3 文件均 <24h 内更新"
fi

exit 0

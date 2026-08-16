#!/usr/bin/env bash
# ============================================================
# UserPromptSubmit hook  --  git 状态按需注入
# ------------------------------------------------------------
# 触发条件 : 用户 prompt 中含 git 相关关键词
# 目的     : 避免每次 session 无脑灌 git 信息 (context 污染)
# 对照     : 原 SessionStart hook 无条件注入 git,现仅保留热区检查
# ============================================================
set -euo pipefail

# ------------------------------------------------------------
# 读 stdin  --  Claude Code UserPromptSubmit 注入的 JSON
# ------------------------------------------------------------
INPUT=$(cat)

# ------------------------------------------------------------
# 提取 prompt 字段
#   Grok 答案给的字段名是 .prompt,这里兼容常见别名避免踩坑
# ------------------------------------------------------------
PROMPT=$(python3 -c "
import json, sys
try:
    d = json.loads(sys.stdin.read())
    print(d.get('prompt') or d.get('user_prompt') or d.get('message') or '')
except Exception:
    pass
" <<< "$INPUT" 2>/dev/null || echo "")

# ------------------------------------------------------------
# 关键词匹配  --  中英混合,精简列表避免误触
# ------------------------------------------------------------
KEYWORDS='git|commit|push|merge|rebase|stash|checkout|提交|推送|合并|切分支'

if echo "$PROMPT" | grep -qiE "$KEYWORDS"; then
  if [ -d .git ]; then
    echo "=== Git (auto-injected on git-keyword) ==="
    git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "(no branch)"
    git log --oneline -5 2>/dev/null || echo "(no commits)"
    git status --short 2>/dev/null || true
  fi
fi

exit 0

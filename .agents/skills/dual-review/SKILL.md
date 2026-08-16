---
name: dual-review
description: Codex + Gemini 双重审核 Codex 的改动，交叉比较后综合输出
version: "1.0"
user-invocable: true
---

# 双重审核

同时调用 Codex (GPT-5.4) 和 Gemini (2.5 Pro) 审核 Codex 的改动，利用两个模型的正交视角互补盲点。

## 执行步骤

### 1. 收集上下文（同单独审核）

```bash
DIFF=$(git diff HEAD)
# 如果无未提交改动
[ -z "$DIFF" ] && DIFF=$(git diff HEAD~1)
FILES=$(git diff HEAD --name-only)
[ -z "$FILES" ] && FILES=$(git diff HEAD~1 --name-only)
```

加上 Codex 做这些改动的理由（从会话上下文提取）。

### 2. 并行调用两个 AI

**必须并行**——两个 Bash 调用放在同一个 message 里：

Bash 1 (Codex)：
```bash
codex exec "<审核 prompt + diff + 理由>" --sandbox read-only 2>&1
```

Bash 2 (Gemini)：
```bash
(echo "<审核 prompt + diff + 理由>") | gemini -m gemini-3.1-pro-preview -p "审核以上 AI 改动" 2>&1
```

### 3. 综合两份审核

收到两份结果后，Codex 自己做综合：

```
## 审核综合报告

### Codex (GPT-5.4) 发现
{Codex 的审核要点}

### Gemini (2.5 Pro) 发现
{Gemini 的审核要点}

### 交叉分析
- 两者一致的问题：{列出}（高置信度，应修复）
- 仅 Codex 发现：{列出}（可能是代码层面的细节）
- 仅 Gemini 发现：{列出}（可能是更高层面的设计问题）

### 建议行动
{按优先级排列的修复建议}
```

### 4. 展示并等待指令

将综合报告展示给 Dr Sun，询问是否需要修复。

## 注意

- 双重审核消耗两倍 token，适合重要改动
- 两个 AI 的 prompt 应完全相同，确保公平比较
- 如果 Gemini 429，降级链：gemini-3.1-pro-preview → gemini-2.5-pro → 默认 Flash

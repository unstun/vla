---
name: codex-review
description: 让 Codex (GPT-5.4) 审核 Codex 的所有改动和推理
version: "1.0"
user-invocable: true
---

# Codex 审核

用 OpenAI Codex CLI 对 Codex 的改动做独立审核。审核范围不限于代码——涵盖改动理由、设计决策、文档变更等一切产出。

## 模型配置

```
CODEX_MODEL=gpt-5.4          # 默认最强模型
CODEX_EFFORT=xhigh            # 推理深度: low / medium / high / xhigh
CODEX_SANDBOX=read-only        # 审核时只读
```

## 执行步骤

### 1. 收集审核上下文

运行以下命令收集 Codex 的所有改动：

```bash
# 未提交的改动
git diff HEAD

# 如果没有未提交改动，取最近的 commit
git diff HEAD~1

# 改动涉及的文件列表
git diff HEAD --name-only
```

### 2. 构建审核 prompt

将以下内容合并为 Codex 的输入 prompt：

```
你是独立代码审查员，正在审核另一个 AI (Codex) 的改动。请审查以下内容：

== 改动的文件 ==
{git diff --name-only 的输出}

== 完整 diff ==
{git diff 的输出}

== Codex 的改动理由 ==
{从当前会话上下文中提取 Codex 做这些改动的理由}

请从以下维度审核：
1. 逻辑正确性——改动是否实现了声称的目的
2. 一致性——跨文件的改动是否互相一致
3. 遗漏——是否有应改但未改的地方
4. 风险——是否引入了潜在问题
5. 改动理由是否站得住脚
这五个维度只是建议不可以不被这个规则框死，终极目的就是检查 cladue 改的有没有问题
输出格式：按严重程度（较重/中等/较低）列出发现，每条附具体文件和行号。最后给一个总体评价。用中文回复。
```

### 3. 调用 Codex

**Cursor 规则**：不要由主 session 调 Agent/插件代跑；把下面命令块交给 Dr Sun 手动执行，完成后回贴输出。

**重要**：长中文 prompt 直接内嵌为 shell 参数不够稳妥——已观察到编码异常和 stdin 阻塞。
推荐将 prompt 写入临时文件，用短英文指令让 Codex 自行读取。

**推荐方式：临时文件 + 短英文指令**（彻底避免 shell 参数嵌入中文）：

```bash
# 写入临时文件
cat > /tmp/codex-review-prompt.txt << 'PROMPT'
{完整 prompt}
PROMPT

# 用短英文指令让 Codex 自行读取文件
codex exec "You are a code reviewer. Read /tmp/codex-review-prompt.txt for the full review prompt and follow it exactly. Output in Chinese." \
  --sandbox read-only 2>&1
```

**备选方式（仅 Claude Code / Droid）：通过 codex:rescue 插件调用**（Cursor 禁用此路径）：

```
使用 Agent tool，subagent_type: "codex:codex-rescue"，
将审核 prompt 作为 Agent 的 prompt 参数传入。
codex:rescue 会自动调用 Codex CLI 并返回结果。
```

### 4. 提取并展示结果

从 Codex 输出中提取最终审核意见（跳过中间的 exec 日志），以结构化格式呈现给 Dr Sun。

### 5. 可选：根据审核意见行动

如果 Codex 发现了真实问题，询问 Dr Sun 是否需要修复。

## 注意

- Codex 会自动读取项目文件来验证审核，不需要手动喂完整代码
- `--sandbox read-only` 确保审核过程不修改任何文件
- 超时设 120 秒，复杂项目可能需要更长
- 输出可能很大（含 exec 日志），只展示最终结论部分

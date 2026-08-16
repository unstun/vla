---
name: archive
description: 对话结束前归档本次变更到项目记忆系统（bigmemory + .pipeline/）。自动提取改动、踩坑、心路等信息写入冷区，刷新热区，更新知识库。
whenToUse: 会话收尾需要把本次改动、踩坑、调研、决策写入 bigmemory 记忆系统并刷新热区时；Dr Sun 说「归档一下」时。
user-invocable: true
allowed-tools: Read, Write, Edit, Glob, Grep, Agent, Bash
---

# Archive Skill — 项目记忆归档

## 触发方式
`/archive`

## 前置条件
当前项目目录下（或上级目录中）存在 `bigmemory/` 目录。

## 执行流程

### Step 1: 定位 bigmemory

从当前工作目录向上查找 `bigmemory/` 目录。如果找不到，提示用户并终止。
同时检测 `.pipeline/` 目录是否存在（影响 Agent 4 是否启动）。

### Step 2: 读取当前状态

读取以下文件了解记忆系统当前状态：

**热区：**
- `bigmemory/热区/状态简报.md`
- `bigmemory/热区/未关闭决策.md`
- `bigmemory/热区/近期改动.md`

**冷区：**
- `bigmemory/冷区/偏好.md`
- `bigmemory/冷区/工作流.md`

同时读取 `bigmemory/格式规范.md` 了解文件格式要求。

### Step 2.5: 会话记录导出已停用

`/archive` 不再导出完整聊天记录，也不再写入 `bigmemory/冷区/会话记录/`。
归档只保留可复查的摘要层信息：改动、踩坑、调研、心路、里程碑、热区状态和 `.pipeline/` 知识库。

### Step 3: 分诊 — 判断归档范围

回顾本次对话，回答以下问题：

**bigmemory 分诊：**

| # | 问题 | 是→写入目标 |
|---|------|-------------|
| Q1 | 产生了代码/配置/文档改动？ | 改动记录 |
| Q2 | 遇到非显而易见的问题（调查超 5 分钟）？ | 踩坑记录 |
| Q3 | 获取了外部信息？ | 调研记录 |
| Q4 | 涉及重要决策或方向变化？ | 心路历程 |
| Q5 | 完成重大里程碑？ | 里程碑 |

**.pipeline/ 分诊（仅当 `.pipeline/` 存在时）：**

| # | 问题 | 是→写入目标 |
|---|------|-------------|
| Q7 | 涉及新文献？ | `.pipeline/literature/index.md` |
| Q8 | 产生实验数据？ | `.pipeline/experiments/YYYYMMDD_<topic>.md` |
| Q9 | 完成一次主题调研？ | `.pipeline/survey/<topic>.md` |
| Q10 | 定义/修改了术语？ | `.pipeline/terminology/terminology.md` |

**如果全部为 NO**，输出"本次对话无需归档"，跳过 Step 4-5，直接进入 Step 6。

### Step 4: 选择归档执行方式

默认优先使用并行 Agent：将归档工作拆分为**最多 4 个并行 Agent**，在同一条消息中同时启动。

**Dr Sun 的“归档”指令已经包含使用本 skill 的 Agent 工作方式。**不要把普通“归档”解释成禁止 subagent；应先尝试启动归档 Agent。

如果工具名称不确定，先用当前平台的工具发现能力查找“spawn agent / subagent / Task / Agent”。工具发现失败、Agent 工具缺失、所有 spawn 尝试失败或平台硬性禁止时，才切换到主会话 fallback。

**归档模型原则**：归档 subagent 使用主会话模型。平台支持继承模型时，不传 `model`；平台必须显式指定模型时，填写当前主会话模型。禁止为了省成本自动降级到 sonnet、mini 或 fast 模型，除非 Dr Sun 明确指定。

**Codex App spawn 重试规则**：先尝试符合职责的 agent type，并默认不指定 `model`、`reasoning_effort` 或 `service_tier`，让 subagent 继承主会话模型。若显式指定主会话模型仍返回模型解析类错误（例如 `could not resolve the child model for service tier validation`），立即重试默认 `spawn_agent`。默认 subagent 能启动时，视为 Agent 路径成功，禁止直接 fallback。

fallback 不是隐藏失败。进入 fallback 前必须记录触发原因，并在 Step 5 报告中写明尝试方式与错误摘要，例如：`Agent 执行：主会话 fallback（尝试：harness_reviewer 指定模型失败；默认 spawn_agent 失败；错误：<摘要>）`。fallback 仍须完成查重、热区全量重写、字数校验、.pipeline 分诊和 git 备份。

**用户更新**：2026-05-30 Dr Sun 明确指出，不能用“不暴露工具限制”来掩盖没有调用 subagent 的事实。归档流程要解决 subagent 未调用问题，而不是把提示语藏掉。

**传递给每个 Agent 的 prompt 必须包含：**
1. 当前日期时间（YYYY-MM-DD HH:MM）
2. bigmemory 绝对路径（+ 项目根目录路径）
3. 本次对话的完整摘要
4. 该 Agent 负责的分诊结果
5. 指示先读 `bigmemory/格式规范.md`

---

#### Agent 1: 冷区事实层

**职责**：Q1 改动记录 + Q2 踩坑记录

只写入分诊通过的类别。追加模式，文件已存在则先读取再追加。

**写入前必须 Grep 查重**，已存在实质相同的记录则跳过。

- **Q1 → 改动记录** → `bigmemory/冷区/改动记录/{TODAY}.md`
  只记录改变系统行为/架构的改动
- **Q2 → 踩坑记录** → `bigmemory/冷区/踩坑记录/{TODAY}.md`
  "原因"字段只写会话中实际验证过的根因，禁止编造

质量标准：每条须回答"未来的我为什么需要知道这个？"

---

#### Agent 2: 冷区认知决策层

**职责**：Q3 调研记录 + Q4 心路历程 + Q5 里程碑 + 偏好/工作流更新

同 Agent 1 的查重和追加规则。

- **Q3 → 调研记录** → `bigmemory/冷区/调研记录/{TODAY}.md`
  URL/数据必须来自会话中实际访问的内容，无法追溯来源标注 `[未验证]`
  **置信度 frontmatter**：新建文件时加 YAML frontmatter（`origin: ai_only` 或 `ai+web`——文内有 URL/DOI/文献 CitationKey 则 `ai+web`，否则 `ai_only`；`reviewed: false`）。已有文件追加时不改 frontmatter，但若编辑了 `reviewed: true` 的文档须重置为 `reviewed: false`。
- **Q4 → 心路历程** → `bigmemory/冷区/心路历程/{TODAY}.md`
  必须包含"为什么"
- **Q5 → 里程碑** → `bigmemory/冷区/里程碑/{TODAY}.md`
- **偏好/工作流** → 对比对话内容与现有文件，有变更时更新并刷新顶部日期

---

#### Agent 3: 热区瘦身

**职责**：冷区关联检索 + 热区全量重写

**关联检索**：Grep `bigmemory/冷区/` 搜索本次关键词，重复踩坑纳入警告，反复模式建议更新工作流。

**热区全量重写**，严格容量预算：

| 文件 | 上限 | 超限处理 |
|------|------|----------|
| 状态简报.md | 1500 字 / 30 行 | 压缩每条到 15 字以内 |
| 未关闭决策.md | 1200 字 / 25 行 | 归档所有已关闭决策 |
| 近期改动.md | 1000 字 / 25 行 | 2天前条目合并为每天 1 条 |

- **状态简报**：活跃任务≤3条 + 关键上下文≤5条 + 未解决警告
- **未关闭决策**：新增/关闭决策；已关闭超7天删除；未关闭超30天标 `[⚠ 长期未决]`
- **近期改动**：今昨≤3条/天，2-4天≤2条/天，5-7天≤1条/天，超7天删除

**写后 `wc -m` 校验**，超限重新压缩。

---

#### Agent 4: .pipeline/ 知识库 + 冷区降级

> 仅当 `.pipeline/` 存在且（Q7-Q10 至少一项 YES 或有冷区文件需降级）时启动。无 `.pipeline/` 的项目跳过此 Agent。

**A. .pipeline/ 写入（含 Codex 质量门控）**

对每项分诊通过的 Q7-Q10，写入前先检查 Codex 可用性，再执行质量门控：

```bash
# 前置检查（不可用则跳过门控，标记 [未门控]）
which codex > /dev/null 2>&1 || { echo "[未门控] codex not found"; exit 1; }

codex exec \
  -m {主会话模型} \
  --full-auto \
  --ephemeral \
  -C {项目根目录绝对路径} \
  "你是知识库质量核查器。判断拟写入内容是否有对话摘要的事实支撑。
不联网，只基于提供的摘要判断。
只输出一行：PASS 或 FAIL: <一句理由>

=== 对话摘要 ===
{对话摘要}

=== 拟写入内容 ===
{拟写入条目的完整文本}" < /dev/null
```

- `PASS` → 正常写入
- `FAIL` → 写入，但条目开头插入：`> ⚠ [待核查] {理由}`
- 主会话模型不可被 `codex exec` 识别 → 可回退到当前 Codex CLI 可用的最近同级模型，但须在条目或归档报告中标记 `[模型回退] <原因>`
- Codex 不可用（未安装/报错）→ 写入，标记 `[未门控]`

按各 `.pipeline/` 子目录 README.md 格式写入。
**置信度 frontmatter**：写入试点目录（`.pipeline/survey/`、`.pipeline/experiments/`）新文件时加 YAML frontmatter（origin 判定同 Agent 2——文内有 URL/DOI/文献 CitationKey 则 `ai+web`，否则 `ai_only`；`reviewed: false`）。

**B. 冷区降级**

读取 `bigmemory/冷区/.degradation-state.json`（不存在则创建）。

| 文件年龄 | 操作 |
|----------|------|
| 31-90 天 | 添加摘要头 `> [摘要] ...`，保留原文 |
| 91-365 天 | 合并为月度摘要，原文移入 `.archive/` |
| 365+ 天 | 月度摘要合并为年度摘要 |

只处理上次降级到今天之间新跨越阈值的文件。完成后更新 `last_run`。

---

### Step 5: 汇总归档报告

全部 Agent 返回后汇总：

```
=== 归档完成 ===
Agent 执行：并行 Agent ✓ / 主会话 fallback（尝试：...；错误：...）
改动记录：✓ / ✗(原因) / —
踩坑记录：✓ / ✗(原因) / —
调研记录：✓ / ✗(原因) / —
心路历程：✓ / ✗(原因) / —
里程碑：  ✓ / ✗(原因) / —
热区瘦身：状态简报 [N字] | 未关闭决策 [N字] | 近期改动 [N字]
偏好/工作流：✓ 更新 / 无变更
.pipeline/：literature ✓/⚠/— | experiments ✓/⚠/— | survey ✓/⚠/— | terminology ✓/⚠/—
冷区降级：处理 N 个文件 / 无需降级
关联发现：[无 / 描述]
Git 备份：✓ [hash] + 推送 / ✓ [hash] 仅本地 / — 无变更
未纳入文件：[无 / 列表]
```

### Step 6: Git 备份（多窗口安全）

> ⚠ **禁止 `git add .` 或 `git add -A`**，只暂存本窗口实际改过的文件。

1. `git log --oneline -3` 确认 HEAD
2. `git status --short` 检查变更
3. 无变更 → "工作区干净，无需提交"，结束
4. 有变更 → 识别本窗口文件（归档 Agent 写的 + 对话中 Edit/Write 的）
5. `git add <文件列表>`（逐个，不用通配符）
6. `git commit -m "备份：[一句话摘要]"`
7. `git remote -v` → 有远程则 `git push`，无远程则报告仅本地
8. 报告 commit hash
9. 仍有未暂存文件 → 提醒用户

## 不归档的内容

- 纯闲聊、无实质进展的对话
- 已在代码/git 中有充分记录的细节
- 临时调试过程（只记结论）
- 简单格式调整、拼写修正
- 重复信息（冷区已有几乎相同的记录）
- 未经验证的外部引用（AI 已知会编造"看起来合理"的引用）

## 模型选择

- 所有平台：归档 Agent 默认使用主会话模型。
- 能省略 `model` 参数的平台：省略 `model`，让 subagent 继承主会话模型。
- 必须显式传模型的平台：传当前主会话模型；如果无法获知主会话模型，先说明不确定点，再使用平台默认继承方式。
- 禁止默认降级：不得因为归档是“机械写入”而自动改用 sonnet、mini、fast 或其它弱模型。
- Codex App：优先通过工具发现找到 `spawn_agent` 并启动归档 subagent。Codex App subagent 默认不指定模型；若指定模型导致模型解析失败，重试默认 subagent。fallback 只在工具不可用、所有 spawn 尝试失败或平台硬性拒绝时使用，并必须报告原因。

## Kimi Code 适配（2026-07-18，Dr Sun 拍板）

- **subagent 工具**：用内置 `Agent` 工具，同一条消息可并行多个（同类批量任务可用 `AgentSwarm`）。该工具**没有模型参数**；官方文档（kimi.com/code/docs agents.html，2026-07-18 核查）未说明 subagent 使用何种模型，按"继承主会话模型"对待——此为假设，未实证，归档报告中不声明"已用主会话模型"，只写"Kimi Agent 工具（模型继承未实证）"。fallback 规则同 Step 4。
- **质量门控（Agent 4）**：Kimi 的主会话模型 ID 不被 `codex exec` 识别，恒走模型回退路径：回退到当前 Codex CLI 可用的最近同级模型，并在条目或归档报告中标记 `[模型回退] Kimi 主会话模型不被 codex exec 识别`。
- **权限**：官方文档确认 subagent 继承主会话已批准的权限规则；本 skill 需要的 Read/Write/Edit/Grep/Glob/Bash 在 Kimi 默认齐全。
- **frontmatter 兼容**：`user-invocable`/`allowed-tools` 为 Claude 字段，Kimi 忽略不解析，不影响执行；Kimi 必需的 `name`/`description`/`whenToUse` 已在本文件头部，两平台字段并存，不要删除任何一边。

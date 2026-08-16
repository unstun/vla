---
name: codex-dispatch
description: 将任务委派给 Codex CLI (GPT-5.4 xhigh) 执行
version: "2.0"
user-invocable: true
---

# Codex 任务委派

将指定任务委派给 OpenAI Codex CLI 执行。默认使用 GPT-5.4 + xhigh 推理深度。

> **Cursor 规则 (2026-04-27)**：本 skill 仅作为命令模板参考；Cursor 主 session 不直接调用 Codex 插件/Task 代跑。应输出任务包让 Dr Sun 手动输入 Codex CLI, 完成后回贴结果。

## 模型配置

```
CODEX_MODEL=gpt-5.4            # 默认最强模型
CODEX_EFFORT=xhigh              # 推理深度
```

## 适用场景

- 代码生成、调试、安全扫描
- 需要与 Codex 不同视角的第二意见
- 精确的代码修改和重构
- 用户明确要求使用 OpenAI 模型

## 调用方式

交互式任务（Codex 可读写文件）：
```bash
codex exec "<详细任务描述>" 2>&1
```

只读任务（审查/分析）：
```bash
codex exec "<详细任务描述>" --sandbox read-only 2>&1
```

## 输出处理

Codex 输出通常含 exec 日志，提取最终结论部分展示给 Dr Sun。标注"以下来自 Codex (GPT-5.4)"。

## 注意

- Codex 自动读取项目文件和 AGENTS.md/AGENTS.md 上下文
- 超时设 120 秒，复杂任务可能更长
- 大输出（>50KB）需读取 persisted output 文件提取结论

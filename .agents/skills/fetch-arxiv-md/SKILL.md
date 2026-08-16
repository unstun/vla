---
name: fetch-arxiv-md
description: 从 arXiv ID 拉 e-print 源码并用 pandoc 转为 LLM 友好的 Markdown。用户说"把 arXiv XXXX.XXXXX 转 md"、"批量转论文"、"这论文怎么让 AI 读"时触发。产物按 CitationKey 存入 `docs/research/papers/md/`。
---

# fetch-arxiv-md

把 arXiv 论文转成 AI 可读 Markdown 的本地 skill。脚本路径相对项目根目录为 `.agents/skills/fetch-arxiv-md/`。

## 背景

直接喂 PDF 给 LLM 会严重稀释 context（图像化布局、噪声 metadata、token 低密度）。Pandoc 从 arXiv 原始 LaTeX 源码转 Markdown：
- 公式用 `$...$`/`$$...$$` 原生保留
- 引用 `[@citation_key]` 完整
- 图表抽取到 `<CitationKey>_figs/`，PDF/EPS 栅格化为 PNG（150 dpi），md 路径自动重写
- token 量约为 LaTeX 源的 40-60%，远优于 PDF OCR

本项目沿用“arXiv LaTeX 源 → Pandoc Markdown”的转换约定；转换结果仍需与论文原文核对。

## 触发条件

- Dr Sun 说"把这 5 篇转 md"、"batch 转 arXiv 论文"
- AI 准备精读论文前（尤其论文数 >= 2 时）
- 新入库 PDF 需建立 AI 可读副本

## 执行

### 单篇

```bash
bash .agents/skills/fetch-arxiv-md/fetch.sh <arxiv_id> <citation_key>
# 例: bash .agents/skills/fetch-arxiv-md/fetch.sh 2309.14341 Cheng2024ExtremeParkour
```

### 批量（从 PDF 自动提 arXiv ID）

```bash
bash .agents/skills/fetch-arxiv-md/batch.sh
# 扫描 1_survey/papers/*.pdf，自动提 arXiv ID + 从 index.md 查 CitationKey，全部转换
```

## Pandoc 参数说明

```
-f latex                              # 输入 LaTeX
-t markdown+tex_math_dollars-raw_html-raw_tex
                                      # 输出 markdown；公式用 $...$；禁内联 HTML/raw tex
--wrap=none                           # 不强制折行（保持原段落结构）
```

**为何选此组合**（2026-04-20 Pandoc 3.9 实测，以 Cheng2024 为样本）：

| 格式 | 公式 | 引用 `[@key]` | token 估算 |
|------|------|---------------|-----------|
| 默认 `markdown` | HTML span（冗余） | ✓ 保留 | 7462 |
| `gfm+tex_math_dollars` | `$\`..\`$` 混合 | ✗ 被剥离 | 7254 |
| **`markdown+tex_math_dollars-raw_html-raw_tex`** | `$...$` 纯 | ✓ 保留 | **7376** |

## 约束

- 依赖：pandoc >= 3.0, curl, tar (macOS 自带), **pdftoppm**（poppler，`brew install poppler`），**ghostscript**（可选，只有 EPS 图时才需，`brew install ghostscript`）
- arXiv ID 源：PDF 首页的 `arXiv:XXXX.XXXXX`（用 pdftotext 提）→ fallback literature/index.md DOI 列
- 无源码论文（作者只上传 PDF）→ 脚本返回 `source-pdf-only`，需 fallback 到 MinerU（本 skill 暂不实现）
- 产物路径：
  - 正文：`docs/research/papers/md/<CitationKey>.md`（MUST 与 CitationKey 对齐）
  - 图片：`docs/research/papers/md/<CitationKey>_figs/*.{png,jpg,jpeg,gif}`（PDF/EPS 统一转 PNG）
- 临时目录：`/tmp/arxiv-fetch/<arxiv_id>/`（可复用缓存 e-print）

## 踩坑记录

- **arXiv e-print 可能是 `.tar.gz` / `.gz` 单 tex / `.pdf`**：脚本用 `file` 命令判断，分别处理
- **主 tex 查找**：用 `\documentclass` grep，多个候选时取第一个
- **图片处理（2026-04-20 v2 升级）**：
  - 源包内所有 `*.png/jpg/jpeg/gif` 直接 copy；`*.pdf` 用 `pdftoppm -png -r 150 -singlefile` 栅格化；`*.eps` 用 `gs` 栅格化（缺 gs 则 skip 并 warning）
  - md 里 `![](figures/xxx.pdf)` 等引用统一重写为 `<CitationKey>_figs/<basename>.png`（pdf/eps）或 `.<原ext>`（bitmap）
  - 以 basename 为唯一键，若源包同名覆盖后出现（实测 5 篇无冲突）
  - _figs/ 里可能有未被 md 引用的源包"散图"（logo、附录未引用图），不自动清理——体积代价 < 重跑风险
- **图片引用正则 delimiter**：`perl -i -pe 's#...#...#'` 用 `#` 而非 `|`，避免和 `(pdf|eps)` 的分支 `|` 冲突（原 `s|...|...|` 报 Unmatched `(`）
- **Perl regex 吞路径**：`([^)]*/)?` 贪婪匹配最后一个 `/`，确保 `a/b/c/xxx.pdf` 的 basename 提取正确
- **Perl 正则变量 escape**：bash 双引号里 `\$1` 保留为 perl 的反向引用，`${CITATION_KEY}` 让 bash 展开
- **bibliography**：arXiv 源通常含 `.bib` 或 `.bbl`，本 skill 不做解析，引用保留为 `[@citation_key]` 占位符

## 验证

转换完毕后检查：
```bash
head -30 docs/research/papers/md/<CitationKey>.md  # 章节结构
grep -c '^#' docs/research/papers/md/<CitationKey>.md  # 章节数量
grep -cE '\$[^\$]+\$' docs/research/papers/md/<CitationKey>.md  # 公式数量
wc -c docs/research/papers/md/<CitationKey>.md  # 大小
```

#!/bin/bash
# ==============================================================================
# batch.sh: 扫描 docs/research/papers/*.pdf，自动提 arXiv ID + CitationKey，批量转 md
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd)}"
PAPERS_DIR="$PROJECT_ROOT/docs/research/papers"

cd "$PAPERS_DIR"

FAILED=()
SUCCEEDED=()

for pdf in *.pdf; do
    [ -f "$pdf" ] || continue

    # CitationKey = 文件名去 .pdf 去 _<ShortTitle> 前缀部分；此处直接用去 .pdf 作为 key
    # 因为 docs/research/papers/ 下 PDF 文件名就是 AuthorYear_ShortTitle.pdf，截到第一个 _
    # 但我们的 CitationKey 不含下划线，从 index.md 查更准确——此处先用 AuthorYear 前缀
    BASE="${pdf%.pdf}"

    # 从 literature/index.md 查 CitationKey（第一列），优先按作者+年份前缀匹配
    AUTHOR_YEAR="${BASE%%_*}"  # 取第一个 _ 之前（例如 Cheng2024）
    CITATION_KEY=$(awk -F'|' -v prefix="$AUTHOR_YEAR" \
        '$2 ~ prefix {gsub(/^ +| +$/,"",$2); print $2; exit}' \
        "$PROJECT_ROOT/.pipeline/literature/index.md" 2>/dev/null || true)

    # fallback：取文件名第一段 (AuthorYear)
    CITATION_KEY="${CITATION_KEY:-$AUTHOR_YEAR}"

    # 从 PDF 首页提 arXiv ID
    ARXIV_ID=$(pdftotext -f 1 -l 1 "$pdf" - 2>/dev/null \
        | grep -oE 'arXiv:[0-9]+\.[0-9]+' \
        | head -1 \
        | sed 's/arXiv://')

    if [ -z "$ARXIV_ID" ]; then
        echo "[$BASE] ⚠ 未提到 arXiv ID，跳过" >&2
        FAILED+=("$BASE (no arxiv id)")
        continue
    fi

    echo "=== $BASE → $CITATION_KEY (arXiv:$ARXIV_ID) ==="
    if bash "$SCRIPT_DIR/fetch.sh" "$ARXIV_ID" "$CITATION_KEY"; then
        SUCCEEDED+=("$CITATION_KEY")
    else
        FAILED+=("$CITATION_KEY ($ARXIV_ID, exit=$?)")
    fi
    echo
done

echo
echo "==================== 汇总 ===================="
echo "成功 (${#SUCCEEDED[@]}):"
for s in "${SUCCEEDED[@]:-}"; do [ -n "$s" ] && echo "  ✓ $s"; done
echo "失败 (${#FAILED[@]}):"
for f in "${FAILED[@]:-}"; do [ -n "$f" ] && echo "  ✗ $f"; done

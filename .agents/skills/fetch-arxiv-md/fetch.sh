#!/bin/bash
# ==============================================================================
# fetch-arxiv-md: 单篇 arXiv 论文 tex → md 转换
# 用法: fetch.sh <arxiv_id> <citation_key>
# 输出: docs/research/papers/md/<citation_key>.md
# ==============================================================================

set -euo pipefail

if [ $# -lt 2 ]; then
    echo "用法: $0 <arxiv_id> <citation_key>" >&2
    echo "示例: $0 2309.14341 Cheng2024ExtremeParkour" >&2
    exit 1
fi

ARXIV_ID="$1"
CITATION_KEY="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd)}"
WORK_DIR="${WORK_DIR:-/tmp/arxiv-fetch/$ARXIV_ID}"
OUT_DIR="$PROJECT_ROOT/docs/research/papers/md"

mkdir -p "$WORK_DIR" "$OUT_DIR"

# ------------------------------ 1. 下载 e-print ------------------------------
if [ ! -s "$WORK_DIR/source.archive" ]; then
    echo "[$CITATION_KEY] 下载 https://arxiv.org/e-print/$ARXIV_ID ..."
    curl -sSL -A "Mozilla/5.0 fetch-arxiv-md" \
        "https://arxiv.org/e-print/$ARXIV_ID" \
        -o "$WORK_DIR/source.archive"
else
    echo "[$CITATION_KEY] 命中缓存 $WORK_DIR/source.archive"
fi

FTYPE=$(file -b "$WORK_DIR/source.archive")
echo "[$CITATION_KEY] 格式: $FTYPE"

# --------------------------- 2. 解压到 extract 目录 --------------------------
rm -rf "$WORK_DIR/extract"
mkdir -p "$WORK_DIR/extract"

case "$FTYPE" in
    *gzip*compressed*)
        # 可能是 tar.gz 或单文件 .gz
        if tar -tzf "$WORK_DIR/source.archive" >/dev/null 2>&1; then
            tar -xzf "$WORK_DIR/source.archive" -C "$WORK_DIR/extract"
        else
            gunzip -c "$WORK_DIR/source.archive" > "$WORK_DIR/extract/main.tex"
        fi
        ;;
    *PDF*document*)
        echo "[$CITATION_KEY] ⚠ 仅 PDF（无 tex 源码）— source-pdf-only" >&2
        exit 2
        ;;
    *"POSIX tar archive"*)
        tar -xf "$WORK_DIR/source.archive" -C "$WORK_DIR/extract"
        ;;
    *)
        echo "[$CITATION_KEY] ⚠ 未知格式: $FTYPE" >&2
        exit 3
        ;;
esac

# ---------------------------- 3. 定位主 tex 文件 -----------------------------
# 找首个含 \documentclass 的 tex（arXiv 主论文惯例）
MAIN_TEX=$(grep -rl '\\documentclass' "$WORK_DIR/extract" --include='*.tex' 2>/dev/null | head -1)

if [ -z "$MAIN_TEX" ]; then
    echo "[$CITATION_KEY] ⚠ 未找到 \\documentclass 的主 tex" >&2
    ls -la "$WORK_DIR/extract" >&2
    exit 4
fi

echo "[$CITATION_KEY] 主 tex: $MAIN_TEX"

# ----------------------------- 4. Pandoc 转 md -----------------------------
MAIN_DIR=$(dirname "$MAIN_TEX")
MAIN_FILE=$(basename "$MAIN_TEX")
OUT_FILE="$OUT_DIR/$CITATION_KEY.md"

(
    cd "$MAIN_DIR"
    pandoc "$MAIN_FILE" \
        --from=latex \
        --to='markdown+tex_math_dollars-raw_html-raw_tex' \
        --wrap=none \
        --output="$OUT_FILE" \
        2> "$WORK_DIR/pandoc.log" || {
            echo "[$CITATION_KEY] ⚠ Pandoc 报错:" >&2
            tail -10 "$WORK_DIR/pandoc.log" >&2
            exit 5
        }
)

# ---------------------- 4.5 抽图 + 栅格化 PDF + 路径重写 -----------------------
# 目标：让 md 里的 ![](figures/xxx.pdf) 真正可读
# - PNG/JPG/JPEG/GIF 直接 copy 到 <key>_figs/
# - PDF → pdftoppm 150dpi 转 PNG 到 <key>_figs/
# - EPS  → ghostscript 兜底（无 gs 则跳过并 warning）
# - md 里引用路径统一重写为 <key>_figs/<basename>.<ext>（pdf/eps → png）

FIGS_DIR="$OUT_DIR/${CITATION_KEY}_figs"
rm -rf "$FIGS_DIR"
mkdir -p "$FIGS_DIR"

BITMAP_COUNT=0
PDF_COUNT=0
EPS_COUNT=0
EPS_SKIP=0

while IFS= read -r -d '' IMG; do
    BN=$(basename "$IMG")
    STEM="${BN%.*}"
    EXT_LC=$(echo "${BN##*.}" | tr '[:upper:]' '[:lower:]')
    case "$EXT_LC" in
        png|jpg|jpeg|gif)
            cp "$IMG" "$FIGS_DIR/$BN"
            BITMAP_COUNT=$((BITMAP_COUNT+1))
            ;;
        pdf)
            if pdftoppm -png -r 150 -singlefile "$IMG" "$FIGS_DIR/$STEM" 2>/dev/null; then
                PDF_COUNT=$((PDF_COUNT+1))
            else
                echo "[$CITATION_KEY] ⚠ pdftoppm 失败: $IMG" >&2
            fi
            ;;
        eps)
            if command -v gs >/dev/null 2>&1; then
                gs -sDEVICE=png16m -r150 -dSAFER -dBATCH -dNOPAUSE \
                    -sOutputFile="$FIGS_DIR/$STEM.png" "$IMG" >/dev/null 2>&1 \
                    && EPS_COUNT=$((EPS_COUNT+1)) \
                    || EPS_SKIP=$((EPS_SKIP+1))
            else
                EPS_SKIP=$((EPS_SKIP+1))
            fi
            ;;
    esac
done < <(find "$WORK_DIR/extract" -type f \( \
    -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' -o \
    -iname '*.gif' -o -iname '*.pdf' -o -iname '*.eps' \
    \) -print0)

# md 内图片引用路径重写
# pdf/eps → png（因已转栅格），其它保留扩展名；目录前缀统一改 <key>_figs/
perl -i -pe "s#!\[([^\]]*)\]\(([^)]*/)?([^/)]+)\.(pdf|eps)\)#![\$1](${CITATION_KEY}_figs/\$3.png)#gi" "$OUT_FILE"
perl -i -pe "s#!\[([^\]]*)\]\(([^)]*/)?([^/)]+)\.(png|jpg|jpeg|gif)\)#![\$1](${CITATION_KEY}_figs/\$3.\$4)#gi" "$OUT_FILE"

# 若 <key>_figs/ 里没东西就清掉目录（纯文本论文）
if [ -z "$(ls -A "$FIGS_DIR" 2>/dev/null)" ]; then
    rmdir "$FIGS_DIR" 2>/dev/null || true
fi

echo "[$CITATION_KEY] 图片: bitmap=$BITMAP_COUNT pdf→png=$PDF_COUNT eps→png=$EPS_COUNT eps_skip=$EPS_SKIP"

# ------------------------------- 5. 追加元信息头 --------------------------------
# 在 md 开头插入 yaml frontmatter（origin=ai+web, reviewed=false）
TMP=$(mktemp)
cat > "$TMP" <<EOF
---
citation_key: $CITATION_KEY
arxiv_id: $ARXIV_ID
arxiv_url: https://arxiv.org/abs/$ARXIV_ID
source: arxiv-e-print
converter: pandoc-3.9 markdown+tex_math_dollars-raw_html-raw_tex
converted_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)
origin: ai+web
reviewed: false
---

EOF
cat "$OUT_FILE" >> "$TMP"
mv "$TMP" "$OUT_FILE"

# ---------------------------------- 6. 报告 ----------------------------------
SIZE=$(wc -c < "$OUT_FILE")
LINES=$(wc -l < "$OUT_FILE")
SECTIONS=$(grep -c '^# ' "$OUT_FILE" || true)
FORMULAS=$(grep -cE '\$[^\$]+\$' "$OUT_FILE" || true)

FIG_FILES=$(ls -1 "$FIGS_DIR" 2>/dev/null | wc -l | tr -d ' ')

echo "[$CITATION_KEY] ✓ $OUT_FILE"
echo "  size=${SIZE}B lines=$LINES sections=$SECTIONS inline_math=$FORMULAS est_tokens=$((SIZE/4)) figs=$FIG_FILES"

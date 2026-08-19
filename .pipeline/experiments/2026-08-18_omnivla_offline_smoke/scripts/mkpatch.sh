#!/usr/bin/env bash
# mkpatch.sh <patch-name-without-number> <relpath> [relpath...]
#
# Creates the next numbered patch in patches/ as a unified diff of the current
# working copy against "pristine snapshot + all patches already in patches/".
# This keeps the series strictly ordered and re-appliable by make_workcopy.sh.
set -eo pipefail

ROOT=/Users/sun/tongbu/study/phdproject/vla
TP="$ROOT/third_party/2026-08-18_omnivla_5182600"
EXP="$ROOT/.pipeline/experiments/2026-08-18_omnivla_offline_smoke"
WORK="$EXP/work/OmniVLA"
REF="$EXP/work/.patch_reference"

name="$1"; shift
shopt -s nullglob
existing=("$EXP"/patches/[0-9][0-9][0-9][0-9]-*.patch)
n=$(printf "%04d" $(( ${#existing[@]:-0} + 1 )))
out="$EXP/patches/${n}-${name}.patch"

# reference tree = pristine + patches already recorded
rm -rf "$REF"; cp -R "$TP/OmniVLA" "$REF"
for p in ${existing[@]+"${existing[@]}"}; do ( cd "$REF" && patch -p1 --no-backup-if-mismatch < "$p" >/dev/null ); done

: > "$out"
for rel in "$@"; do
  diff -u --label "a/$rel" --label "b/$rel" "$REF/$rel" "$WORK/$rel" >> "$out" || true
done
rm -rf "$REF"

if [ ! -s "$out" ]; then
  echo "mkpatch: no differences for: $* — nothing written" >&2
  rm -f "$out"; exit 1
fi
echo "wrote $out"
wc -l < "$out"

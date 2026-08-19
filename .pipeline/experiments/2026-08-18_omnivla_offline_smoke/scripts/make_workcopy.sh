#!/usr/bin/env bash
# Rebuild the OmniVLA working copy from the pristine pinned snapshot.
#
#   work/OmniVLA  ==  third_party/2026-08-18_omnivla_5182600/OmniVLA  +  patches/*.patch
#
# The pristine tree is never edited: upstream scripts write output images into
# their own tree and `pip install -e .` creates *.egg-info there, so all
# execution happens in this disposable, git-ignored copy. Idempotent.
set -euo pipefail

ROOT=/Users/sun/tongbu/study/phdproject/vla
TP="$ROOT/third_party/2026-08-18_omnivla_5182600"
EXP="$ROOT/.pipeline/experiments/2026-08-18_omnivla_offline_smoke"
WORK="$EXP/work/OmniVLA"

echo "[make_workcopy] verifying pristine snapshot integrity"
( cd "$TP/OmniVLA" && shasum -a 256 -c ../SOURCE_MANIFEST.sha256 2>&1 | grep -v ': OK$' ) && {
  echo "[make_workcopy] FATAL: pristine snapshot does not match SOURCE_MANIFEST.sha256" >&2
  exit 1
} || true

echo "[make_workcopy] recreating $WORK"
rm -rf "$WORK"
mkdir -p "$EXP/work"
cp -R "$TP/OmniVLA" "$WORK"

shopt -s nullglob
patches=("$EXP"/patches/[0-9][0-9][0-9][0-9]-*.patch)
if [ ${#patches[@]} -eq 0 ]; then
  echo "[make_workcopy] no patches to apply"
else
  for p in "${patches[@]}"; do
    echo "[make_workcopy] applying $(basename "$p")"
    ( cd "$WORK" && patch -p1 --no-backup-if-mismatch < "$p" )
  done
fi

# Checkpoint locations expected by the upstream scripts, as plain relative paths
# from the repository root ("./omnivla-edge", "./omnivla-original"). Symlinks are
# used instead of a patch so the upstream path strings stay untouched.
for name in omnivla-edge omnivla-original; do
  if [ -d "$TP/checkpoints/$name" ]; then
    ln -sfn "$TP/checkpoints/$name" "$WORK/$name"
    echo "[make_workcopy] linked ./$name -> $TP/checkpoints/$name"
  else
    echo "[make_workcopy] checkpoint $name not present locally, no link created"
  fi
done

echo "[make_workcopy] done: $WORK"
echo "[make_workcopy] patches applied: ${#patches[@]}"

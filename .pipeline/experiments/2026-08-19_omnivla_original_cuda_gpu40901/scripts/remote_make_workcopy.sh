#!/usr/bin/env bash
# Rebuild the remote working copy from the pristine pinned snapshot:
#   work/OmniVLA == pristine/OmniVLA + patches_edge/*.patch + patches_original/*.patch
# The pristine copy is never edited; every local modification is a tracked patch
# file in the local repository (AGENTS.md sync gate). Idempotent.
set -euo pipefail
REMOTE=/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_original_cuda
cd "$REMOTE"

echo "[make_workcopy] verifying pristine snapshot against SOURCE_MANIFEST.sha256"
( cd pristine/OmniVLA && sha256sum -c ../../SOURCE_MANIFEST.sha256 > "$REMOTE/verify/remote_source_manifest.txt" 2>&1 )
bad=$(grep -vc ': OK$' "$REMOTE/verify/remote_source_manifest.txt" || true)
ok=$(grep -c ': OK$' "$REMOTE/verify/remote_source_manifest.txt")
echo "[make_workcopy] manifest: $ok OK, $bad not-OK"
[ "$bad" -eq 0 ] || { echo "[make_workcopy] FATAL: pristine snapshot mismatch" >&2; exit 1; }

rm -rf work/OmniVLA
mkdir -p work
cp -a pristine/OmniVLA work/OmniVLA

shopt -s nullglob
for p in patches_edge/[0-9][0-9][0-9][0-9]-*.patch patches_original/[0-9][0-9][0-9][0-9]-*.patch; do
  echo "[make_workcopy] applying $p"
  ( cd work/OmniVLA && patch -p1 --no-backup-if-mismatch < "$REMOTE/$p" )
done

# Checkpoint locations as the plain relative paths the upstream scripts expect.
for name in omnivla-edge omnivla-original; do
  if [ -d "$REMOTE/checkpoints/$name" ]; then
    ln -sfn "$REMOTE/checkpoints/$name" "work/OmniVLA/$name"
    echo "[make_workcopy] linked ./$name -> $REMOTE/checkpoints/$name"
  else
    echo "[make_workcopy] checkpoint $name not present yet, no link created"
  fi
done

echo "[make_workcopy] files differing from pristine:"
diff -rq pristine/OmniVLA work/OmniVLA || true
echo "[make_workcopy] done"

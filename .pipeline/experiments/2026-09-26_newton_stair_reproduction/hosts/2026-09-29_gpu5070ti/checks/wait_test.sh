#!/bin/bash
# Port review round 4, N28 (c) and (d): what the runner's abort handler relies on in gpu5070ti's bash. Does a second
# `wait` on a background pid return its status again? Does bash reap an exited background child by itself, so that
# `kill -0` fails? Does a TERM handler that runs after the main `wait` returned still get the status from `wait`?
set -uo pipefail
echo "bash $BASH_VERSION"
# 1: a second wait on a pid whose status the first wait already returned
bash -c 'exit 3' & p=$!
wait "$p"; echo "case1 first wait=$?"
wait "$p"; echo "case1 second wait=$?"
# 2: a child that exits while the shell is busy elsewhere: reaped asynchronously? then wait
bash -c 'exit 5' & p=$!
sleep 0.5
if kill -0 "$p" 2>/dev/null; then echo "case2 kill -0 succeeds (not reaped yet)"; else echo "case2 kill -0 fails (reaped asynchronously)"; fi
wait "$p"; echo "case2 wait=$?"
wait "$p"; echo "case2 second wait=$?"
# 3: the same inside a TERM trap handler that runs after the main wait has returned
trap 'h' TERM
h() { trap "" TERM; echo "case3 in handler, entry status $?"; wait "$q"; echo "case3 handler wait=$?"; exit 0; }
bash -c 'exit 7' & q=$!
wait "$q"; kill -TERM $$; echo "case3 not reached"

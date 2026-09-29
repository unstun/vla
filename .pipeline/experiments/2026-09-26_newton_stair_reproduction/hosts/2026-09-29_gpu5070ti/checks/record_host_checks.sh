#!/bin/bash
# Re-run P1 and the shim's network and user-namespace tests on gpu5070ti with every output saved (port review round 1,
# B2: their first runs printed only). Usage: record_host_checks.sh <attempt>; writes checks_out/*_attemptNN.* in the
# port directory of the execution copy. Refuses to overwrite.
set -euo pipefail
export PATH=$HOME/vla_exec/bin:$PATH
E=$HOME/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction
H=$E/hosts/2026-09-29_gpu5070ti
N=$(printf %02d "$1")
O=$H/checks_out
mkdir -p "$O"
for f in "$O/p1_gates_attempt$N.json" "$O/net_test_attempt$N.txt" "$O/keepid_test_attempt$N.txt"; do test ! -e "$f"; done
"$HOME/vla_exec/envs/newton_worker/bin/python" "$H/checks/p1_gates.py" > "$O/p1_gates_attempt$N.json"
bash "$H/checks/net_test.sh" > "$O/net_test_attempt$N.txt" 2>&1
F=$HOME/vla_exec/vla/.pipeline/experiments/2026-09-27_lite3_factory_runtime_audit
ARM=sha256:1c102582b40d5305e310788c79e963e4b6cde13aea2bc5db3b7c1800e821935d
{
  echo "shim: $(sha256sum "$(command -v docker)")"
  head -3 /proc/sys/fs/binfmt_misc/qemu-aarch64
  docker create -i --pull never --name "vla-port-keepid-$N" --network none --read-only --cap-drop ALL \
    --security-opt no-new-privileges --memory 1g --cpus 1 --pids-limit 64 --user "$(id -u):$(id -g)" \
    --tmpfs /tmp:rw,exec,nosuid,nodev,size=64m --mount "type=bind,src=$F/private_snapshot,dst=/snapshot,readonly" \
    --entrypoint /bin/sh "$ARM" -c 'uname -m; id; head -c 4 /snapshot/lib/ras_lib/libdeepras.so | od -An -c; test -r /snapshot/deps/libtorch_cpu.so && echo libtorch-readable; touch /snapshot/x 2>&1 | head -1' >/dev/null
  docker start -ai "vla-port-keepid-$N"; echo "start exit=$?"
  docker rm -f "vla-port-keepid-$N" >/dev/null
} > "$O/keepid_test_attempt$N.txt" 2>&1
sha256sum "$O"/*_attempt"$N".*

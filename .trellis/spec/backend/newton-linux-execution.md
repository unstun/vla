# Newton Linux execution

## 1. Scope and trigger

On 2026-10-09 Dr Sun moved builds, simulation and analysis to gpu5070ti.
This supersedes the earlier Mac-only execution exception. The local repository
remains authoritative. v123/v124 own the host port; native comparison variants
remain v114 (baseline) and v122 (diagnostics). v125 repairs concurrent ROS log
directory creation and Linux writer inspection. No hardware actuation is authorized.

## 2. Signatures

`versions/v125/run_remote_corner.py --variant {baseline,candidate} --attempt N`
runs one bounded 90-second original Building corner episode. Execute with
`/home/sun/vla_exec/envs/newton_worker/bin/python` on gpu5070ti, from the verified
copy at `/data/sun/vla_mppi_20261009/repo`. `freeze_host.py verify` checks the
source/snapshot pairs and explicit runtime-input manifest before execution.

## 3. Contracts

Bulk and outputs live below `/data/sun/vla_mppi_20261009`; the system disk is
separate and had only 3.3 GB free at preflight. Local returns use an explicit
allowlist. Never recursively download raw captures or build trees.

`V125_VARIANT` chooses only the tested native install. `V125_BUILD_EVIDENCE`
points to a receipt bound by `quality.json`. The gate checks platform, variant,
Docker image identity and every source/install hash. ARM64 Mac receipts cannot
qualify an x86_64 rebuild. Baseline/candidate must use the same host environment.

Preserve CPU Newton physics, factory-PD-RL startup, original geometry, sensor
timestamps and all validity/stop gates. The task-owned Docker wrapper delegates
only the pinned ARM factory image and its owned container names to the existing
rootless Podman shim; native Foxy uses Docker. Native ROS network/domain and
loopback IPC remain isolated from hardware drivers. Linux `ru_maxrss` is KiB;
convert to bytes before retaining the inherited byte-named evidence field.

Prepare ROS_LOG_DIR before concurrent ROS initialization: the direct 12-process
reproduction failed 3/12 without it and 0/12 with it. Use the host UID/GID for
native ROS and its applied-state tmpfs, and preserve the original 8 MiB limit.
The scoped lsof wrapper skips stat only for Docker-internal overlay and network
namespace mounts; requested run files remain inspected. Real host and container
writer tests must both detect open writers and accept a closed file. Other lsof
errors still reject archive pruning.

## 4. Validation and error matrix

| Condition | Required behavior |
|---|---|
| Source, variant, image or installed file differs | Reject launch |
| Existing run ID, file or unrelated prepared directory | Reject; preserve it |
| Docker would create missing output parents as root | Pre-create the empty owned directory chain before mounting |
| Container or host cannot write its own output | Fail the ownership test before physics |
| Native tests pass | Component evidence only |
| Physics/mission fails | Keep raw failure evidence; no navigation acceptance |

## 5. Cases

Good: create `runs/<id>/artifacts/external_episode` as the invoking user before
the tmpfs mount, then retain the original prepared-mount rejection checks.
Base: use a new attempt ID with unchanged frozen source.
Bad: chmod an entire shared directory, delete failed attempts, or edit a frozen
host version after a runtime failure. v123's first attempt failed before physics
on output ownership; v124 records that one host fix.

## 6. Required tests

`test_host_port.py` compares physics, scenario and planner parameter bytes with
the original parent and rejects mismatched receipt/variant/image identities.
`test_output_ownership.py` uses a real Docker tmpfs to verify host request and
retention writes plus native state writes and live-writer detection.
`test_native_graph.py` starts the real 10-child ROS graph for 10 seconds with
the original baseline install, without physics, and rejects a child exception.
These tests pass on gpu5070ti. Native
baseline and candidate builds each passed 36 component tests. Physical acceptance
must be obtained from the separate actual run artifacts, not these tests.

## 7. Wrong versus correct

Wrong: compare Mac and Linux solve times and credit the algorithm for the gap.
Correct: use paired same-host runs and report diagnostic coverage separately
from task success, timing and physical behavior. A rejected target candidate
inside a successful round is not a failed planning round; observation freshness
recorded at a rejection is context, not proof of the root cause.

## Step-2 execution binding (v126, 2026-10-10)

For step 2, baseline means retained native v122 at `/task/candidate/install`,
not the earlier v114 `/task/baseline/install`. The candidate is v126 at
`/task/step2_v126/install`. Its `V126_VARIANT`, `V126_BUILD_EVIDENCE` and
`V126_NATIVE_CONTAINER` use new receipts under `results/step2_v126`.
`versions/v126/run_comparison.py --variant {baseline,candidate} --attempt N`
verifies frozen inputs, waits for existing loopback ports to become available,
runs one bounded episode, then analyzes only the closed capture. New trial IDs
are mandatory; there is no port-reuse or timeout relaxation. `test_native_graph`
must source the actual candidate install and save evidence to the step directory.
The inherited v114 graph preflight alone cannot qualify the new candidate.

## gpu40901 continuation: v234 migration and v235 single trial

### Scope / trigger

Dr Sun authorized the move to gpu40901 on2026-10-17. v234 reconstructs the
exact317-file v232 native source; v235 binds the full physical entry. Original
5070Ti install-byte comparison and historical126324+3 replay remain optional
audits. They do not block a source-verified rebuild with new-host offline gates.

### Signatures

Use `versions/v235/launch.py --preflight-only`, then `launch.py` for the one
authorized physical attempt, with the private Python under
`/home/ubuntu/sun/vla_v234_20261017/env/newton_worker/bin/python` and private
v234/bin before v233/bin on PATH. `--episode` is the supervised child entry.

### Contracts

The local repository remains authoritative. Bind the rebuilt native receipt,
all14 package prefixes, original policy, original route and generated profile.
The create-exclusive `evidence/v235_physical_launch_once.json` records the
single full-route invocation. Native execution uses4 CPUs/6GiB/shares128;
host physics uses2 CPUs/nice19 and no CUDA. These caps are an execution choice,
not evidence that sensor deadlines or physical performance will pass.

### Validation / error matrix

| Condition | Evidence / behavior |
|---|---|
| Source/install/profile/actual graph pass | Offline readiness only |
| Preflight socket is still in TIME_WAIT | Wait for release; never kill a foreign process |
| Captured scanner misses the original0.1s period | Preserve the exception and failed attempt; do not relax the period |
| Recorder exits before result/finish | Keep both absent; report partial physics and no arrival |
| Global lsof emits inaccessible-mount warnings | Retain originals; a verified non-pruning snapshot is permitted |

### Good / base / bad cases

v235 passes the12s graph/profile gate but stops with a scanner deadline
exception; the last retained frame is12.801543235778809s and no navigation
goal was sent. Full-route,45–55s stairs and terminal PD are untested. A partial
recorded-state video may show the failure without creating a source result.

### Tests and assertion points

Verify the actual generated profile, all source/install hashes and the real
graph before physics. Check exact source-state indices/times, zero render
physics, full MP4 decode and input hashes for partial video. A warm zero-step
scan and static graph do not establish deadline headroom under concurrent
physical execution; separate scanner timing evidence is needed for diagnosis.

### Wrong / correct

Wrong: infer physical readiness from165 passing native cases, synthesize a
FINISHED result for a partial capture, or automatically rerun a one-shot test.
Correct: preserve the failed physical attempt, original missing result/finish,
honest comparison video and independently passing offline gates.

## Step-3 execution binding (v127, 2026-10-10)

v126 remains parked. Step 3 starts from native v122 and host v125; use new
`V127_*` environment keys, `results/step3_v127` receipts and
`/task/step3_v127/install`. The baseline remains `/task/candidate/install`.
`versions/v127/run_comparison.py` runs the bounded pair entry unchanged.
The candidate source audit must show the complete v122 retry chain preserved.
For validator comparison, keep JSONL verdict files separate from merged ROS
stdout/stderr: fragmented stream insertion can interleave with diagnostic lines.
Logs remain evidence but are not the canonical structured comparison records.

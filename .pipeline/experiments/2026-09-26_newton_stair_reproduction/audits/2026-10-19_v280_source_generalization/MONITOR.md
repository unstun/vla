# Final state — delivery complete

All ten formal attempts and all postprocessing are complete. All ten full videos
and462 compact artifacts are returned and SHA-verified locally. The automation
is PAUSED; the owned resource probe has exited after its stop marker. No further
physical run or analysis restart is needed. Selected baseline remainsv232/v233.
See RESULTS.md, physical_table.csv and delivered/README.md. Historical status
notes below are retained only as provenance.

# Resource watch and once-only physical continuation

User authorization: inspect resources autonomously and proceed with the already
approved ten representative routes; do not interfere with unrelated workloads.

Local source of truth: `/Users/sun/tongbu/study/phdproject/vla`.
Remote execution root: `/data/sun/vla_mppi_20261009` on `gpu5070ti`.
The remote repository has the same relative paths under that root's `repo/`.

The read-only resource watch runs every 60 seconds (initial PID 1212104).
`results/resource_watch/latest.json` and `samples.jsonl` record its actual
timestamp, PID, gate identity, memory, GPU compute jobs and output disk.
The gate is inherited unchanged: 20 GiB available RAM, no GPU compute process,
10 GiB free output disk. Only the disk target is the actual larger /home output
filesystem. A stale timestamp is not evidence of a live watcher.

All ten zero-step preflights completed. A04 invocation01's resource failure is
retained; A04 invocation02 and the other nine invocation01 checks passed.
The common v282 execution identity is frozen and has been verified locally.

Formal runner initial PID: 1220154. Inspect `results/physical_batch_status.json`
and `results/physical_batch01.log`. `run_physical.py` holds an exclusive flock;
it waits for the resource gate before each route and never retries an existing
formal ledger. Five resume-contract unit tests pass. An interrupted formal
ledger or partial task directory requires inspection, not deletion or rerun.

Authoritative per-case once-only ledger:
`/data/sun/vla_mppi_20261009/generalization_v282/<CASE>/execution/physical_launch_once.json`.
Actual captures:
`/home/sun/vla_exec/physical_runs_v282/v282_<CASE>_attempt01/`.
Order: A04, G05, CU06, D07, S04, CD12, CM02, CM07, CS03, CE03.
Do not render or transfer large files during physics. Every failed actual attempt
remains part of the final table and receives its available full-prefix video.

After the batch closes, use `postprocess_all.py` / `postprocess_case.py`, then
return compact hash-verified evidence and real complete MP4s to local `delivered/`.
Analysis/render retries may repair tooling without re-running physics. The
actual native body-margin scorer and profile configuration were smoke-tested;
full physical postprocessing still needs execution.

The current-thread heartbeat `continue-building-validation-when-5070ti-is-free`
checks every ten minutes. Stay quiet on unchanged waiting/running state. Report
completion or actionable failures. Pause the heartbeat and stop the owned probe
after delivery. The probe can be stopped by creating its own
`results/resource_watch/stop_requested`; do not stop any unrelated process.


Latest verified state: A04 attempt01 closed with a normal FAILED finish_request
at114.728577s; final PCT error pct_endpoint_pose_rejected. G05 is waiting on
external IsaacLab GPU use and less than20GiB available RAM. The external job
appeared during A04, so retain a resource-overlap limitation in its timing report.
An unsuccessful route is an experimental outcome, not permission to retry or
modify frozen code. Continue the remaining nine once resources allow. Full
A04 postprocessing can wait until physics no longer competes for resources.


2026-10-19 12:24 UTC progress supersedes the preceding G05 wait: resources
cleared and the same runner resumed. A04/G05/CU06 closed FAILED; D07 and S04
returned FINISHED at129.693192s and31.714199s. Full arrival/PD/margin/video
verification remains pending. CD12 is now running. Six formal ledgers exist;
never restart any of those cases. Compact new receipts and hash-bound progress
snapshots are returned locally. Continue remaining cases, then postprocess all.


2026-10-19 post-physics continuation: ALL TEN formal attempts closed. The formal
runner PID1220154 has exited; do not launch any more physics. Recorder states:
FINISHED D07,S04,CD12,CM07; FAILED A04,G05,CU06,CM02,CS03,CE03. Full acceptance
for FINISHED cases still pending. Compact closure ledger returned locally.

First A04 analysis PID1265834 finished successfully. Analysis batch PID1267153
(postprocess_all.py) verified and skipped A04, completed G05/CU06, then waits
for the resource gate before D07. The first three full videos and139 compact
files returned with SHA verification and six-frame local visual review. Full
analysis resource waits are normal; do not start another analysis batch.

Additional physical_support_margins.py uses each case's built edge_diagnostic
on exact recorded body_poses; zero physics. It passed2,209 support/ENV parity
samples for A04/G05/CU06. Run it for the remaining seven once their analysis
finishes, then rerun collect_physical.py. Collector returns only compact
physical_return/ plus explicit real delivered/ videos; raw recordings remain
on the host. Do not copy physical/*/margin_build or entire raw run trees.

Display-only snapshot-schema repair is in postprocess_case.py with red/green
receipts; v280/v282 hashes pass. No frozen execution/native code changed. All
remaining outputs, complete metrics/report, local visual QA and heartbeat/probe
shutdown after delivery are still required. Keep selected v232/v233 baseline.

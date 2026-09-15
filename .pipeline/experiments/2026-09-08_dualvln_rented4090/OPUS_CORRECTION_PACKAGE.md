---
origin: ai+local_review
date: 2026-09-09
status: prepared_not_dispatched
executor: Opus
---

# DualVLN: correct and archive the existing execution evidence

Write all responses and `OPUS_CORRECTION_RETURN.md` in English.

## Goal and scope

Close findings R1–R6 in `review/LEAD_REVIEW.md`. BF16 inference and two real
simulation videos already exist; both navigation trials failed. Preserve those
results while making statistics, STOP handling, visualization, and local
archival accurate. This pass is experiment analysis and harness correction.

- Read `AGENTS.md`, the original `OPUS_EXECUTION_PACKAGE.md`, `OPUS_RETURN.md`,
  and `review/LEAD_REVIEW.md`.
- Local Source of Truth: `/Users/sun/tongbu/study/phdproject/vla`.
- Own only `.pipeline/experiments/2026-09-08_dualvln_rented4090` (`EXP`) and
  `.trellis/tasks/09-08-dualvln-rented4090`.
- Remote execution copy: `/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090`.
  Use `ssh ubuntu@117.50.179.202` or `rented4090`; existing key auth works.
- You are not alone in the repository. Preserve concurrent edits, original
  records/videos/returns, the pristine source, other remote projects, and the
  running `isaac-sim` workload. Re-identify processes rather than trusting old PIDs.
- Ordinary fixes and evidence transfers are within the existing authorization.
  Do not start training, robot actuation, new navigation experiments, or an
  allocator/brightness ablation in this correction pass. No infrastructure
  replacement, unrelated process termination, staging, or commit.

Keep the original BF16 checkpoint revision
`a698a9e898b4001621a319e1bc89f02ec715cc86` and InternNav source commit
`7a5c62400ac45b313d9b709c740b64191556a242`. The verified environment uses
diffusers 0.32.2; do not reopen setup or change precision.

## Work

1. **Return unique evidence first.** All 864 episode PNGs (101,913,541 bytes)
   were freshly verified remotely against `setup/observation_manifest.json` by
   the lead; none are local. Transfer them resumably into the identical relative
   paths. Batch or losslessly deduplicate transport if useful, then verify each
   reconstructed file's size and SHA-256 locally. Audit other unique run outputs
   and cited previews/debug evidence for remote-only gaps. Preserve remote copies
   until local verification passes. Public pinned caches may remain remote under
   the original package's exception. A manifest or MP4 does not replace raw PNGs.

2. **Correct statistics without changing old raw records.** Produce a derived
   metrics artifact keyed to the original record hashes. Count every S2/S1 call,
   including look-down and calls containing both systems; distinguish recorded
   arrays from code-inferred invocation counts. Name existing latency groups as
   whole `agent.step` calls, with look-down timing reported separately. Relabel
   final-interval memory counters and end-of-run `nvidia-smi` snapshots; aggregate
   available samples and mark unavailable global peaks explicitly. Remove the
   unsupported allocator-effect claim. Repair future instrumentation to include
   every call and define its measurement interval; a sampled device maximum must
   include timestamped samples and cadence. No rerun is required to fill missing
   historical measurements.

3. **Fix STOP provenance.** Empty/unparseable output must not become learned
   STOP. Keep S1 padding/replan separate from explicit S2 STOP, including queued
   and look-down outputs. Add a small CPU-level regression check for these cases
   and distance-plus-STOP success. Preserve historical `success` fields; identify
   the corrected derived scoring as authoritative for these two failed trials.

4. **Rebuild both videos from existing evidence under new filenames.** Show
   look-down pixel goals on their matching tilted RGB view with its recorded
   gain, and retain the level view/action context. Label cached S2 text and
   pre-/post-action values clearly. Do not draw tilted-view coordinates on a
   level image. Fail visibly on missing required inputs rather than silently
   dropping frames. Decode the new MP4s, verify hashes locally, and inspect all
   pixel-goal moments (1 in v1, 9 in v2). Keep the original videos unchanged.

5. **Audit and narrow explanations.** Record the custom realworld-agent loop's
   camera-pair, queue, S2 cadence, and STOP differences from the pinned official
   Habitat evaluator. Do not silently change that experiment or claim parity.
   Correct the opening-spin interval. Treat brightness, rendering defects,
   camera tilt, and missing STOP as observations/hypotheses unless tested;
   withdraw causal claims about exposure, allocator savings, or camera necessity.

## Verification and return

Author changes locally, sync only owned files, and compare source/config hashes
before any remote execution, including video generation. Preserve the original
evidence and return new artifacts to the same local relative paths. For future
runs, add immutable executed-source/config provenance; do not retroactively
claim an exact source snapshot for the old runs if it cannot be recovered.

Return `EXP/OPUS_CORRECTION_RETURN.md` with an R1–R6 disposition table, exact
commands and outcomes, meaningful regression results, corrected metric scopes,
local MP4 paths and verification, local archival counts/hashes, owned diff, and
remaining gaps. Link the preserved original return. Keep navigation success
false for both historical trials. Mark the task `review` with
`executed_pending_lead_review` after completing corrections; any incomplete
transfer stays explicitly open. Do not call the package accepted yourself.

# v284 execution

Local source: versions/v284; parent frozen v283 stays unchanged. Remote execution
copy: /home/sun/vla_exec/static_continuity_v284. Raw recordings remain under
/home/sun/vla_exec/physical_runs_v284 on gpu5070ti. Use the same pinned container,
policy, geometry, 0.35 m body radius and 0.1 s scan period/deadline.

Commands below run from the corresponding experiment-relative repository paths
on gpu5070ti. Sync owned source first and verify source inventories before use.

1. `python3 versions/v284/prepare.py`, then `python3 versions/v284/build.py`.
2. `python3 versions/v284/run_native.py build`, `contract`, `continuity`, `unit`;
   run `python3 versions/v284/regressions.py`. Preserve parent failing continuity
   probe and all failed development checks separately from final qualification.
3. `python3 versions/v284/reuse_cohort.py` once: exact frozen v283 cohort/captures.
4. `python3 versions/v284/freeze_native.py`, then `run_matrix.py` exactly once for
   the 53 scored requests. Return all compact outcomes and the offline gate.
5. After every independent audit finishes, record the explicit timing-only
   authorization with `execution_admission.py --record-authorized-timing-exception`.
   This verifies all non-timing criteria and binds the unchanged benchmark gate,
   matrix, ledgers, completion receipt, native freeze, and exact user decision.
   Then run `prepare_execution.py`, all ten `preflight_runner.py` calls with
   V284_CASE_ID, and `freeze_execution.py`. Benchmark timing remains failed.
6. `audits/2026-10-19_v284_static_continuity/run_physical.py` executes the fixed
   order once each under the explicitly approved CPU resource admission. A04,G05,CU06,D07,
   S04,CD12,CM02,CM07,CS03,CE03. Inspect early startup rejections directly; no
   actual attempt may be repeated. Retain all launch logs and failures.
7. Closed recordings only: postprocess_all/collect_physical, compact return,
   full MP4 return, summarize, hash/decode/coverage and local visual review.
   Rendering adds zero physics. Do not rerun an episode to repair a video.

Hard admission for initial global requests and independent geometry audits remain
unchanged. The new static soft band is an optimization cost, not a wider hard
radius. Report goal/PD and geometry independently; no baseline promotion.

## Soft-cost qualification

The source-wall cost is `0.1 * max(0,(0.07-margin)/0.07)^2`; the exact radius
stays 0.35 m. Its source gradient repels in XY/yaw at actual height and leaves Z
zero; do not describe it as a full 3D ESDF derivative. Global GPMP can reuse the
existing request-owned hard-query cache solely to prove the cost is exactly
zero beyond 0.07 m, with exact source fallback otherwise. The local optimizer
uses the same evaluator and existing curve-gradient propagation.

Preserve development01/02/03/04 as unscored input replays. Final regressions cover
16 synthetic translated/rotated band/value/derivative controls,200 cached versus
full source-cost comparisons, the recorded source wall and A04 support-height
request, and original support/collision/epoch/control tests. Same final tracking
probe can run against the read-only parent using `--parent tracking-build` then
`--parent continuity`; parent failure 0/4 is expected.

For final normal videos, use the generic close-body FOV 95 camera on every route.
Display choices do not change physics, source poses, outcomes or navigation.

## Timing decision

The scored native median is 1.649324541 s (v283: 1.301 s). The original 1.5 s
benchmark gate is preserved. User reply: “继续十条，耗时记未达标”. This permits
physical execution after geometry and all other criteria pass; it does not
convert benchmark acceptance to success or authorize a new native revision.

## Approved remaining-resource execution

Dr Sun authorized GPU sharing: “可以没那么僵硬吧，gpu有一定资源也能用吧”.
Newton and the factory policy remain CPU workloads. Before each physical launch,
require >=16 GiB available RAM and >=10 GiB output space; observe GPU jobs
without vetoing CPU execution. Preserve original ports and all navigation,
geometry, scanner and mission gates. Rendering requires >=2 GiB free GPU memory.
Resource overlap is recorded and reported; no exclusive-host timing claim.

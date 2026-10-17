# Implementation plan

1. Executor: implement a local, ROS-free terrain/person collision module and
   focused tests under `p2b_execution/reactive_stair/`. Reuse the existing
   step prototype only as a reference. Do not edit the accepted `scan_04` tree,
   existing dirty runner files, or pinned `planner.yaml`.
2. Executor: add a hash-gated candidate materializer under the same directory.
   It may create a new `scan_05` tree from `scan_04`, but must not mutate the
   baseline. Integrate an explicit current-track input or report why the ROS
   adapter cannot be made safely with available inputs. No remote run.
3. Lead: inspect actual diff and local tests, including negative cases and
   source hashes. Request corrections if person occupancy can be cleared or
   the candidate silently falls back to the one-window prototype.
4. Lead: if local gates pass, perform a bounded Foxy build and source sync
   check. Then prepare one bounded Isaac moving-pedestrian stair episode if a
   verified track source and terrain input exist. Record a missing dependency
   instead of substituting simulator truth without a label.
5. Lead: write a result with exact tested scope and untested paths. Review
   staged paths before any commit; leave concurrent dirty paths untouched.

## Stop conditions

No physical robot or formal training. Do not alter prior experiment verdicts
or frozen thresholds. Stop before an Isaac run if terrain support or person
track provenance is unknown, the GPU host is busy, or the source gate fails.

## 2026-09-26 execution pause and archive

Dr Sun reported server shutdown and asked to archive. scan33 native tests,
independent review, deterministic source regeneration and full build pass;
install identity and paired optimizer replay are pending. Stop remote retries.
Task remains in progress; do not close A4 or repeat the completed build.
Continue from `.pipeline/handoffs/2026-09-26_scan_stair_handoff.md`.

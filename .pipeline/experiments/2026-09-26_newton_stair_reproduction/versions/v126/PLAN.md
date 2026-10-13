# MPPI adaptation 2: one reference-path recovery chain per round

Stage: experiment + analysis. Native parent v122; host entry parent v125.
Dr Sun explicitly selected the retained diagnostic candidate and authorized step 2.
Local repository is authoritative; compile, tests, physics and full-data analysis
run on gpu5070ti under /data/sun/vla_mppi_20261009. No robot actuation or training.

## Single change and rationale

The REFERENCE_PATH branch of SCANReplanFSM::planFromCurrentTraj currently calls
the entire recovery chain up to three times with different polynomial/random
initialization flags. The current native graph initializer no longer consumes
those flags. Each call already contains warm-to-cold fallback, fixed-height
recovery and up to three shared shorter-target proposals. Remove the two outer
legacy initialization retries; callReboundReplan owns one complete chain.

This borrows bounded retry ownership from the inspected Nav2 MPPI optimizer
(bcc9c48cf468588559d01942b72d511a6b990891), not its ROS API or planar checks.
Failure returns to the existing FSM/safety policy; the next scheduled round can
use fresh inputs. A map update during the old extra retries might have enabled
later recovery: this scheduling tradeoff requires physical comparison, not an
unconditional behavioral-equivalence claim. No failed-result cache is added.

Only the reference-path retry block changes in native code. Preserve all inner
distinct recovery modes, prefix proposal budget, captured boundary PVA/epoch,
optimizer repair, publication/collision/dynamics/freshness checks and stop flow.
Initial planning and non-reference modes stay unchanged. Steps 3–5 are excluded.

## Checks and decision rule, before running

1. Verify the exact native diff and that old initialization flags do not affect
   the graph initializer. Compile actual FSM/manager control flow with scripted
   target/solver seams: first success, warm failure then cold success, fixed-height
   success, shorter-target success, exhausted retries and next-round recovery.
   Preserve captured PVA/epoch and per-round independence; prove fewer actual
   solve attempts on unchanged-input exhaustion. Label scripted results as such.
2. Run the retained real native recorded-map trajectory/publication/stale-input
   test, component plugin tests, and verify unchanged successful curve values.
3. Run up to two independently initialized same-host pairs: retained v122 versus
   v126, original Building corner, CPU Newton, 90-second bound (early measured
   arrival allowed). No concurrent build/analysis during timed physics. Allow
   ports to become free between runs without changing simulator safety timers.
4. Keep only if fixed-input recovery checks pass, duplicate work decreases, and
   candidate physical runs reach the original goal/measured hold without falls
   or weakened gates. Require median P95 latency no more than 10% above the
   control and median longest pause no more than 1 second above it. A candidate
   navigation failure may stop the sequence early and parks the candidate.
   Report all outcomes; two trials are not a reliable population success rate.

## Source and evidence

Baseline install remains /task/candidate (native v122). New v126 install is
/task/step2_v126; do not overwrite the prior installs. The launcher selects
explicit source/install receipts and uses the same verified Foxy image.
Freeze the new source after component checks, before physics. Return compact
reports, CSV and SHA-256 locators (target <15 MB); retain raw runs, images,
compilers and replay inputs remotely. Keep v48 as the navigation reference until
the broader acceptance gates pass. Preserve the pre-existing Git index lock.

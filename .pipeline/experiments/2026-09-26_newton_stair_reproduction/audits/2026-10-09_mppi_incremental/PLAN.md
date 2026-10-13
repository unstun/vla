# Sequential MPPI-inspired adaptations

Stage: experiment + analysis. Dr Sun authorized five adaptations, one at a time,
with an isolated test and a keep/park decision before the next adaptation.
No combined untested change is accepted. No real-robot actuation or formal training.

| Step | Change | Acceptance / keep criterion | State |
|---|---|---|---|
| 1 | Typed planning failure classification | Correct source-stage and input-age context, no substituted causal claim; same decisions/curves in controlled native tests; bounded overhead; recorded physical smoke | keep: v122 diagnostics; v125 same-host pair and fixed-input curve comparison passed |
| 2 | Unified retry ownership | Fewer redundant attempts without losing feasible recovery or weakening safety; measured comparison | park v126: components pass, first same-host physical candidate fails; retain v122 |
| 3 | Independent trajectory validation interface | Equivalent original 3D/support/PVA/freshness decisions and explicit reasons; no regression | park v127: fixed-input equivalence passed, first physical candidate failed; retain v122 |
| 4 | Plugin-based preference scoring | Swappable soft objectives with unchanged hard rejection; controlled behavior tests and navigation comparison | pending |
| 5 | Candidate / score / rejection visualization | Correct same-run candidate identity and causal timing; measured recording overhead | pending |

Step 1 changes only diagnostic classification. It does not change search,
retry counts, stopping, validity thresholds or controller commands. Benefit is
explanatory coverage; faster navigation is not a step-1 acceptance requirement.
A compile or unit-test pass alone does not establish physical navigation.
A failed or regressing candidate is retained but not used as the next parent.

## Step 1 boundary

Native parent v114, recorder/entry parent v116; new logical version v122.
Borrow the separation of outcome/validation from Nav2 MPPI at
bcc9c48cf468588559d01942b72d511a6b990891 (Apache-2.0 package).
Do not copy the planar MPPI validator or its newer ROS interface.

Owned changes: new diagnostic type header; manager header/implementation to
record existing failure branches; FSM to bracket a round and return structured
outcome; GridMap read-only getters for the original observation-ready/max-age
fields; native tests; v122 export/launch/provenance. Existing frozen versions
remain byte-identical. No dispatch/subagents.

Report the stage that actually rejected and input freshness observed at that
point separately. A stale observation seen after a failed A* does not prove
staleness caused every explored edge to fail. Preserve first/last failure and
per-stage counts even when a later retry succeeds. A successful round must not
be labelled failed just because an earlier attempt failed.

The latest instruction on 2026-10-09 explicitly moves builds, simulation and
comparison to gpu5070ti. This supersedes the earlier Mac-only execution scope.
Use /data/sun/vla_mppi_20261009 for owned execution and bulk evidence; local
source remains authoritative. v123 owns the x86_64 host port; v122 remains
immutable. Compare baseline and candidate on the same host/environment and
retain the original CPU physics solver. Do not combine Mac and Linux timings.
Return only compact checksummed reports, metrics and review media. The previous
Mac v116 attempt03 has no completion record and its temporary root is unavailable;
do not count it as a completed comparison. v122 Mac attempt01 has compact results
but its temporary raw root is also unavailable; rerun remotely before acceptance.
Do not remove the pre-existing Git index lock or automatically stage/commit.

Before running the native step-1 probe: measure 1000 structured log emissions
(including context reads); require mean below 200 microseconds and P95 below
500 microseconds on this local container. This is an overhead check, not a
per-round hard deadline or a Jetson performance claim.

## Step 2 boundary, 2026-10-10

Dr Sun selected the retained step-1 version and explicitly authorized step 2.
Native v126 removes only the two outer legacy initialization retries in the
REFERENCE_PATH current-trajectory branch. The current initializer ignores those
flags. Preserve warm/cold, fixed-height, three shorter-target proposals, checked
PVA/epoch and all original safety gates. See ../../versions/v126/PLAN.md for the
predeclared component and two-pair physical decision rules. Builds and physics
run on gpu5070ti; local source remains authoritative. Steps 3–5 stay pending.

Step 2 result: park v126 after one paired trial (v122 arrival; v126 navigation
failure). The predeclared early stop applies; no second pair. See
`../2026-10-10_mppi_step2/REPORT.md`. Retain native v122 / host v125 for the next
adaptation. Steps 3–5 remain pending.

Step 3 result: v127 independent native validation passes 376 fixed-input checks
and original safety regressions, but its first physical trial fails after stale
evidence and no-progress recovery. Park it under the declared early-stop rule;
retain native v122 / host v125. See `../2026-10-10_mppi_step3/REPORT.md`. Steps4–5
remain pending. The single pair does not isolate causality.

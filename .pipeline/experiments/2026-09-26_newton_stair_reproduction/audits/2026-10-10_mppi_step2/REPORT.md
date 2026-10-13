# MPPI adaptation 2: reference-path retry ownership

Stage: experiment + analysis. Decision: **park v126; retain native v122 / host v125**.
The candidate failed its first physical navigation trial. The predeclared early
stop rule applies; no second pair or steps 3–5 were started.
Native parent v122, candidate v126; host source parent v125. All builds and
physics execute on gpu5070ti, with CPU Newton and the same Ubuntu 20.04 / Foxy
image. Local source is authoritative. No Jetson or robot-actuation claim.

## Change and evidence boundary

The native change is a single REFERENCE_PATH branch in
`versions/v126/src/plan_manage/src/scan_replan_fsm.cpp`: call the existing complete
recovery chain once, removing the two outer polynomial/random initialization
replays. The real graph initializer ignores both flags. Manager, optimizer,
three shared shorter-target proposals, warm-to-cold and fixed-height recovery,
PVA/epoch, publication, collision/dynamics/freshness gates and stopping remain.
Initial planning and non-reference navigation branches are byte-identical.

This adapts bounded retry ownership from the inspected Nav2 MPPI optimizer at
`bcc9c48cf468588559d01942b72d511a6b990891`; it does not replace SCAN with MPPI or
import modern ROS interfaces into Foxy. Fewer retries may also reduce opportunities
to consume a newly completed map during the same callback. Physical comparison is
therefore required. A new scheduled round can retry with fresh input; no failure
cache is introduced. This is not a hard 60 ms deadline.

## Component checks

- Full isolated 14-package Foxy x86_64 build; 36 component tests, zero failures.
- Compile actual parent/candidate FSM and manager control flow. Only target
  admission, endpoint occupancy and individual solver outcomes are scripted.
  Six cases per arm pass. First success uses one attempt; warm/cold and fixed
  height use two; shorter target uses three. Exhausted graph seed attempts fall
  from 6 to 4, and exhausted optimizer attempts from 12 to 8. Sampled PVA/epoch,
  previous-curve preservation, height-mode restoration and next-round recovery
  are checked. These are control-flow assertions, not safe-curve or timing proof.
- Separate real native recorded-map test: successful curve has identical 33
  control values, knots and duration; exact publication proof and stale-input
  rejection pass for both native installs.
- Candidate-installed ten-child ROS graph startup, original configuration
  comparison, wrong source/variant/image rejection and real host/container file
  ownership/writer checks pass. No physics in these startup checks.
- Frozen source/snapshot verification: 2,833 pairs and 618 runtime inputs.

Results: `component/contracts/result.json`, `component/build.log`,
`component/host_tests02.log`; exact code diff: `../../versions/v126/changes.patch`.
The first fixture compile failure and inherited host-probe limitation are
preserved in `early_attempts.json`; neither is counted as a passing candidate test.

## Physical decision rule

Declared before execution in `../../versions/v126/PLAN.md`: up to two independent
same-host pairs, 90-second bound with early native arrival and measured PD hold.
Keep only with candidate arrivals, no falls or weakened gates, median P95 no more
than 10% above control, and median longest pause no more than one second above it.
A candidate navigation failure can stop early and parks the candidate. Report
all attempted runs. These trials cannot estimate population reliability.

## Physical result and decision

One independently initialized same-host trial per arm was completed. All source,
copyback and archive gates passed; neither robot fell. These are one-run
observations, not a statistically established causal effect or success rate.

| Metric | Retained v122 | Candidate v126 |
|---|---:|---:|
| Native arrival + measured PD hold | Passed | Failed |
| Measured path | 26.371 m | 23.559 m |
| Simulation end, including startup | 51.423 s | 58.779 s |
| Complete planning rounds | 980 | 877 |
| Failed planning rounds | 17 | 17 |
| Mean / P95 round latency | 3.083 / 5.997 ms | 4.989 / 6.231 ms |
| P99 / maximum round latency | 19.198 / 136.189 ms | 123.784 / 442.960 ms |
| Rounds >60 ms (successful / failed) | 7 (5 / 2) | 15 (7 / 8) |
| Maximum solver attempts per round | 13 | 9 |
| Emergency transitions | 7 | 9 |
| Longest low-speed interval | 4.298 s | 9.695 s |

The baseline's longest low-speed interval is its intentional terminal stand;
the candidate's 9.695 s interval occurs before its final abort. Both variants
had 17 failed rounds, yet only the baseline completed navigation: per-round
failure counts alone are inadequate acceptance criteria.

The candidate's direct terminal chain is recorded in `postmortem.json`: Nav2
first reports `Failed to make progress`; a later recovery is aborted when native
observation age is 0.259857177 s, exceeding the unchanged 0.25 s limit; the final
recovery reports `scan_trajectory_missing`, then `Navigation failed`. Stopping
remained active. The maximum 442.960 ms round at simulation time 31.179 s is a separate
earlier event, with 8 solver attempts. Its map revision advances 254->259 and its
last rejection is dynamics with a fresh observation. This evidence does not
establish that every slow round or the eventual failure has the same cause.

Fewer redundant attempts were demonstrated, but navigation regressed in the
observed pair. The early-stop failure rule therefore parks v126 regardless of
its P95. Keep the frozen candidate and all failed evidence for investigation;
do not use it as the parent for the next adaptation. Retained native source and
install are v122; the previously qualified host entry is v125. v48 remains the
broader experimental reference. No claim of sustained 30 Hz, universal tail
improvement, Jetson compatibility testing or hardware validation is made.

A possible follow-up is a state-equivalent replay around the recovery divergence,
including map-arrival timing, before reconsidering retry reduction. This follow-up
and adaptation 3 are not executed in this task.

## Storage and reproducibility

Bulk: `/data/sun/vla_mppi_20261009`. Baseline native v122 remains `/candidate`;
candidate is `/step2_v126`; prior installs are untouched. Run entry:
`versions/v126/run_comparison.py --variant {baseline,candidate} --attempt N`,
using `/home/sun/vla_exec/envs/newton_worker/bin/python` on the remote execution
copy. Source/install/image receipts are checked before physical execution.
Compact outputs return here, with raw captures retained remotely and SHA-256
locators. Steps 3–5 remain pending; v48 stays the broader navigation reference.

Final return verification: 36 allowlisted files, 1,440,844 bytes, all matched server SHA-256 and size. Both native installs and all 2,833 frozen source/snapshot pairs remain exact; owned runtime containers/processes are absent. Full trial evidence remains on gpu5070ti (v126_baseline_attempt01: 163,656,495 bytes, v126_candidate_attempt01: 186,747,144 bytes). See `closeout_manifest.json` and `final_verification.json`.

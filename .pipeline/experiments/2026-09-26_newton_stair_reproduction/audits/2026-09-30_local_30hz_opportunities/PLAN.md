# Local 30 Hz optimization opportunities

Status: analysis and proposed changes only. No production source, frozen version,
runtime configuration, training run or physical run was changed in this audit.
The current physical baseline is v45; its native implementation is v44.
Local source of truth: `/Users/sun/tongbu/study/phdproject/vla`.

## Observed evidence

`findings.json` binds statistics to the v45 scan log and current native source
SHA-256 values. `rounds.json` contains all 878 completed nominal rounds; the
remaining started round has no completed result and is excluded from solve-time
statistics.

- Single-attempt rounds: 140, mean 19.670 ms; 21 exceeded 33.333 ms.
- Two-attempt rounds: 630, mean 56.467 ms; 524 exceeded 33.333 ms.
- Three-attempt rounds: 94, mean 99.732 ms.
- 647 completed rounds failed the seed search in their first rebound attempt.
- 736 rounds proposed a shorter reference-path prefix, and these rounds ultimately
  succeeded. This is a strong lead for local-window selection, not proof that
  shortening every initial window would preserve progress or reach 30 Hz.
- Failed seed-search log spans averaged 34.610 ms, versus 14.176 ms for successful
  searches. These spans also include printing and seed checks; they are not
  isolated CPU-profiler measurements.
- No A* 200 ms timeout was logged. Most observed failed searches returned
  `SEARCH_ERR`; reducing the existing 200 ms timeout alone will not address the
  dominant observed failures.
- No same-mode, byte-identical captured initializer was solved twice within a
  completed nominal round. Repeated attempts must not all be labelled redundant.
- The inherited `flag_polyInit` and `flag_randomPolyTraj` parameters are passed
  through but never consulted by the current graph-based initializer. The outer
  retry names therefore no longer describe different initialization algorithms.
  Incoming data and intermediate targets can still differ, so blindly deleting
  those calls is not justified.

The single-attempt and retry groups have different geometric difficulty.
Their means cannot be used as a causal speedup estimate or an acceptance claim.

## Ranked implementation candidates

### 1. Reuse the recently feasible local window as the first candidate

Today `getLocalTarget()` chooses a fresh nominal horizon, and failed planning
then halves the reference-path window inside `callReboundReplan()`. The next
nominal cycle starts that search again. Investigate retaining a hint about the
most recently accepted local window, validating it against current route
identity, measured progress, map bounds, support and fresh sensor evidence,
then extending it when feasible. A changed goal, route geometry, map identity,
or invalid current evidence must invalidate the hint.

This changes intermediate-target selection and needs its own integer version.
Keep the exact final goal and yaw unchanged. Assess path progress and pauses
alongside frequency: a shorter window that makes the robot crawl is not an
acceptable optimization.

### 2. Initialize from the remaining valid trajectory before graph search

Pinned upstream SCAN-Planner already has a previous-trajectory initialization
branch:

https://github.com/wuyi2121/SCAN-Planner/blob/348e8a590a50a5a6bbab8d8c6dcfd171f009be26/src/planner/plan_manage/src/planner_manager.cpp

Its local snapshot is recorded in `findings.json`, and the manager source hash
was checked against the recorded upstream identity. The current stair initializer
always starts with A*, even when a recently accepted local curve exists.

Adapt the reuse concept to the current stair contract. Use the remaining curve
as an initial guess, bind its route/command identity, preserve start/end PVA,
and check it against newest occupancy and terrain support. Fall back to the
existing native search when reuse is invalid. Do not blindly restore the old
polynomial extension: it does not establish the current stair-support contract.
Keep the final full-curve collision, dynamics, minimum-cruise and goal checks.
Reusing an initial guess does not mean restamping an old curve as a new plan.

### 3. Bound the complete solve and recovery chain

Current recovery includes shorter prefixes, fixed-height optimization, outer
initialization retries, up to 200 L-BFGS iterations per solve, optimizer restarts
and rebound loops. The 30 Hz scheduler records overruns after these finish; it
does not impose a 33.333 ms solve deadline.

Investigate one shared monotonic budget across target selection, graph search,
optimization and recovery. Reserve time for the final safety check and executor
callbacks. On timeout, continue only an existing trajectory that still passes
fresh safety and identity checks; otherwise use the original stop flow. Never
publish a partially checked curve. Report attempted cycles, successful new
trajectories and controller outputs as separate rates. A 30 Hz attempt timer
with frequent failed solves is not sufficient acceptance.

This is a behavior change, not a timer-only optimization, and requires its own
version and explicit timeout/stop regression cases.

### 4. Profile bounded cache reuse and diagnostic output

The raw-contributor cache currently ends with each executor callback. There may
be reuse between callbacks while the underlying raw inputs are unchanged.
Investigate a bounded cache with explicit input revisions and invalidation at
every relevant mutation. Keep final occupancy/support/freshness/pose checks live;
do not cache those verdicts. Verify ring-buffer shifts and newly observed obstacles.

Large seed/curve dumps and visualization publications are another measurement
candidate. Their actual share is not established by current logs. If material,
defer diagnostic serialization while preserving raw inputs, rejected-curve
reasons, timing records and reproducible numerical evidence.

## Suggested order and verification

Start with a new version that changes only the feasible-window policy; keep
warm initialization, solve budgeting and cross-callback caching in separate
versions. Alternatively, if strict numerical equivalence is the priority,
measure the cache candidate first. Do not combine all candidates and attribute
the resulting speedup to one of them.

Before implementation, construct representative replay cases from v45,
including a successful first search, first-search failure followed by a shorter
successful window, fixed-height recovery, the slow tail and current-curve
invalidation. The old v32/v33 stopped-state cases remain useful safety
regressions but do not represent the v45 live retry distribution.

For each candidate, compare identical recorded inputs before and after on the
5070 Ti execution copy, return all source/install/log hashes locally, then run
the complete physics/sensing/transport stack. Preserve all frozen versions.
Measure solve median/P95/P99/max, actual local/controller/global rates, skipped
slots, budget overruns, invalid-curve publications, measured motion and pauses.
Use 20–25 ms as a provisional solve target to leave room under 33.333 ms; it is
not an observed result or a guarantee.

The separate `global_refresh_failed:pct_no_route` terminal in v45 also remains
unresolved. Improving local frequency does not establish complete Building
navigation acceptance. No GPU-migration or multi-executor speedup is claimed
without an appropriate profiler and state-ownership design.

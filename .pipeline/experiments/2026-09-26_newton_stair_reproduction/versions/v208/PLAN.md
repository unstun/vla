# v208: stillness-based RL-to-PD return

Parent navigation: frozen v206. Previous display: v207. Stage: experiment +
analysis. Dr Sun authorized trying the surveyed machine-dog return mechanism;
this session continues without a Trellis task.

## One behavior change

The physical locomotion adapter owns zero-command return to standing. Replace
its entry dependence on four-foot loading and near-equal force shares with
continuous body/joint stillness for 0.25 s: linear speed <=0.15 m/s, angular
speed <=0.5 rad/s, tilt <=0.15 rad, each joint speed <=1 rad/s. The physics owner
supplies current measurements synchronously. Use the existing two-second
crossfade variant and cap the stand contribution to 0.2 rad from each measured
joint, as in machine-dog's A5/A6/A7 mechanism.

Preserve V12's torque-matched capture target. Do not copy V21k's nominal pose or
force symmetric joint angles across uneven support. Preserve factory startup,
the original disturbance handling and REJOIN, policy/history contract, motor
gains and limits. No forced takeover on timeout. Existing ten-second settling
window bookkeeping may restart; it never authorizes transfer.

PCT, SCAN, Tracker, global refresh, Nav2 goal tolerances, ten-second terminal
budget, two-second final physical hold, and retry behavior are unchanged.

## Owned files

- Versioned stance_hold.py: explicit snapshot of the prior pinned Python hold,
  with only the declared return changes. The old source remains untouched.
- Versioned newton_stance.py and activate.py: bind the existing Newton sensor
  adapter to the new hold explicitly; no global default replacement.
- Targeted tests, captured-input check, bounded physical probe and receipts.
- Version index and architecture HTML: report the actual outcome and scope.

## Verification declared before execution

1. Existing old-hold suite remains unchanged and passes. Candidate regressions
   check uneven loads, motion/joint/tilt rejection, dwell reset, no forced
   timeout, transfer/target cap, new-command rejoin and unchanged startup hold.
2. Replay the recorded v206 terminal inputs. Preserve the old failure and
   determine the candidate's first eligible transfer; this is decision evidence
   only, not a substitute for physical simulation after ownership changes.
3. On gpu5070ti, initialize the original Building robot/mesh and V12 policy from
   two recorded states: the first final-zero boundary (115.548126 s) and the
   later quiet, balance-blocked state (120.285522 s). Run the old and new hold
   from the same state for ten seconds each (at most 501 control intervals,
   allowing one final 20 ms interval for the float32 clock). Preserve measured q/qd,
   applied targets/gains, last action, and all ten policy-history frames.
   Solver contact/warm-start caches were not recorded; this is a matched
   initialized-state probe, not an exact continuation of the original episode.
4. Report takeover time, actual PD ownership and gains, maximum tilt, measured
   motion and XY drift, foot forces, torque continuity and limit occupancy.
   Candidate success requires >=2 continuous seconds of FIXED_STAND with
   measured speed <=0.03 m/s, angular speed <=0.05 rad/s, all feet >1 N, and
   no fall, finite-state failure or growing tilt. Record failures without
   changing thresholds to fit them. No new full-route trial is authorized here.

Source of truth: this local version directory. Sync the explicitly listed
sources to /data/sun/vla_mppi_20261009/repo, verify a single source manifest,
then execute with the existing Newton Python on gpu5070ti. No local builds.
Heavy raw physics records stay on gpu5070ti; return compact reports, provenance
and any review video. Freeze the candidate before physical stepping; preserve
its outcome and use a subsequent integer version for a later behavior repair.

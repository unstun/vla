# Response to independent review round 1 (`independent_review_round1.json`, failed)

Every finding was checked against the code and records before it was acted on. Both blocking findings are
correct. The round-1 candidate is kept in `round1/`.

## B1: the import record was not updated, so the trial would have been refused before physics. Fixed.

- **Confirmed:**
  - `run_local_episode.py:163-165` re-hashes every row of `setup/runtime_sources.json` and raises "Archived
    runtime source changed". The round-1 record mismatched exactly `contracts.py`, `control_gate.py` and
    `node.py`.
  - `node.py` is in the manifests of v11, v14, v26, v31 and v32. v11 and v14 changed it, and both listed the
    record as a changed file. v26 did the same for `config.py`.
- **Fix:** `setup/runtime_sources.json` is v33's fifth changed file. `materialize.py`'s `update_record` gives the
  three rows their new `sha256` and `bytes`, keeps the import hash as `archived_sha256` (node.py's existing one
  unchanged) and adds a `local_modification` note, in the file's own format. The preimage is
  `parent_source/setup/runtime_sources.json`, and the edit is in `changes.patch` and `prepared.json`.
- **Checks:**
  - K1 and K2 now cover the record: the rebuild, the restoration, only the three rows and the four fields
    changed, and the hashes are the current files'. The other v32 files number 2,970.
  - The new K1b (`record_check.py` → `record_check.json`) executes `run_local_episode.py`'s own three lines and
    the review's `source_identity` comparison on the v33 bytes: both pass. Its negative control, v32's record
    against the v33 files, finds exactly the three files.
- **Corrected text:**
  - `PLAN.md` "The change" now states the provenance.
  - `COMPONENT_RESULTS.md` corrects the round-1 statements.
  - `materialize.py`'s comment and pre-checks: every record must match before the edit.
  - `PHYSICAL_RUN_PLAN.md` "Gates before physics" names the record check.

## B2: the claim boundary misstated what the simulation base gives up. Corrected, and decided by Dr Sun.

- **Confirmed:**
  - The bridge publishes `/clock` and the pose from one state sample in one timer callback
    (`_publish_complete_state`).
  - SCAN's `cmdCallback` runs on a 10 ms wall timer and checks only that a trajectory and a pose have ever
    arrived.
  - With `require_fresh_simulation_feedback: false`, a `STALLED` verdict does not zero commands.
  - The Mac side's 250 ms rule acts only on commands that stop arriving.
- **One refinement:** the case the review cites, L1's stall inside the bridge's ROS thread, is bounded at about
  0.25 s. The same thread receives the backend's commands (`_on_twist`), so the bridge's command thread sends
  zero once its newest command is 0.25 s old. The 2.0 s exposure applies to a stall before that thread or on
  delivery to the backend, while the command path keeps running.
- **Recorded bound, reproduced independently:** `evidence/clock_lead_survey.py` finds 128 gaps over 0.25 s in
  17 of 48 runs. Across them, simulated time advanced at most 0.08 s, counting the burst after the gap.
- **Dr Sun's decision (2026-09-29, asked after this review):** keep the 2.0 s backstop, document the case, and
  flag it in the trial's analysis. Any pose gap in which simulated time advanced more than 0.25 s is reported as
  a stalled pose path, and the run's claims are qualified by it.
- **Corrected text:**
  - `PLAN.md`: the basis (line 18's claim), the consequence under "The simulation clock", "What the simulation
    base means" (rewritten, with the command paths), the decisions, and the claim boundary.
  - `PHYSICAL_RUN_PLAN.md`: "How the run ends", the new flag, and the stop rule.
- **Code:** the rule is unchanged. Three comments in the edits now name the stalled pose path besides a stopped
  simulator.

## Non-blocking

- **N1:**
  - `replay_gate.py` now calls M2 an approximation and adds M3, the burst after a gap.
  - `PLAN.md` K4 gives the direct measurement: the observer's `/clock` minus the backend's newest pose was at
    most 0.08 s over 1,890,389 samples (`evidence/clock_lead_survey.json`), and at most 0.0403 s outside v12.
  - `pose_gap_survey.py` and its docstring are left unchanged, as the record of how that survey was made.
    `PLAN.md` no longer calls its figure an upper bound.
- **N2:**
  - K5 now runs the trial path: the loader, `build_runtime` and a single-threaded executor on the
    native_graph-derived config. It passed on `trial` attempts 02 and 03.
  - Every attempt writes its own files and cannot overwrite another. (Corrected after review round 3, N5: the
    round-2 guard protected only the JSON, not the log; no log was overwritten. The script now exits on any
    existing output. See `REVIEW_RESPONSE_round2.md`, N6.)
  - The session record shows that round 1's K5 revision was written after the passing attempt, not before. Both
    that change and round 2's are recorded as post-failure changes (`PLAN.md` K5, `COMPONENT_RESULTS.md`).
  - The round-1 harness (`multi`) is kept and reported. Two of its three round-2 attempts failed on the
    unchanged heartbeat, because its shared executor threads starved the harness's own command stream. The gaps
    were measured. (Corrected after review round 3, N5: the cause is not established. GIL contention among the
    harness's threads is a hypothesis, and the publisher node has no callbacks for the executor to serve.)
- **N3:** the backstop rule now applies under the simulation base only. K3 C7 adds wall configurations: an
  `odom_stale_s` of 2.5 s, which red and green both accept, and a backstop below the limit, which green accepts
  (red has no backstop field). This sentence was corrected after review round 2 (N7), since it had said that red
  and green both accept both.
- **N4:** `PHYSICAL_RUN_PLAN.md` pre-registers:
  - the exposure count: pose wall gaps over 0.25 s while an owner was admitted, found through
    `backend_states.jsonl`;
  - the attribution rule: the backstop if and only if the wall gap exceeded 2.0 s (refined after round 2, N3, to
    use the stop flow's start time);
  - the observer's `clock_ns` as the `/clock` proxy.
- **N5:** the heartbeat figures are reproduced (`v12_building_route01` 0.439 s, `empty_long_route03` 0.231 s; at
  most 0.05 s in the historical_full trials) and added to `PLAN.md`'s claim boundary. A `heartbeat_stale` end is
  read as a backend-side stall.
- **N6:** `PHYSICAL_RUN_PLAN.md` records the fixed "original sensor/command freshness watchdogs" text as a known
  inaccuracy, for RESULTS to note.
- **N7:** `PLAN.md` states the quantization of lost-pose detection: up to about 0.35 s when only sensor frames
  advance `/clock`.
- **N8:** `PHYSICAL_RUN_PLAN.md` clamps negative simulation ages at 0 in the distributions and reports the raw
  minimum.

## Re-run after these changes

- **K1/K2:** passed, 5 files, 2,970 others unchanged.
- **K1b:** passed.
- **K3:** passed on the Mac (3.12.13) and in the pinned image (3.10.12), with identical cases.
- **K4:** passed: 48 runs, 84 wall-base episodes in 16 runs, 0 simulation-base trips under M1–M3, and 48/48
  synthetic losses detected.
- **K5:** passed on the trial path (`ros_smoke_trial_attempt03.json`).
- **Also fixed:** a zsh mount mistake in my first container command this round. It changed no check
  (`COMPONENT_RESULTS.md`).

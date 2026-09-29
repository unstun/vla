# Response to independent review round 3 (`independent_review_round3.json`, passed)

Round 3 confirmed the round-2 fixes, with no blocking finding and six non-blocking ones. All six were checked
against the code and records and fixed. No runtime byte changed. N1 and N2 change pre-registered analysis rules,
and N3 and N4 change check scripts, so round 4 confirms them. Any round-4 finding that is wording only will be
applied after it and listed in `independent_review.json`, as v32 did after its round 5.

- **N1, attribution measured from the wrong pose.** Confirmed on the records. In 7 of the 12 recorded
  `odom_stale` ends, the stop flow started 1–41 ms after the pose gap had ended: v17, v25, v30, `diag_v31_clock03`,
  `empty_long_route01/02` and `v5_building_route01`. The runtime's monitor polls the gate every 50 ms
  (`runtime.py`, `monitor_period_s`).
  - **Why it matters:** there, a lag taken from the newest pose is 0.001–0.025 s. Taken from the gap's start,
    it is 0.27–0.30 s.
  - **The new rule** (`PHYSICAL_RUN_PLAN.md`, `PLAN.md`): the lag runs from the start of the newest pose gap over
    0.25 s that contains the stop flow's start or ended at most 0.1 s before it. It is the backstop if and only if
    the lag is at least 2.0 s, since the backstop trips only after 2.0 s and the flow can only follow.
  - **Cross-check:** the observer's `/clock` at the flow's start.
- **N2, exposure.** Condition 3 now also requires the observer's `gated_command` stream, the backend's output,
  to have no interval over 0.20 s across the gap, so the backend was evaluating. A gap failing condition 2 or 3 is
  "not exposed" even when condition 1 is unknown.
- **N3, the harness check after a failing run.** `run_ros_smoke.sh` now captures the run's status, always
  compares the harness copy, and exits with the run's status. A scratch test with a failing stub run passed an
  unchanged harness through and detected one changed during the run.
- **N4, added or renamed rows.** The record check restores rows with `old.get(path, row)`, so an added or renamed
  row fails the restoration instead of raising. Scratch mutants cover an added row, a renamed path, a foreign
  note, a dropped `archived_sha256` and a dropped row: all detected, none crashed. `check_change.json` is
  unchanged.
- **N5, stale or overstated statements:**
  - (a) `REVIEW_RESPONSE_round1.md`'s two statements, on the overwrite guard and on the `multi` cause, are marked
    as corrected;
  - (b) `freeze.py`'s manifest text now says that the applied-evidence check catches a stopped simulator first in
    this integration;
  - (c) `PLAN.md` bounds a physics-stopping host stall at 2.0 s (`applied_evidence_stale`);
  - (d) the trial loads three of the seven `config_archived/` files, which total 13,628 bytes, and all seven are
    pinned;
  - (e) `REVIEW_RESPONSE_round2.md` notes that the freeze's file count depends on the files present then.
- **N6, the relaxation factor.** It is now about 2.5–4 times: 0.25–0.35 s of simulated time against v32's
  0.0875–0.10 s. `REVIEW_RESPONSE_round2.md` is marked.

## Found while checking N1: a false statement in K4, now corrected

`COMPONENT_RESULTS.md` and `PLAN.md` said the K4 replay's wall base reproduces every recorded `odom_stale` end. It
reproduces 11 of 12. `v5_building_route01` ended on `odom_stale` (its `result.json`), but its only gap over 0.25 s
was 0.2604 s. That left a 10.4 ms stale window, no replay evaluation point fell inside it, and the backend's own
watchdog caught it. Rounds 1–3 did not flag the statement. The miss concerns only the wall-base validation. The
simulation base's result, with ages at or below 0.08 s, is not near its limit. Both files now state 11 of 12
and the reason. (Corrected after review round 4, N1: it reproduces 10 of 12. `empty_long_route02` is missed as
well: its first gap, 0.2532 s, left a 3.2 ms window, and the replay's one episode in that run is in its later gap,
after the stop flow. Both files now state 10 of 12.)

## Unchanged since round 3

- **Runtime bytes and plan:** `materialize.py`, `changes.patch`, `prepared.json`, `parent_source/` and the five
  changed runtime files.
- **Check outputs:** `record_check.json`, `gate_contract_*.json`, `replay_gate.json`, every
  `ros_smoke_*_attempt*` output and `k5_harness/`.
- **The survey:** `evidence/clock_lead_survey.py` and `.json`.
- **Re-run, with identical output:** `check_change.py`, after N4.

# Response to independent review round 2 (`independent_review_round2.json`, passed)

Round 2 passed with no blocking finding and ten non-blocking ones. All ten were checked against the code and
records and fixed before the freeze. None of the fixes changes a runtime byte: the four source files and the
record keep their round-2 hashes. They do change the pre-registered analysis, the K5 harness script, a check
script and the freeze. So, as in v32 (edits after a review are reviewed again), the changed files go back to the
reviewer for a confirmation round.

- **N1, a stopped simulator is caught first by the applied-evidence check.** Confirmed in the code and the records.
  - **The code:** the node checks the applied snapshot's 2.0 s age before the gate, in `_watchdog_tick` and
    `_on_raw_command`. The worker stamps each snapshot at the step's start and sends it after the step's physics.
  - **The margin:** `evidence/clock_lead_survey.py` (new measure 5) pairs each step with its own step-end pose,
    counting steps whose step-end pose was superseded rather than measuring them. The pose arrived after the
    step's snapshot stamp in every step: at least 15.6 ms over 119,056 steps in 46 runs, and at least 45.0 ms in
    `v32_historical_full01`, the reviewer's figure.
  - **My first pairing was wrong:** it took the newest pose within each step's 0.02 s and gave negative minima.
    That came from superseded step-end poses, and `COMPONENT_RESULTS.md` records it.
  - **Corrected text:**
    - `PLAN.md`: "The simulation clock", and "What the simulation base means", which now separates a stopped
      simulator from a stalled pose path;
    - `PHYSICAL_RUN_PLAN.md`: "How the run ends";
    - `ros_smoke.py`'s docstring: in `trial`, check 4 models a stalled pose path.
  - **Pre-registered:** a backstop end without `applied_evidence_stale` is read as a stalled pose path with
    physics running, and it is checked with the applied reports.
- **N2, the exposure rule.** A gap now counts only when three conditions hold. The newest status sample before
  the gap is at most 0.5 s old and shows an admitted owner with the gate open; otherwise the gap is "unknown". No
  stop flow started before the gap. The observer's raw commands have no interval over 0.20 s across it, so the
  heartbeat was fresh.
- **N3, attribution.** The trip lag is the stop flow's start (`data.stop_flow.started_monotonic_s`) minus the
  newest pose's receipt. A lag of at least 1.98 s is the backstop, a shorter one the simulation age. Combined with
  N1. (Superseded after review round 3, N1: the lag is now measured from the start of the pose gap that contains
  the stop flow's start, or ended at most 0.1 s before it, and the threshold is 2.0 s.)
- **N4, the flag.**
  - **What it shows:** it now says only that physics ran while the backend's pose was frozen.
  - **What is reported for each flagged gap:** the commands physics received, from `telemetry.jsonl` and the
    observer's `gated_command` stream.
  - **A second measure, independent of the pose path:** the physics-time advance from `applied_sent.jsonl`
    (measure 4 in the survey). It is at most 0.06 s over the 122 recorded gaps with data, reproducing the
    reviewer.
  - **Terminal gaps:** they are measured by the second measure.
  - **Either measure over 0.25 s flags the gap.**
- **N5, fixed-name outputs.** `PHYSICAL_RUN_PLAN.md` now requires scratch copies or redirected, run-named outputs
  for every post-trial tool, naming the known fixed-name writers. v33's manifest is re-verified after the
  analysis.
- **N6, the K5 record.**
  - **(a) The guard:** `run_ros_smoke.sh` now exits explicitly if the attempt's log, JSON or harness copy exists.
    A scratch test refused an existing log and left it intact. No log had been overwritten.
  - **(b) Harness copies:** `k5_harness/` keeps the harness of each round-2 attempt. Attempts 01 and 02 were
    rebuilt by reversing the recorded edits and checked by replaying them forward to the attempt-03 file. The
    script now copies the harness before each run and checks it afterwards. (Since round 3, N3, the check also
    runs after a failing attempt.)
  - **(c) The cause of the `multi` failures:** it is now stated as a hypothesis.
- **N7, wording:**
  - (1) and (2): `PLAN.md` basis and evidence;
  - (3): the status-sample rate, 10 Hz simulated and about 4.6 Hz wall;
  - (4): C7's wall cases, where only green has a backstop field, in `PLAN.md` and in `REVIEW_RESPONSE_round1.md`
    (marked as corrected);
  - (5): `empty_long_route03` did end on `heartbeat_stale`;
  - (6): what the wall base does and does not change.
- **N8, two further relaxations in "What is lost".** Stale-pose commands act 2.5–3.5 times (corrected in round 3,
  N6: about 2.5–4 times) longer in physics
  terms when poses are lost while `/clock` advances. The `/clock` subscription adds about 60 callbacks a second to
  the backend's executor. The heartbeat is watched for it.
- **N9, `config_archived/`.** `freeze.py` adds its seven files to v33's manifest, so the trial's version gate
  checks them before physics. A read-only dry run of `freeze.py` from scratch selects 3,052 files, 7 of them from
  `config_archived/`. (Round 3, N5: the count depends on the files present at the freeze; the manifest records
  it.)
- **N10, the record check.** It now records a failure instead of crashing. Three mutants were detected in scratch,
  and `check_change.json` was unchanged by the fix. (Round 3, N4: an added or renamed row still crashed; fixed
  since.)

## Unchanged since round 2

- **Runtime bytes and plan:** `materialize.py`, `changes.patch`, `prepared.json`, `parent_source/` and the five
  changed runtime files.
- **Check outputs:** `record_check.json`, `gate_contract_*.json`, `replay_gate.json` and every
  `ros_smoke_*_attempt*` output.
- **Re-run, with identical output:** `check_change.py`, after N10. `evidence/clock_lead_survey.json` gained
  measures 4 and 5, and its earlier figures are unchanged.

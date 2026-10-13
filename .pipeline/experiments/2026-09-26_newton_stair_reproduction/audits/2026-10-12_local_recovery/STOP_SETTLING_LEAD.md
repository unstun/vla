# Parked stop-settling lead — no implementation or acceptance claim

Read during the unchanged v177 cohort, not used to alter that cohort.

The imported `runtime_sources/bridge/lite3_sim_bridge/run_pct_scan_building.py`
stance implementation at the STAND_SETTLING branch explicitly omits the per-leg
latch path. It requires all four feet >=10N continuously for0.25s, low body motion,
tilt<=10degrees and balanced average support before the2sPDtransition. While
waiting it continues the locomotion policy with zero commanded velocity.
Closed v175 failure traces show STAND_SETTLING during their late drift, but the
exact failing gate/contact history has not yet been audited. This is a lead,
not proof that the omitted optional path caused those failures.

A read-only sibling source contains an optional per-leg latch and a targeted
unit test for a fleeting four-contact instant:

- `/Users/sun/tongbu/study/phdproject/machine-dog/0_trials/2026-08-22/v17a28_mujoco_wasd/run_v17a28_mujoco_wasd.py`, `_update_leg_latches` near1420; default `leg_latch_enabled=False`.
- Sibling `test_run_v17a28_mujoco_wasd.py`, `test_per_leg_latch_enters_on_a_four_contact_instant_the_dwell_would_miss` near2048.

No source commit was selected, no code imported, no tests rerun, and no physical
qualification of that optional path was established. Do not enable it based on
this note. First audit recorded contact/settling reasons and distinguish
navigation terminal deadband, safety revocation, physical braking drift, and
standing-pose capture. Any future lower-controller change requires its own
version, pinned interface provenance and physical regression.

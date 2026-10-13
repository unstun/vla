# v133 failed pilot: turning and stop investigation

Stage: experiment + analysis. Authorized by Dr Sun to repair the latest failed
episode and repeat simulations on gpu5070ti. Local repository remains source of
truth; heavy reconstruction, builds and physics remain under
`/data/sun/vla_mppi_20261009`. No policy training or robot actuation.

Target: `v133_candidate_attempt02`. Preserve its immutable source and raw capture.
The final stop follows a loss of posture: about 2 degrees at 36.5 s, about
19 degrees at 37.5 s, and about 30 degrees after 41.7 s. Rejoining starts at
36.731 s and finishes at 36.991 s. The original one-second measured-stop window
never completes after the final stop. Do not relax it.

Ranked falsifiable hypotheses:

1. The restarted turn places feet over an unsupported edge or into architecture.
   Recorded forward kinematics against the exact scene must reveal the first
   support/collision change before body tilt; a support-aware path should avoid it.
2. PD-to-policy rejoin creates an actuator/history discontinuity. Replaying the
   exact state/control sequence should expose a discontinuity at that transition,
   before any geometry problem. A corrected transfer must remove it.
3. Tracker reference progression outruns the physical body after the stop.
   Recorded commanded motion and reference/body error must grow before tilt;
   repairing the responsible progression rule should prevent this in replay.
4. Stale input causes the initial loss of posture. Source ages must first exceed
   their original limit before the body tilts. If not, this cannot explain onset.

First read-only diagnostic reuses the verified Capture reader and actual frozen
Newton model shape/body indexing, recorded body states and original Building
triangles. It performs no physics stepping and feeds no truth into navigation.
Owned files initially: this audit directory only. A proven behavior correction
will use a new integer version with its own contract and fixed repeat protocol.

Acceptance: direct regression for the identified defect, unchanged original
safety/ownership/stop rules, then bounded sequential physical repeats including
all failures. Component success cannot stand in for mission acceptance.

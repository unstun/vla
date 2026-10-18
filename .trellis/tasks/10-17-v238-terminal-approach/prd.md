# Repair avoidable terminal-approach hesitation in the v237 recording

## User request and authorization
Dr Sun requests exact attribution and repair of the v237109–114.5s approach,
including planner failures/slow solves, zero commands and two observed stance
changes. Pass offline regression for that window while retaining the45–55s
stair behavior. Include >=0.5s low-speed episodes and split cumulative
hesitation metrics. No new physical run is requested or authorized here.

## Requirements
- Local VLA repo is the sole source of truth. Use gpu5070ti only as execution
 copy; preserve frozenv232/v237 sources, native install and all raw evidence.
- Preserve RL, original start/goal, ENV225,0.35m collision/support hard guards,
0.1s scans, dynamic/freshness/publication/stop and terminal acceptance rules.
- Independently verify pasted observations: separate actual failed rounds from
 successful cold solves and global counters from window-local events.
- Establish the measured command/velocity/stance and planner/safety causal
 timeline, with original clock mapping and source/point-cloud/map provenance.
- Fix the demonstrated native cause, retaining legitimate collision/invalid
 input stops. No new cross-module recovery protocol or threshold relaxation.
- Register the next logical candidate asv238; do not adopt it from offline tests.

## Acceptance
1. A reproducible pre-fix feedback loop shows the relevant native failure or
 avoidable expensive fallback and its stop consequence at a real seam.
2. Red/green regression exercises the actual failing code and recorded window;
 corrected native outputs pass unchanged support/collision/dynamics/epoch
 gates. Preserve45–55s reference behavior and existing affected regressions.
3. Audit reports raw measured low-speed intervals, >=0.5s and legacy>=1s counts,
 cumulative low time/window span and stance transitions. Motion between split
 episodes is not called stopped time; startup/final PD are separately labelled.
4. Post-fix replay does not produce the demonstrated avoidable stop in the
 captured terminal approach. Report reconstructed/native replay limits; only
 a separately authorized new physical route can validate changed real motion.
5. Return compact native tests, source/install hashes and exact cause report;
 keep clouds/maps/build caches remote. No physical rerun or shared-job change.

## Authorized physical continuation —2026-10-18

Dr Sun reviewed the offline result and authorized committing v238–v240,
then one complete original-route physical simulation on gpu5070ti. Use frozen
v240 with the v237 scanner deadline repair, unchanged RL/.35m/.1s/endpoints.
Execution binding isv241. No second physical attempt is authorized. Check
109–115s approach emergency and measured>=0.5s stops,45–55s stairs/stops/edge
margin, original route/arrival/PD. Return full video and v237 side-by-side.
Keep all failed evidence, report shifted route-relative approach separately,
and preserve selectedv232/v233 pending a separate adoption decision.

# v35 video-producing trial

Stage: experiment + analysis. Dr Sun authorized the trial on 2026-09-30:
"录制视频我看看". Run `v35_historical_full01` on gpu5070ti, with the v34
historical Building profile. Only the native candidate, planner YAML and
integration version change to v35. No added dynamic actors or training.

## Entry points and limits

`hosts/2026-09-29_gpu5070ti/v35_trial_run.sh` and
`checks/p1_gates_v35.py` are substitution-only derivatives of the frozen v34
files, recorded in `trial_derivation.json`. Same quiet-host checks, lock,
redacted host sampler, signal forwarding, recovery and returned-file manifest.
The runner keeps 600 s nominal physics observation, 1500 s goal wall budget
and 1800 s overall deadline. One run after physics starts; a pre-physics
infrastructure failure is retained and takes a new numbered run ID.

Current local source is the only source of truth. Before launch, freeze the
source/configuration and component evidence after two independent read-only
reviews. Verify every frozen source file on the execution copy, then P1
checks version identity, 99 archived runtime records, all 98 native source
and 516 installed-file identities, reviewed-candidate identity and scene inputs.
Use only the existing authorized execution environment and controller bytes.

## Recorded evidence and video

Return run logs, full-rate telemetry, actual recorded `video_states.json`,
run-bound source hashes and host records to the same local relative paths.
Render the heading-follow camera from those immutable states, without
additional physics steps. Deliver an ordinary MP4 under
`output/2026-09-27_lite3_versions/`, verify complete decoding, frame/state
identities and representative images. Provide a short viewing clip plus
the full heading recording; standard view is optional if informative.

Analyse nominal trigger intervals from `nominal_replan` log records,
new-trajectory arrival versus old expiry, command-zero intervals, final pose,
route progress and safety/failure reason. The fixed rate is nominal and urgent
safety replans can add attempts. A visible pause does not itself distinguish
handoff delay, failed feasibility, intentional braking or locomotion settling.

The pre-existing possibility of missing `stair_driver_result.json` is retained
as a reporting limitation; do not fabricate it or relabel an incomplete
observation as successful arrival. Earlier v34 evidence and videos remain.

## Abort and claim boundary

Abort only by SIGTERM to the trial runner PID; its inherited handler forwards
the signal and collects state. Do not signal `run_bounded` alone. A navigation
failure remains the one trial's outcome and still gets a video when states
are available. Component checks and video generation do not establish full
route, moving-obstacle or physical-robot acceptance.

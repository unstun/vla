# v247/v248 generic physical traversability — tested, incomplete generalization

The user-directed simplification is implemented and frozen. The nominal12x5
native component matrix admits55/60calls; all55use A* graph fallback, with
zero first-GPMP passes. Three predeclared single physical attempts were run
serially, without retries or case substitution. Only R11passes the complete
original spatial/arrival/PD gates. This is not generalization acceptance and
does not replace the selected v232/v233baseline.

## What was subtracted

See CLEANUP.md. v247starts from v240, restores the original PCT map instead of
v135's0.53m cost50mask, removes raw-cost/DecideLayer admission authority in
physical mode, associates real support floors before symmetric adjacency, and
shares the unchanged native0.35m support helper with SCAN. ENV225is the shared
soft clearance/terrain objective. No v244anchors/components/body-oracle recovery,
new endpoint relocation or Building-coordinate condition is composed.

The strict mask-only ablation leaves1337states isolated and still admits only
1/12requests; removal alone does not fix original PCT cost/transition coupling.
All source and installed regression receipts, the frozen60-call matrix and
fresh H00historical-route component control are in ../../versions/v247/RESULTS.md.
H00is not a new historical-route physical run. B09remains0/5; B08's independent
raw-solid reference margin is negative. The55/60figure is component admission,
not55whole-route collision-clearance proofs. No physical slope claim is made.

## Physical results — actual post-PD starts and live sensing

RLpolicy, exact requested scenarios,0.35m hard collision/support radius,
0.18m offsets,0.1s scan period and v237deadline implementation are unchanged.
All three actual generated profiles pass numerical/source parity. v248has25
passing ROS tests and requires observed ACTIVE states before goal dispatch.
Zero-step process preflight did not claim ACTIVE without TF.

| Case | Actual outcome | Native time s | Local successes/rounds during navigation | Pauses>=0.5s / >=1s | Min ENV extra edge m | Min raw-solid comparison m | Goal PD |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| A02 | FAILED | 19.801 | 0/0 | 1 / 1 | 0.150000 | 0.150000 | not reached |
| G07 | FAILED | 106.733 | 1690/1825 | 10 / 6 | 0.139742 | 0.093454 | not reached |
| R11 | PASS | 133.520 | 2902/2938 | 4 / 4 | 0.126883 | 0.060514 | PASS |

Pause scope is the measured goal-request through first actual arrived journal
observation; failed cases end at the last preterminal observation (100ms driver
sampling). Initial planning wait is included. Speed comes from20ms measured
horizontal velocity<0.05m/s. Final PD and shutdown are separate. Geometry and
floor-height windows are clipped to navigation, avoiding upstairs startup bias.
Margins cap at+0.15m. Independent raw-solid comparison retains the original
sqrt(3)*0.025m voxel padding; it is not a mesh-contact or foot-contact proof.

### A02 — actual start refusal, no route or spline

After factory PD, the measured start shifts about0.093m behind the nominal
pose. The actual oriented native support query returns11=SupportGap, not just
a refused rounded graph cell. Replaying the unchanged installed C++ graph from
the nominal pose passes both ways; the measured pose fails both ways (18states
in the requested direction). Native support is refused64/64navigation samples,
although ENV and raw-point margins cap positive. Soft margin must not override
this hard support-gap result. Do not add a connector that silently admits it.
The task closes FAILED normally; no native process crash. Full19.801sphysical
recording is retained and its entire timed display is delivered.

### G07 — near-end seed failure on the middle platform

The robot walks from the downstairs start to approximately
(7.703,6.483,3.357), then fails before the upstairs goal. The last native round
tries four local seeds; even an occ=0endpoint cannot produce an accepted
connection. The final round spends1.905msand never enters optimizer/refine/final
check. Continuous trajectory starvation reaches0.799561sagainst the unchanged
0.75sgate. Recovery GPMP attempts fail support-height association, and the
third graph candidate has2directed poses refused by shared native review.
The task closes FAILED without a process crash or scan deadline failure.

The throttled UnknownObstacle query near(2.774,2.133,4.833)belongs to a future
upper-floor route section, not the selected current local target. Logs select
a closer frontier and then near prefixes. It is not a proven root cause.
Actual body support is Free934/934samples and raw-solid comparison stays
positive. These endpoint/body checks do not prove the connecting edges and
planning headings are free. The precise first refused seed edge is not captured;
retain this as an open diagnosis, not an invented local-target or stale-input
fix. See results/G07_failure_log_excerpts.json and failure_attribution.md.

Navigation has10pauses>=0.5sand6>=1s; the complete floor-transition interval
has9/5. The raw45–55swindow has no>=0.5spause, but this does not establish a
smooth whole staircase. The recording ends106.733s;109–115sis unmeasured.

### R11 — one complete descending route, with pauses

Strict original request/spawn/continuous-state/arrival/PD gates pass. Final
XYerror0.120264m, height error0.007645m, yaw error0.113824rad. Final consecutive
FIXED_STAND suffix is4.370728swith policy ownership false; the original driver
also closes its measured2sarrival hold. The record ends133.520096s, with78.209m
recorded body path. No fall or process crash is recorded.

Whole navigation:2902/2938successful rounds,4pauses>=0.5sand4>=1s. Full
floor-transition interval:2289/2314rounds and2/2pauses; critical historical
stair geometry:327/328rounds andzero>=0.5spauses. Raw45–55s:252/259rounds,
zero pauses, minimum extra edge0.137305m. Raw109–115s:180/180rounds, zero
pauses, minimum extra edge0.138802m. These raw-time windows are retained for
review, not treated as route-equivalent segments across new endpoints.
Whole-navigation minimum extra edge0.126883m; independent raw-solid minimum
0.060514m. Native measured-body support is Free1192/1192samples.

## Delivery and evidence boundary

All four regular MP4s are in delivered/: A02/G07/R11new full recorded attempts,
plus the previously missing v246A02startup-failure prefix. Complete failed
recordings are not completed routes. All pauses and original first/last physical
states remain; startup follows recorded simulation time and navigation follows
original wall1:1time. No pose interpolation or new physics is used for display.

All four streams pass1280x720/30FPS/full decode locally and on gpu5070ti;
video SHA/size, causal source indices and complete endpoints agree with remote
proofs. local_video_verification.json and visuals/manifest.json bind the actual
local files. Twelve decoded delivery frames were inspected: bodies, scene,
curve visibility and terminal captions agree with each recorded outcome.
The inherited descriptive host-port string retains v240in one original field;
per-case native_binding_clarification.json records actual v247/v248source
identity without rewriting the original verifier output. Runtime install/config
receipts and video titles bind the actual treatment.

Compact return:209allowlisted files,2742030bytes, excluding all build/cache/raw
streams. Four videos total30032906bytes. return_manifest.json records each
returned report hash/source; all entries and video bytes were verified locally.
Original clouds, physics states, archives, compiler outputs and failed display
attempt logs remain on gpu5070ti. Raw roots and hashes are in each capture
snapshot/outcome; source/configuration and review videos are local. Reproduce
analysis with postprocess_case.py plus V248_CASE_ID, the original frozen native
layout and a fresh V248_RENDER_ID; never rerun physics under an existing ID.

v247manifest SHA:17a81d34d24628e4a2c2255abd8246df2261d8ba45ce8fc9ca5bf64b1c8e04a0.
v248manifest SHA:4e625f97400805258469ea43c90ab63f50709b5603c47870b77f3c799446cc40.
No current change is committed or archived; unrelated harness edits and v221
remain untouched. No baseline promotion is made. Keep this task open for
review of the remaining generic connection failure, GPMP fallback and real
post-PD pose coverage before authorizing further physical attempts.

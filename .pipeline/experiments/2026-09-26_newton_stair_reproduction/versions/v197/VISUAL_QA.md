# v197 visual QA — v196 Mac attempt 01

Stage: experiment + analysis. Display review passed for the recorded
v196_mac_full_attempt01 capture. Parent/native implementation: v196;
display parent: v195. The display executes zero physics steps.

The delivered regular MP4 has 3,880 frames at 1280 × 720 and 30 FPS,
129.333333 seconds, 12,028,789 bytes. SHA-256:
`7e063950f0a8974ddc4f49007ba17a307aeb86c9bd5ff2f4a97fe7e717b74f53`.
The remote copy has the identical size and hash.

Nine actual decoded MP4 samples were inspected in the
[contact sheet](returned/visual_qa/contact_sheet.jpg), with the final sample
also inspected at full resolution. Samples cover actual initial state,
factory zero-return and standing, navigation at approximately 30, 60, 65,
100 and 112.5 simulation seconds, and the exact final recorded state.
The robot, floors, stairs and rails are visible; the close following camera
keeps the robot in view. Cyan local splines and the orange global route are
distinct in the moving samples. At the 112.5-second low-speed sample the
cyan overlay is correctly absent, while navigation remains active. The
final sample is upright in the recorded held pose and reads
`Navigation: arrived (nav2_arrived)` and `CYAN: local SCAN (no active curve)`.
No blank frame, corrupted scene or clipped status caption was seen in
these samples. The light scene and robot appearance are inherited from v195.

All 3,880 frame source indices and curve/route/timing causal checks passed,
along with full video decoding and the encoded stream size/rate checks.
There are 332 startup frames using original simulation time and 3,548
navigation frames using original wall time at 1:1. The first physical state
is at time 0.0 with zero physics steps; the last is the original
126.58206176757812-second state. No interpolation, episode stitching or
pause removal occurred. Native local curves are visible in 3,256 frames;
global routes are visible in 3,507 frames.

The last recorded spline is #2923, ending at 121.9036976347492 simulation
seconds. At the final frame its zero command is stale by 4.814917 wall
seconds / 4.537506 simulation seconds. It is hidden. The raw final state
is FIXED_STAND, policy_owns_joints=false and command=[0,0,0].

The 10 overlay and four timeline tests passed. Original captured inputs,
parent manifests and source snapshots verified unchanged before/after
rendering. The unchanged physical full-route verifier passed separately.
The older analyzer's broader full_qualification=false is preserved because
sustained 30 Hz has not been established; it does not invalidate the
separate passed original-route gate.

This review covers one recorded simulator trial. It adds no repeated-route
reliability, collision-clearance or real-robot acceptance. The sample images
and hashes are in [samples.json](returned/visual_qa/samples.json).

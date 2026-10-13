# v76 current corner test and review video

Stage: experiment + analysis. Parent v74, exact native v63/runtime v59.
The logical change is post-run archival/video closeout: verify durable raw
storage before rendering. Planner, scene fixture, trajectory, final goal/yaw,
PVA/dynamics and safety/stop rules are unchanged.

The fresh Mac test completes 40,000 physics steps / 39.990 simulated seconds.
Measured path is 20.035 m and successful local frequency is 14.700 wall Hz
(483 successful / 485 completed chains). Median is 8.263 ms, P95 166.731 ms
and maximum 1,307.535 ms. The target corner-region maximum is 397.826 ms;
the largest 11-attempt corner round takes 41.318 ms. The overall maximum
occurs later on the stairs, with four attempts and 976.721 ms of inclusive
input processing. No measured pause exceeds one second; one original emergency
transition/current-curve-invalid event remains. No fall; goal active at the bound.
Copyback, native source/install and available Mac component gates pass. Full
qualification, uninterrupted continuity, arrival and sustained 30 Hz do not pass.

The review MP4 contains 982 causal frames, 32.733 s, 1280×720 at 30 FPS.
Full decode, original state/time/index verification and three-frame visual
review pass. [Video receipt](REVIEW_VIDEO.json) binds the actual physical run.
Raw/render data is archived and fully SHA/size-verified on gpu5070ti, with no
remote compute job. See [comparison/report](../../audits/2026-10-04_corner_start/REPORT.md)
and `mac_trials/attempt01/v76_mac_trial01_attempt01/analysis/` for plots/metrics.
v48 remains the runnable reference; v49 is excluded; no commit is made.

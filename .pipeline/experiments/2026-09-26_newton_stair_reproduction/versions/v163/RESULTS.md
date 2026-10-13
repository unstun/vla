# v163: component pass, physical failure retained

Stage: experiment and analysis. The Nav2 BT can remember and restore an exact
previous PCT reference. The gateway allows its binding only after explicit
`pct_no_route`, a matching measured-stop release, and unchanged mission, goal
and map. Binding permission is consumed once. No new PCT result is fabricated.

The parent gateway regression fails three assertions. The candidate passes
nine production callback tests with mocked PCT/IO, two BT cache tests, the
existing terrain test and 18 host tests. The actual running BT library was
verified. Source is frozen: 3,695 pairs and 618 runtime inputs.

The first full Mac run FAILED after 27.067 m, without a recorded fall. The new
reference-reuse branch did not trigger. Global routes were admitted, but the
robot could not obtain a first local curve after stopping on a stair. All six
mission retries were consumed. This is not physical validation of reference
reuse. All 291 raw files are remotely archived and verified (see the receipt).

A diagnostic replay uses 545 recorded published scans, the original map and a
body sample at 65.615570068 s, queried at 65.620568 s. The stationary body is
clear, but every near-forward 5 cm segment is blocked. 33 of 65 sampled planar
directions pass the original native segment check. The actual parent FSM
fails all six reference prefixes. This ordered reconstruction does not restore
the original asynchronous map publication or executor schedule.

v164 expands the bounded steering proposals and tests that exact replay. The
raw source remains v163; do not retroactively relabel the failed physical run.

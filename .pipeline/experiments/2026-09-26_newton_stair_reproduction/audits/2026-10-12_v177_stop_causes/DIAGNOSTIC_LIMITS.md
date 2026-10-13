# Diagnostic boundaries and retained failed probes

No production navigation source/configuration changed. No new physical route,
training, or real-robot actuation was performed. v177/v178 remain frozen.

`results/` binds all 35 native revocation messages to matching first cancellation
messages, by owner and reason: 30 recovery events and 5 successful final stops.
`windows/` and `windows02/` are successive read-only extractions. The latter adds
optimizer start/seed failure counts; the former and its executed script remain
available with original hashes. Log-window selection uses interpolated realtime
to simulation-time anchors. Exact safety ages use source/message stamps, not
that interpolation. Nearby log messages are context, not automatically the cause
of a matched rejection.

Remote native replay did not start: resource admission reported 14,991,163,392
bytes available and three other Isaac processes, below the original 20 GiB
physical-run rule. Existing artifacts were read/exported at low priority; native
checks were moved to a local Mac container limited to 2 CPUs and 4 GiB with no
network. A later SSH interruption affected a redundant second input export; the
already returned and verified first export supplied every final local check.
No claim is made about why SSH was interrupted.

The first local probe (`native_replays/`) loaded B-spline points transposed
(N x 3 instead of production 3 x N). Its six curve cases returned diagnostic
status 2 and asserted (exit133); those are **probe defects, not production
crashes**. Four body-only cases completed. Preserve the executed C++/Python
sources alongside their hashes. The second probe corrected the matrix layout
and rejects malformed curves before evaluating them; all six curve cases
complete normally in `native_replays02/`.

The first input selector also used the last asynchronous safety timer message
for some stalled snapshots. That message can stop updating while the controller
continues its independent checks. In particular the first attempt's 65 s probe
selected a 5.9 s old cloud; it is not evidence of a 5.9 s old live controller
map. Corrected long-stall probes explicitly use a controlled fresh prefix at
least150ms before the selected body time. The three controller rejection probes
retain their exact recorded observation stamps.

Ordered sensor reconstruction preserves recorded points, poses, static maps and
native predicates, but not original DDS batching, asynchronous snapshot order
or Linux/Mac floating-point identity. In the three fresh rejection cases it
reproduces the original first-collision phase and sample count (1561,1360,1).
This supports the identified rejection conditions; it is not a new complete
episode or a bitwise asynchronous replay. Four stopped-body checks identify the
same static negative-mask veto, which does not depend on map arrival timing.
The last of those body probes also has stale input; only its independent static
mask finding is used, not its total occupied/headings result.

Safety publication contains a boolean rather than detailed rejection enums.
For20events, source age exceeds the250ms gate while the observer has newer
frames. This establishes a sufficient freshness violation. It does not prove
that no geometric rejection coexisted, or pinpoint all missing latency to
mapping computation versus input consumption, scheduling or publication-lock
waiting. The latter requires separate timing instrumentation.

The drift analysis uses original ~20ms telemetry. Sampled gate-duration estimates
are not full-rate physical acceptance. The recorded stance state/reason and
effective commands directly establish that the observed span remained in
STAND_SETTLING despite zero commands. The static gap sweep uses the unchanged
production mask on the recorded body pose, not ground-contact or collision-force
labels. A mask violation is not itself proof of a physical fall or wall contact.

Upstream source inspection is `surveyed`, never `reproduced`, `integrated` or
benchmark-qualified.13repositories and their exact pins are recorded in the
linked survey. No stop/freshness/support threshold was relaxed.

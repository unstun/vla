# Diagnostic boundaries and rejected leads

The v165 attempt01 ordered native replay uses904retained scans, query time
101.576080322s and the original map. Body position[7.886857,6.378124,4.832431],
measured yaw2.565327rad is clear. Reference admission succeeds. Six ordinary
prefixes and the v164 steering proposals fail. Do not describe this case as
an invalid current footprint or a pre-admission failure.

A native5cm backward proposal succeeds without changing the map or thresholds:
0.607s,306samples, full fixed-heading collision/PVA/dynamics checks pass.
Intermediate in-place headings are blocked by the support-gap mask. The current
tracker instead tries to face the motion tangent, motivating explicit short
reverse-prefix intent in v167. No robot motion occurred in that replay.

Other leads were checked but do not support a change:

- No lateral command saturation in local v160/01, v163/01 or v164/01. Their
  maximum absolute raw lateral commands are below0.35m/s. Do not change component
  velocity clipping based on the unconfirmed corner-cutting hypothesis.
- v165 runs01-03 have maximum pacing lag about0.277s and maximum20ms-window
  catch-up ratio1.47-1.49, concentrated at startup11-12s before the navigation
  goal. No interval exceeds1.5. This is not evidence that mid-route failures
  are caused by a large physics catch-up burst; no pacer change was made.
- v165/04 aborted while binding the telemetry listener before navigation. Its
  prior socket owner was not retained. v166 reproduces the Linux self-connect
  failure class and moves service ports outside the actual ephemeral range;
  that does not prove which socket caused the historical failure.

The replay is an ordered map reconstruction with a fixed diagnostic clock, not
an exact restoration of asynchronous publication or scheduling. Keep all failed
runs and distinguish component feasibility, actual command evidence and full-
route acceptance.


## v175 full cohort: short-prefix completion is not the observed blocker

The older v172 stair traces show a real endpoint issue: a5cm prefix can finish
with8–11cm targeterror and then emitzeros under the generic15cm completion
radius. Applied commands did reachRL; the stand-release deadband is0.001,
so a high release threshold is not supported. Keep this issue separate.

All three v175 failures instead have zero published recovery curves after their
final stop (02 generations6–10,03 generations7–11,05 generations2–7). No reverse
curve is published in those owners. Changing endpoint tolerance cannot explain
or directly repair these missing first curves. Replay their actual maps/poses
and reference paths before selecting another execution change. No v176 change
has been made from the short-prefix hypothesis.

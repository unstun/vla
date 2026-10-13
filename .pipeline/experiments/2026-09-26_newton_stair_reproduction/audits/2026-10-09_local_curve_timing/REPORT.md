# Native local curve video and timing HTML

Stage: experiment + analysis. Dr Sun requested the actual local planning curve
in the simulation video and an HTML computation-time plot. Delivered the offline
HTML and standalone MP4 under output/2026-10-09_nav2_local_planning/delivered/.

## Recording gap and bounded reruns

The previous v114 successful recording contains zero Bspline events. The observer
subscribed to /planning/bspline while the Nav2-owned native worker publishes
/quad_0/planning/bspline. Seed logs are not final optimized curves and were not
substituted. v116 changes the recorder only: correct curve topic plus cancellation
and safety events. Native source/install receipt, scene, sensor, planner parameters,
policy, clocks and validity limits remain exactly v114. Actual isolated Foxy DDS
regression: previous recorder0 curves; repaired recorder3 byte-identical messages;
three cancel and three safety events also recorded.

Attempt01 recorded774 native curves but failed at an applied-command acknowledgement
timeout and mismatched final copyback; all failed bytes retained. Attempt02 completed
recording and verified applied-state copyback, but navigation FAILED after three
protected stop/retries. This is not the earlier successful run. It travelled23.561m
with no reported fall, actual RTF0.999362. No navigation repair was attempted here.

## Delivered visualization

v117 establishes causal curve selection, camera and report. It passed data checks,
but the thin curve was difficult to distinguish where it overlapped the global
route. v118 adds0.025m display spheres at the same150 native-spline samples;
no curve coordinates, scene, states or dynamics change. The cyan local curve is
clearly visible over the thin orange global route. The initially wider following camera introduced start-frame wall occlusion.
v120 restores the qualified close-follow camera while retaining the thick curve;
start/stair/final robot visibility is directly checked. The video is53.366667s/1601frames at30FPS,
1280x720, actual recorded-wall1:1 replay without state interpolation or new physics.

Curve selection requires the exact controller admission and owner identity, only
uses events received before the displayed source state, observes cancellation,
rejects emergency-hold curves, and clears if that owner's output is older than
its original100ms lease. The newest accepted plan can replace an older command
between controller ticks; a displayed plan is not labelled an executed path.
903 video frames show the local curve.904 raw spline messages comprise895 normal
curves and9 emergency holds; the emergency holds are not counted as moving curves.

v119 fixes causal seeking; final v121 builds the same offline single HTML with embedded MP4, actual Matplotlib SVG plots,
linear/log scales, tooltip data, raw CSV download, playback cursor and click-to-seek.
The seek regression covers all900 actual rounds and selects the first recorded frame
after completion, avoiding a30FPS frame whose underlying state predates the result.
The currently displayed latest result can already be a subsequent faster round.

The chart uses all900 recorded complete scheduled planning rounds (895 success,
5 failure), not message periods/FPS. Median1.5802085ms, P95 4.08086665ms, maximum
138.781625ms; six rounds exceed the unchanged33.333ms/30Hz budget. All900 native
starts pair with900 results. Gaps remain gaps, not zero-time calculations. Wall
clocks use the original converged Mac/Linux clock mapping. Source CSV and video
hashes are embedded in the report. No smoothing or hidden peak clipping.

Final video: v120. Final HTML: v121. Intermediate v117–v119 outputs remain
separate; the physical recording and all timing/curve selection data are unchanged.

## Validation and limitations

Four curve-selector/native cubic sampling tests pass; the full1601-frame data
replay contains no future curve events. The adapted renderer parses, frozen source
checks pass, complete video decode passes, and the stair frame at15s visibly shows
cyan SCAN409. Browser tests confirm logarithmic display, peak seeking, slider at15s
showing curve409 and1.20ms, with no console errors. Embedded MP4 bytes exactly match
the standalone delivered video. The HTML works without CDN/external media.

This is a visualization delivery, not repeated-run navigation acceptance or Jetson
validation. The earlier v114 success remains separate. v48 reference and the main
30Hz/continuity task stay unchanged. Raw attempts are archived on gpu5070ti, storage
only; see STORAGE.json. The local runtime is retained, with no broad staging,
commit, index-lock removal, real robot actuation or subagents.

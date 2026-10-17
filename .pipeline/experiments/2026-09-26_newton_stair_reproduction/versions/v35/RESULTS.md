# v35 trial and video results

Status: frozen, executed on gpu5070ti, videos delivered; **navigation failed**.
Parent: v34. Native build: `runtime/scan66_periodic_replan_v35`.
Component checks and failed test-setup attempts are preserved in `COMPONENT_RESULTS.md`.

## Trial and identity

Dr Sun requested this recording on 2026-09-30. Independent read-only spec and
standards reviews passed. The freeze-identity gap found by review was corrected
and tested without another planner-source change. Frozen source/evidence:
**3,752 files**. Pre-physics sync: **4,269 files**, all SHA-256s equal. P1 version,
99 archived runtime records, 98 native sources, 516 installed files, candidate
identity and 36 scene inputs passed.

Single run: `v35_historical_full01`, historical Building profile on gpu5070ti,
CPU Newton physics, no dynamic actors, factory/PD stance control. No retry
occurred. Recorded physics: **561.512634 s**, 27,452 control steps and 5,490
sensor frames. Wrapper exit **1**, without timeout, after **1189.84 s wall time**.

End: **`native_replan_exhausted`**, after 1,000 consecutive planning failures.
The actual driver-final record exists and records failure/stop flow; v34's
missing-final-record limitation does not apply here. Final body:
**(7.80118, -4.08341, 1.83764) m**, XY goal error **5.94845 m**. Final fixed
stand: **489.74 s**. Minimum base-up z **0.94950**, above the existing 0.5
no-fall threshold. No arrival.

Return: **5,602 run/host files, 2,597,095,811 bytes**, every SHA-256 matches.
See `video_preparation/2026-09-30_v35_delivery/full_return_verification.json`.

## Scheduling and observed pauses

The raw native log contains **1,080 nominal attempts**. Interval: minimum
**0.500202 s**, median **0.503540 s**, maximum **1.434212 s**; none below 0.5 s.
This confirms the 2 Hz nominal gate, not hard real-time execution. Safety
attempts are separate and may occur between nominal attempts.

Using the same exact-zero three-axis command predicate and 0.3 s minimum
duration, after first motion at 12.2813 s:

- No qualifying zero-command interval occurs before **54.2618 s**.
- At the east-end corner, nine short intervals between **54.2618 and 59.7188 s**
  last **0.340-0.560 s**. Forward/restart pulses continue afterward. Brief
  pauses have not all been eliminated.
- The final continuous zero-command interval starts at **63.0370 s** and lasts
  **498.476 s**. Fixed-rate scheduling did not solve corner feasibility.

The body passes the former corridor entry at **32.129 s**, passes x = -4.0
on the upper floor at **33.223 s**, and reaches route pose **207/631** at
**62.517 s**. There are 80 native full-curve-clear log entries, 7 final curve
rejections (status 1), 18 first-three-control-point failure messages and 118
A* budget hits. Aggregate counts alone do not identify the corner root cause.
See `nav_progress.json` and `observed_metrics.json` in the dated preparation
folder.

## Existing result review

Both original reviewers ran on the execution copy, where recorded Linux
paths resolve. The Building result is **`passed: false`**. Source identity,
continuous physics, actual motion, PD gains, no-fall and measured-stop checks
hold; process/driver completion, arrival and goal-position checks do not.
Returned reviewer JSONs are in the dated preparation folder. Video generation
is not navigation acceptance.

## Videos

Ordinary H.264 files, 1280x720 at 12.5 FPS, under
`output/2026-09-27_lite3_versions/`:

- `v35_historical_full01_heading_preview_100s.mp4`: 1,250 frames, 100.0 s.
- `v35_historical_full01_heading_full.mp4`: 7,000 frames, 560.0 s playback,
  ending at recorded physics time 561.512634 s.

Both have complete decode checks and use source states SHA-256
`1ceeb4511bb9f31260e9ed10caa8c7c0d1eef655defebcedbedb5952f020bdfc`.
No additional physics step occurred. The preview supplies the existing
renderer's display limit through an adapter because the heading wrapper drops
extra argv; its executed source/derivation are kept. Its first 1,249 PNGs
match the full render exactly; the final preview frame has identical scene/top
overlay pixels but a footer marking the end of the preview observation. All **8,250 frames** and **3,752 frozen files**
were rechecked with no mismatches. Frames 250, 650 and final 6999 were visually
inspected. The final frame names the actual failure. `video_receipt.json`
records video/state hashes, decoder and frame checks.

Useful viewing interval: **0:15-1:05**, particularly the turn and short stops
around **0:54-1:03**. Raw evidence and older versions remain. Last accepted
navigation condition: v3's empty 12 m floor. Human visual feedback is pending;
no v36 change, commit or push.

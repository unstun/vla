# v34 trial and videos: entry passed, east-end corner still blocked

Stage: experiment and analysis. The single `v34_historical_full01` trial ran on
gpu5070ti on 2026-09-30. It crossed the former corridor-entry stop, reached the
corridor's east-end corner, and did not arrive before the bounded observation
ended. **v34 remains frozen and unvalidated.**

## Source and execution

- K5 passed in the independent read-only review. The two nonblocking document
  findings were corrected before freezing; `independent_review.json` retains
  the original verdict and `independent_review_amendments.json` the corrections.
- The skill's old model and the local configured model were rejected by the
  CLI account. The completed review used the catalog-listed `gpt-6-astra`.
  Attempts and Dr Sun's one-review authorization are preserved in the review
  execution record. No private controller, model or media data was authorized
  for that external review.
- The freeze contains 3,548 files. Local source and snapshot hashes matched.
  All 5,381 synchronization files matched on gpu5070ti, and P1 passed the
  version, 99 runtime-record, native-source/install, candidate and scene gates.
- The reviewed runner started the trial at 07:32:08Z. It recorded exit 1 after
  1,277.68 seconds of wall time, without its 1,800-second deadline firing.
  Physics reached 600.51654 seconds, with 29,449 control steps and 5,889 sensor
  frames. This is the one outcome; there was no second physical trial.
- The runner's manifest self-check passed and no container remained. All
  5,998 original manifest files returned to the local project with matching
  SHA-256 (`video_preparation/2026-09-30_v34_delivery/full_return_verification.json`).

## Observed outcome

The pre-written `analysis/nav_progress.py` analysed the captured observer
records and SCAN log, writing a new output outside the frozen file set:

- The corridor entry was crossed at 36.0768 seconds; the longest stay in the
  old entry box was 0.655 seconds. The body passed x = -4.0 at 37.0663 seconds.
- The farthest matched route pose was 206 of 631, at 113.3044 seconds. This
  meets the pre-registered east-end-corner observation, not a claim that the
  robot cleared that corner.
- Final body position: `(7.74193, -4.04738, 1.86520)` metres. Final XY goal
  error: 5.88362 metres. The final uninterrupted `FIXED_STAND` interval was
  454.267 seconds.
- Minimum recorded `base_up_z` was 0.953145, above the existing 0.5 no-fall
  threshold. Architectural collision acceptance was not established.
- Startup fill matched the contract: 86,775 navigation layers, 17,214 added
  and 22,785 rejected by the drop guard.
- SCAN logged 0 inside-obstacle messages, 1,765 first-three-control-point
  messages, 7 final-curve rejections, 4,457 A* time-budget hits and 887 replan
  cycles. Its replan limit did not fire. These signatures do not identify the
  corner's root cause.
- The unchanged v33 timing analysis found no pose gap over 0.25 seconds and
  no stop flow. It supplies no exposure evidence for stall tolerance.

The original worker reported that the long route did not finish. Its final
backend still had an accepted active owner, with no terminal arrival and no
`finish_request`. This outcome must not be renamed `native_replan_exhausted`.

## Missing final driver record

`artifacts/stair_driver_result.json` is absent in the original run. The
unchanged common reviewer failed at that read, before emitting a verdict;
the Building reviewer then lacked the common report. Both stderr records are
preserved in `video_preparation/2026-09-30_v34_delivery/reviews/`.

No replacement driver record was fabricated. No complete Building-review
pass is claimed. The direct metrics above come from the verified captures;
the missing record and corner stop remain follow-up items.

## Video delivery

Two render attempts failed before the first frame because the restricted
macOS process saw an empty Cocoa screen list. Their logs remain in
`runs/v34_historical_full01_video01` and `_video02`. The same unchanged
renderers succeeded with normal display-service access under new render IDs:

- `_video03`: heading-follow view;
- `_video04`: standard fixed-spawn-heading view.

Both read the same state SHA-256
`e9dad7eeeece831b96c7ec5de854d7a2914a9917201c28946e21e56376405692`.
They performed zero physics steps. Each full MP4 contains 7,499 frames at
12.5 FPS, 1280×720 H.264, and is 599.92 seconds long. Full decoding passed;
all 14,998 PNG hashes matched. The 3,548 frozen source files still matched
the manifest after rendering; source and snapshot both matched at freeze time.

Ordinary delivered files under `output/2026-09-27_lite3_versions/`:

- `v34_historical_full01_heading_preview_100s.mp4`: first 1,250 heading frames,
  100 seconds of playback, to physics time 100.0167 seconds;
- `v34_historical_full01_heading_full.mp4`;
- `v34_historical_full01_standard_full.mp4`.

See `video_receipt.json` and the preview receipt for hashes. Checked frames
show the climb, corridor approach and the final stand. The heading view keeps
the robot visible at the stop; the standard view is partly blocked by a wall
there. Prefer the heading view for Dr Sun's visual feedback. The final frame
labels the bounded observation as not arrived.

Raw captures and render frames remain at their project paths. Exact narrow
ignore entries, byte counts, hashes and restoration instructions are in
`LOCAL_ONLY_BYTES.json`; no files were deleted.

## Boundary and next step

The entry improvement is observed in one trial on gpu5070ti. The whole route
is unsuccessful, and v3's empty 12-metre condition remains the last accepted
navigation condition. The videos are replay visualizations of actual logged
physics; they do not claim live rendering or real-robot execution.

Await Dr Sun's visual feedback. The corner stop and missing final driver
record have not been repaired here. A later logical code/configuration
change must preserve frozen v34 and use the next integer version.

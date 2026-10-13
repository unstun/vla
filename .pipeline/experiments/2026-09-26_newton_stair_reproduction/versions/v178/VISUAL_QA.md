# v178 review video QA

Inspected returned frame000000 (original physicaltime0 factory startup),
002435 (mid-route recovery with no active curve),004870 (arrived hold), and
decoded frame1500 (video50.00s, native50.24s). The latter visibly shows the cyan
controller-admitted localcurve1049, orange global path and latest completed
solve6.17ms. Blank local curves during stopped/revoked periods are preserved.

The full video is162.366667s,4871frames at30fps,1280x720. All frame-source indices,
startup simulation timestamps, navigation wall timestamps, curve causality and
full decoding passed. It replays the first actual v177 run without any new
physics steps, interpolation, stitching or skipped pauses. Final status is
arrived (Nav2 action status4). The first recorded state is physicaltime0 at the
original spawn, not a renamed late-route segment.

The inherited long descriptive footer is cropped at the right edge; the status,
version, clocks, curve legend, trajectory identifier and solve time remain clear.
This minor display limitation does not alter the recorded route or its evidence.

Regular local MP4: `delivered/v177_full_route_attempt01.mp4`,19986833bytes,
SHA256`2315e907b8e3c28e72733d69bfce64737b32b63e0a24594e641af8c333877854`.
The returned video and verification records match their remote hashes.
The first trial contains12recovery handoffs; it was selected before completion of
the cohort, not selected for the smoothest appearance. The separate five-run
cohort passed5/5 with30qualified handoffs; this one video alone is not that proof.

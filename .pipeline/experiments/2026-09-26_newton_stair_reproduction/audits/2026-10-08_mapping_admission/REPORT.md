# Mapping admission and separated execution: measured decision

Date: 2026-10-08. Stage: experiment + analysis.

Both requested investigations have executable, locally returned component
evidence. **Newest-only mapping is rejected for navigation adoption.** The
three-lane prototype passes its component checks, but is not integrated into the
physical navigation runtime. Continuous navigation and strict 30 Hz remain open.

## Plain-language result

The mapper can catch up faster by skipping old scans, but those scans can contain
an obstacle that later scans do not contain. Our actual map comparison loses
occupied evidence, and an explicit native transient fixture demonstrates the
miss. Also, a newly completed fresh map does not make the preceding map fresh
throughout a processing stall.

Separating sensor inspection and execution decisions from the slow map works in
the bounded prototype: both continue running while mapping is intentionally
stalled. They correctly reject execution when original evidence becomes stale.
This prevents interpreting healthy callback cadence as permission to move, but
does not itself make the mapper fast enough or qualify moving-robot safety.

## Direct evidence

- [v84 comparison](../../versions/v84/RESULTS.md): six identical-input native
  mapping arms; 188 frames; unchanged full-frame baseline hash; skipped-obstacle
  negative. Blackout latest skips 12 frames and loses 173 occupied cells;
  timer/latest skips 16 and loses 252 in the durable attempt.
- [v85 prototype](../../versions/v85/RESULTS.md): 26 contract checks; all 188
  frames retained; six sensor callbacks and nineteen execution decisions during
  each of two 650 ms mapper stalls; zero checked stale-map allowing decisions.
- [Upstream survey](../../../../survey/2026-10-08_mapping_backlog_upstream_survey.md):
  exact source pins distinguish scheduling adaptations from whole upstream
  reproductions. Original SCAN and ROG mechanisms are references, not replacements
  whose behavior has been validated on Lite3.

## Next concrete integration boundary

Keep every distinct observation until an alternative proves obstacle/clearing
retention under non-repetitive LiDAR coverage. Preserve the 250 ms threshold.
The next runtime change must bind the sensor veto to the original accepted
full-trajectory geometry and P2B owner/stop path. Its acceptance needs moving
obstacles, stair support, cancellation/hold, invalid clocks and frozen physics
evidence. Source-level separation and a stationary-body veto are insufficient
for that promotion. No speculative runtime adapter was enabled after these
negative findings.

## Runtime and preservation

Executed on Mac using pinned ROS Humble image
`sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb`,
linux/amd64, three CPUs, 5 GiB, network disabled. Native v82 source has 102 files;
all match the local source and built copy. 309 installed files and the three
probe executables are hashed in the build receipt. No remote GPU computation,
physics integration or robot command publication occurred.

The first temporary environment disappeared after a deliberate turn interruption;
its cause is unknown. No task cleanup command had run. Tool-observed numbers and
failure boundaries are retained under v84/failures. The bounded tests were
recreated from the original verified remote archive, and every completed arm
was immediately copied into its version directory. Durable attempt02 supports
the report. Storage manifests and restoration commands accompany the archived
raw results and exact component runtime.

# v284: execution complete, repair not accepted

Frozen v284 completed the exact 50+3 offline cohort and ten once-only Newton
physical attempts. Hard radius 0.35 m and scanner period/deadline 0.1 s remain
unchanged. No native/execution edits or actual retries occurred after freeze.

Offline full chain: 48/50 legal, 3/3 illegal. Global median 1.649325 s: timing
unmet. User explicitly authorized continuing with that timing failure retained.
All non-timing offline criteria and ten zero-step preflights passed.

Three routes pass arrival plus terminal PD (S04, CM07, CS03), but only CM07 also
passes measured support/source/raw geometry. S04 and CS03 still have source
solid excursions of 5.155 and 3.465 cm. Seven routes fail with no executable
SCAN trajectory while their measured prefixes are geometry-clear. Global
endpoint/shared-no-route rejections are absent and all ten references keep
one epoch and original geometry. These component improvements do not establish
successful physical navigation.

See [full report](RESULTS.md), [offline results](OFFLINE_RESULTS.md), and the
[confirmed observations](../../audits/2026-10-19_v284_static_continuity/OBSERVATIONS.md).
Ten real local MP4s and complete failure evidence are linked in the report.
Task remains for human review; no baseline promotion or commit is implied.

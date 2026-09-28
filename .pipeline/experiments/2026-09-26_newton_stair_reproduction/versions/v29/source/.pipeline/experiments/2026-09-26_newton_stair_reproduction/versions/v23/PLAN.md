# v23: use the explicit qualified source for all terrain-return classification

Stage: experiment + analysis. Parent: v22. One native behavior change.

When the extra static surface topic is configured, use that qualified source
for both the existing floor-band and paired-tread riser rules. Otherwise retain
the original selected source. Do not OR the two predicates. Both inputs must
pass the existing freshness and layout gates before measured cloud ingestion.

The scored navigation support, original navigation map, raycasting, nonterrain
history, unknown handling, footprint, speed settings and all numerical
classification thresholds remain unchanged. No obstacle type or actor pose is
provided to the native planner. This change applies the existing geometric
rule; it does not establish a new semantic rule for mapped low protrusions.

Validate the actual compiled implementation against old stopped-state fixtures
and the v21 stop, including a repeated successful continuation, complete-curve
collision checks, endpoint PVA, and fail-closed inputs. Compare all eight
unmapped obstacle fixtures exactly with their preceding outputs. Report mapped
low-protrusion cases separately under the still-pending acceptance policy.
Only after these pass, run the short physical Building route, verify measured
stop and artifact copyback, and bind any video to this frozen version.

# v159 select original due body measurements

Stage: experiment + analysis. Native/host parent v158. First v158full Mac route
failed without entering steering recovery; two actual observation-age faults
and a TF/body sample10msahead of the controller clock consumed retries.
The recorded mismatch is83.120948792s current versus83.130943298s source.

Reuse the existing native BodyTimeBuffer in the controller. Queue future
measurements unchanged, select only the latest already-due original pose/twist,
and enforce the same100ms freshness gate before tracker/native validation.
No time rewriting, interpolation, expired pose, future pose or cached safety
permission. Invalid frames/values, regressed future-delivery stamps, overflow, negative safety
and owner/stop handling still fail closed. Cleanup clears the input buffer.

Actual plugin regression must fail on the parent and pass on the candidate;
retain the existing1ns-future-without-history and100ms-expiry tests. Native
planner/steering libraries stay byte-identical in a verified v158underlay;
build only the changed controller overlay, verify actual package selection,
then freeze before original-start physical testing. Other observation-age
faults remain real and are not waived.

The first overlay test found that applying the raw-source queue to ordinary
historical TF queries would reject an already-supported80ms-old pose. Keep
ordinary due inputs unchanged; use the queue only for future deliveries. The
existing delayed-ticket test remains mandatory and unmodified.

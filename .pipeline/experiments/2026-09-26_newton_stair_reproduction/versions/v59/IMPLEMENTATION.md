# v59 timing implementation

The manager derives an optional origin from the current old curve's timestamp and requested sample time, after checking layout, clock, current lifetime and exact sampled PVA. That stack-owned origin is passed through the synchronous warm/native/fixed-height attempts. Every original optimizer, PVA, dynamics and newest full-curve safety check still executes. A successfully checked curve retains the sampled epoch; a candidate whose valid time has already elapsed cannot be committed. This has no wall-time budget and creates no stop reason.

The actual controller receipt callback computes elapsed time from the same epoch instead of resetting every non-emergency curve to zero. Emergency curves retain zero phase. All subsequent command, freeze/resume, cancellation, final-goal and final-yaw function bodies are exact parent bytes. Malformed timestamp fields are ignored before mutation to prevent invalid time construction.

Analytically identical consecutive curves must match P/V/A at the same handover instant. Reoptimized curves share their original hard-PVA boundary; their later common-time P/V/A differences are measured separately and not misrepresented as exact geometrical equality.

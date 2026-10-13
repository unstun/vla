# v74 corner-start observation

Stage: experiment + analysis. Parent v70, exact native v63 and runtime v59.
Only the explicit corner fixture/profile changes the starting condition; final
goal, physics, policy, sensors, controller and safety/stop rules remain.

The actual 40,000-step Mac recording reaches 39.990 s and travels 19.651 m.
582/582 completed rounds succeed, with 16.990 successful wall Hz, median
8.878 ms, P95 87.012 ms and maximum 720.812 ms. The immediate corner-region
maximum is 534.749 ms. No measured pause exceeds one second; one emergency and
one current-curve-invalid event remain. Goal remains active at the bound;
30 Hz, arrival and full continuity are not validated. State copyback passes.

Frozen source, build/entry receipts and compact analysis survive. The original
temporary raw root became unavailable following interruption before durable
video closeout; this task issued no cleanup of that root. Do not claim an
archived source or video for this attempt. v76 repeats the same physical/native
configuration with immediate durable archival and provides the actual video.
See [corner comparison](../../audits/2026-10-04_corner_start/REPORT.md).

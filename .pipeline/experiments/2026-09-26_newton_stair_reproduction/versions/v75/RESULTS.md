# v75 upstream corner attempts

Stage: experiment + analysis. Parent v74, exact v71 pinned upstream ROS2 probe
and original runtime v59. The physical fixture and external controller/backend
rules are retained; upstream native planning rules and scheduling differ.

Six-package build and all six actual native transport/cancel checks pass.
Both physical attempts fail on the existing AppliedClient receive/ACK path and
final state copyback. Frozen source and local failure/build/entry logs survive;
the temporary raw roots became unavailable following interruption. No completed
navigation, stop, 30 Hz, durable raw archive or video is claimed for these
attempts. The previously inspected first log showed 14 successful chains and
brief motion; it must not be described as producing zero moving curves.

v77 repeats the upstream corner condition and durably archives the actual
partial recording before rendering, preserving its physical failure status.
See [corner comparison](../../audits/2026-10-04_corner_start/REPORT.md).

# v84 native admission comparison

Parent: frozen v82 map, synchronous mode; observation-only component experiment.
One change: a finite recorded-input scheduler compares FIFO, a 50 ms latest-slot
timer derived from pinned PCT-SCAN-ROS2, and a latest-slot consumer derived from
pinned ROG-Map. The mapper, poses, support inputs and thresholds are identical.

Virtual admission time advances by actual measured native service time. The
nominal schedule uses original sensor intervals; the second schedule adds two
explicit 650 ms worker blackouts at scans 60 and 120. These are controlled
overload injections, not a recreation of the historical live scheduler.
Log decisions and per-cloud cost, preserve final full-map digests and categorical
occupancy/inflation differences. Do not interpret fewer fused scans as parity.

A separate transient fixture checks native obstacle evidence when an observation
exists only in a replaced slot. No physics or new navigation candidate is claimed.

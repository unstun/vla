# v151 nested full-curve collision sampling candidate

Stage: experiment + analysis. Native parent v147; Mac host parent v149. v150
reproduces the latest recorded clear-to-blocked pattern with unchanged native
code: changing the remaining interval moves the sample grid into a narrow
support rejection. Holding the earlier body pose still rejects, while checking
the complete interval again passes. It is a discrete sampling miss in that
recorded curve; no full-route recovery fix is yet established.

One behavior change: retain every original full-curve sample and insert four
equally spaced checks between each adjacent pair. Keep original endpoints,
heading, occupancy/support predicates, timestamps and failure handling. The
existing maximum sample budget remains a fail-closed bound. This strengthens
the existing sampled contract; it does not claim continuous collision proof or
eliminate every possible narrow missed interval.

First require a compiled regression showing all original sample coordinates are
still checked, invalid inputs and budget exhaustion fail, and a missed interval
is now found. On the preserved v150 fixture require the previously accepted
curve to reject before motion, while its recorded negative case still rejects.
Keep the unchanged old-library result as a control. Then exercise the actual
planner and full original route. Reject or revise the candidate if it merely
stops earlier without finding usable alternatives or causes unacceptable stalls.

Reuse the owned v149 temporary root and ARM64 image; place candidate native
source/build/install under `recovery_v151`, preserving `recovery_v147`. Rebuild
from the exact parent export with one changed header and record every difference.
Freeze a version before physical trials. Preserve every Mac/Linux failure;
later Linux repeated validation remains required and separate from Mac timing.
No safety relaxation, silent old-outcome replacement or reference promotion.

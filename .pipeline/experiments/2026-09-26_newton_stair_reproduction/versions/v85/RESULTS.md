# v85: separated-lane native prototype, component checks passed

Stage: experiment + analysis. A native three-thread replay separates sensor
veto, every-frame map processing and 30 Hz execution-decision polling. It does
not publish robot commands or replace the existing navigation runtime.

- 188 offered scans, 188 independent sensor checks, 188 native map applications.
- Complete native final-map digest equals the original full-frame baseline.
- 26 contract checks pass, including actual raw PointCloud2 body intrusion,
  mismatched pose timestamp, non-finite points, stale/future source data,
  cancelled-owner latching, new-owner admission, late old-owner rejection and
  pending transient evidence that a newer but incomplete map cannot erase.
- During each deliberately injected 650 ms mapping stall, the sensor lane
  completes six callbacks and the execution lane makes nineteen decisions.
  There are zero allowing decisions in the checked stale-map part of either
  stall. New sensor arrivals do not refresh an old map's timestamp.
- 564 execution decisions; longest observed interval 44.092 ms. The nominal
  30 Hz poll is **not** a verified strict 30 Hz controller or planner result.
- Maximum sensor body-veto processing 13.261 ms in this recording. This is an
  observed component value, not a worst-case deadline.

The guard is veto-only. It requires original map clearance and source age in
addition to fresh sensor data; an observation cannot grant floor support, PVA,
collision clearance or permission to continue on an expired map. A map producer
must supply a truly contiguous applied-observation bound before a previously
unmapped hazard can clear. A later map timestamp alone is insufficient.

## Deliberate boundary before navigation integration

The direct sensor geometry checks the current measured stationary body footprint
using the original double-cylinder spacing and discrete inflation dimensions,
with original selected-ground classification. It is not a full moving-trajectory
collision or braking-distance check. The native map still supplies its original
body/support/freshness verdict. The prototype owner is a numeric epoch surrogate,
not the production full P2B identity/message contract. It does not exercise the
actual stop/hold acknowledgement or PD/RL transitions.

Consequently the prototype establishes concurrency and the specified rejection
contracts only. Integration requires binding the original committed full cubic
trajectory, full owner identity and sole existing stop owner; qualifying the
moving/stair/dynamic-obstacle envelope; then a version-bound physics run. None
of those later gates is claimed here. v48 remains the reference; v82 remains
frozen as failed; no real robot action, training or new navigation acceptance.

Evidence: `analysis/attempt02/verification.json`, actual returned sensor/map/
execution traces, `results/attempt02/lanes_attempt02.log`, and the shared
source/install/input/storage receipts. The interrupted earlier attempt had no
recoverable v85 completion result and is not counted as a passed repetition.

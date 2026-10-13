# v87: Nav2 observation-window scheduling for the native SCAN map

Parent: v86 plugin/native source; map arithmetic parent remains frozen v82.
Dr Sun explicitly requested Nav2-style backlog handling. Scope is observation
admission and independent periodic map updates, preserving 3D mapping/query code.

Reference: Nav2 0.4.7 `ObservationBuffer`, `ObstacleLayer` and `Costmap2DROS` at
commit a947ab5656e46ae3aa1afdf95e1706a16e478974. Observations are buffered in sensor
callbacks and consumed by a periodic update worker. Retention 0 keeps the latest
observation; positive retention keeps the recent source-time window. The most
recent reception time, not a rewritten source stamp, anchors that window.

Expose `grid_map.mapping_admission` (`fifo` or `nav2_observation_window`),
`grid_map.map_update_frequency`, `grid_map.observation_persistence`, and a hard
maximum buffered-cloud count. FIFO remains available for controlled comparison.
The candidate profile uses 5 Hz updates and 0.5 s retention; test the Nav2
zero-retention case too. These are design choices, not performance qualification.

Unlike Nav2's repeated marking of retained observations, SCAN's probabilistic
fusion applies each selected scan once. Retain paired original poses, clocks,
support, map state and publication leases. Count expired/latest/capacity drops.
Metadata overflow or malformed input fails the map rather than growing forever.
Full-map equality is not expected when distinct observations are removed.

Test actual timed buffering, exact pairing, bounded pending work, invalid policy
values, source-age rejection and transient obstacle loss/retention. Compare the
retention selector against real Foxy ObservationBuffer. Run original recorded
input through native mapping if the archived input restores successfully.
Keep failures and changed occupancy counts. A fresh map after a stall does not
erase the stale interval or prove every missed obstacle was retained.

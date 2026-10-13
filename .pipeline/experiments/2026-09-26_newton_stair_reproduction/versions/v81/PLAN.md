# v81 asynchronous versioned mapping

Parent v80. Single writer owns all mutations. Planner adopts immutable completed
snapshots at original fresh-input boundaries. Unchanged support tables are
shared read-only and copied on mutation; old map memory retires on the writer.
Final full-curve validation and Bspline publication hold one short publication
lease, preserving newest completed occupancy through handover. Existing goal,
yaw, PVA, freshness, dynamic and stop gates remain unchanged. No hard deadline.

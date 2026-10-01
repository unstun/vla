# v25: restore the historical complete-floor route profile

Stage: experiment + analysis. Parent: v24. One execution-profile change.
Native scan58, geometry-only sensing, surface data, collision/terrain contracts,
policy, factory startup, speed parameters and PD handoff gates are unchanged.

The short v24 stair route physically arrived, but its mid-flight goal did not
allow the original four-contact/tilt PD handoff dwell. Preserve that incomplete
acceptance result. Do not lower its safety gates or relabel the run as complete.
The user requested the historical stairs/complete-floor result. Test that
original route in its own version, whose original endpoint is on a horizontal
platform rather than inside the short flight.

Use original spawn ground [-5.545314788818359,6.01318883895874,.05804443359375],
yaw -1.3258179441604312, and original goal ground
[1.954685200623011,-2.9868112220934897,4.5330305099487305]. The unchanged native
PCT planner already produced the631-point/73.2373m route in the audited preflight
with automatic layer selection. Set `pct_layer=None` for this explicit profile;
the current fixed layer1 produces the wrong final height for the original goal.

Keep `building_full` as the geometry selector. Add an explicit
`--building-route historical_full` profile, defaulting existing callers to
`short_stair`. Pin the scenario JSON and bind it to the version and run request.
Use a bounded600s physics window and the already-supported1500s goal wall
budget. These budgets do not change sensor freshness, speed or stop criteria.

Validate default/invalid/pinned profile handling without physics, then confirm
the actual requested spawn/goal, backend None layer setting, native PCT route
length and final height. Full acceptance still requires actual native arrival,
continuous physics, measured final PD hold, original gains, no fall, sensor and
source identities, copyback and a directly viewable recorded-state video.
The platform sampling audit establishes horizontal support only; no route or
four-foot stability success is inferred from it in advance.

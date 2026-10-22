# Verified source findings

Parent native inventory binds 329 files; A-star implementation is byte-identical to v240 and its header to v196. v284 owns the tracker, FSM, source field and environmental cost wiring.

- Non-exact A-star converts endpoints using their chord yaw, retreats along its normalized 3D vector without a bounded local adjustment, and uses the endpoint sloped plane for planar neighbors. A synthetic supported stair hill reproduces search failure; a right-angle stair corridor reproduces pool exhaustion in both directions on the frozen parent. The same probes execute the actual native AStar and GridMap. Fixture construction errors (missing synthetic physical-floor binding and recomputed floating-point boundary expectations) are preserved separately from production failures.
- Tracker phase previously advances by full dt after v284 removed translation scaling. Native ROS-clock contrast shows four rotated large-heading travel cases retaining nonzero translation but full-speed phase; candidate scales both and remains positive.
- Reference-mode FSM uses predicted position until expiry/repeated failure, without the requested displacement/occupancy fallback. The candidate uses the curve tangent for that occupancy query and existing measured initialization.
- Removing added repulsion preserves exact hard field implementation, source collision checks, ENV225 and scan scheduling. Timing and L-BFGS effects remain empirical questions.

The v284 raw-log baseline uses identical per-line counters: 90 pool, 90 endpoint adjustment, 44 A-star optimization failure, 331 inside-obstacle, 664 -1008 and 54 no-executable mentions. Repeated log mentions are not distinct failures; v284 has seven terminal failed routes.

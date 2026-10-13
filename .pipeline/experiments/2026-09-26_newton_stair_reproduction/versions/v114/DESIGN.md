# v114 controller validation

The Nav2 SCAN controller checks its exact executing spline before computing a
command. It uses the native full remaining-curve checker from the tracker phase,
with an immutable native map revision and the original controller pose and clock.
The map view owns its query caches; native diagnostic static state is not shared.
A publication lease pins the checked revision without adopting it into the planner.
Negative native safety messages, emergency splines, cancellation, ownership and
measured-stop contracts remain in effect. Positive native timer proofs cannot
replace the controller proof. Original 100 ms body/proof and 250 ms observation
limits are unchanged. Publication rechecks the original body source time.

Verified components: 34 colcon test entries (31 GTest cases); 27 paired native
occupancy queries; immutable map hashes; separate controller clock; future/stale
body, wrong frame, bad quaternion, stale observation and out-of-map spline rejection;
writer failure propagation, publication pinning and subsequent actual writer progress;
actual native publication proof and original emergency/wait/stale state checks.
Full navigation acceptance requires the original physical run and measured stop.

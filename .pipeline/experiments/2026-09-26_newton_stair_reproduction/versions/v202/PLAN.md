# v202 — LocalMotion owns SCAN and Tracker

Parent: frozen v201. SCAN source comes from its verified composed workspace;
the controller/tracker source is frozen v200, unchanged by v201.

Replace the internal route, spline and execution-freeze topic round trips with
one LocalMotion interface. Nav2 supplies a route, requests a command and cancels
execution. LocalMotion owns the native worker, tracker and their exchange state.
The Nav2 adapter retains terminal completion and the sole server velocity outlet.

- Route and control feedback enter bounded immutable snapshots, consumed on
  SCAN's serialized worker. Tracker state is written only on the control thread.
- SCAN delivers completed spline snapshots through a direct callback, including
  emergency stop. Route generation invalidates late outputs after cancellation,
  a new goal or a changed route. A repeated identical route keeps its generation.
- Feedback includes trajectory identity so freezing one curve cannot freeze its
  replacement. No worker callback directly edits Nav2 or Tracker state.
- `/pct_path`, `/quad_0/planning/bspline` and execution-freeze topics remain
  observation outputs. LocalMotion subscribes to none of them. Standalone SCAN
  retains its existing ROS interface when no direct interface is supplied.
- External localization, sensor/map inputs, physical execution feedback and
  clock subscriptions remain ROS inputs. Mapping cadence, immutable map leases,
  collision/support logic, optimizer and tracking formulas are unchanged.

Required checks: build the changed native library and dependent controller;
existing tracking parity, terminal/stop and SCAN component tests; direct route /
output / freeze exchange, stale generation rejection, cancellation, ROS injection
isolation and repeated worker lifecycle. Only component fixtures; zero new full
route experiments or physics steps. Update the HTML and source/version records.

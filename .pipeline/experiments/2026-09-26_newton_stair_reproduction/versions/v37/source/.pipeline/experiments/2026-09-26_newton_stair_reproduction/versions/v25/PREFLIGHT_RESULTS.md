# v25 route-profile preflight

Five host profile tests pass: unchanged default short route, exact historical
spawn/goal/budget, corrupt-file rejection, scene/profile compatibility and
unknown-profile rejection. Changed Python sources parse successfully.

The actual native PCT run reads the new pinned profile file and uses existing
automatic layer selection. It returns631 points,73.237319626m XY length, final
body reference[1.954685232,-2.986811204,4.831252664]. Relative to the original
goal ground plus.30m, final height error is.001777846m. The entire returned
route result is exactly equal to the earlier native_auto preflight. The run
receipt is audits/2026-09-27_full_route_preflight/attempt03_profile_v25.

No physical route or final PD acceptance is inferred from these checks. The
actual episode must confirm the configured layer mode and executed goal again.

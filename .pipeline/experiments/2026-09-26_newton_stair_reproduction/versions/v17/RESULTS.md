# v17 results

Native compilation passed (39.56 s), with all frozen source identities unchanged.
The original 66-scan and expired-curve 67-scan continuations still pass PVA and
full-curve checks without invoking recovery. The v5 positive still requires
three-axis optimization; fixed-height alone still fails that old case.

The 189-scan physical-ground diagnostic passes complete native continuation twice
through the bounded recovery. Complete-manager tests also check restored height
mode, one failure count per completed failed call, and no failed trajectory
publication. The original selected-ground input remains blocked. See
`runs/v17_native_regression01/review.json`; the diagnostic ground is not adopted.

The production-input physical trial `v17_building_route01` is unsuccessful:
35.252 s simulated time, 1.841 m net forward travel, 0.210 m rise, final XYZ
(-5.396678, 4.268281, 0.608526). The terminal reason is `odom_stale`; the observed
maximum body-callback gap was 0.262 s against the unchanged 0.25 s watchdog.
The stop flow completed with controller hold and measured stillness, and Linux
applied-state copyback verified. This is progress beyond v15's 1.058 m, not
stair-route or full-building acceptance. Architectural contact safety is not
claimed. The configured cruise requirement remains 0.6 m/s with existing
boundary acceleration/braking exceptions; measured minimum cruise is unproven.

# v129: allow measured stop to complete before recovery times out

Native/host parent: frozen v128; unchanged control native v114. This is a
separate recovery-protocol fix, with no MPPI adaptations. Original captured
v128_candidate_attempt04 needs5.273s to complete the original1s stop window;
the installed gateway wait loop fails at4s and real BT service client at5s.
Both premature timeouts were reproduced with the original installed code.

Change only the recovery wait budget to10s (matching the existing Nav2 progress
allowance) and the outer BT response budget to11s. Do not change body/scan/proof
ages, applied command limits, speed/yaw stillness,1s dwell, collision checks,
owner binding, two retries or global mission budget. Timeout never releases
ownership. A closing mission still fails the wait immediately.

Owned behavior paths: gateway.py wait_stopped and bind_route.cpp WaitForScanStop.
Test the real installed wait/release methods with original recorded applied
snapshots; verify successful proof after5.27s, absent proof stays failed/owned,
and closing stops waiting. Test the actual C++ BT plugin with a5.3s service
reply. Full physics and remaining route-admission failures are separate gates.

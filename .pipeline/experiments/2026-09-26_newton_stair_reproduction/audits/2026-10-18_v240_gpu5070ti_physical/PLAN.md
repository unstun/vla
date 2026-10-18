# One full original-route physics test of frozen v240, execution v241

Authorized by Dr Sun on2026-10-18 after the v238–v240 commits. One attempt
only, no automatic retry. Preserve RL, original endpoints, ENV225,0.35m hard
collision/support,0.1s captures and v237's scanner deadline fix. Native runtime
is v240, graph/driver remain frozen v232, physics/scanner/locomotion remain
v237/v216. Bulk stays on gpu5070ti; local returns are compact evidence/videos.

Report original route/arrival/measured PD, sensor deadline, actual emergencies,
20ms measured >=0.5s/legacy>=1s and cumulative split low-speed intervals in
45–55s and109–115s. Also report route-relative approach to avoid mistaking a
shifted earlier terminal hold for an approach hesitation. Keep raw fixed-window
counts. Compare actual body-yaw edge margin under the same frozen ENV225.

Reuse the causal v220 renderer through the v237 audit adapter, binding only
the new execution identity/source. Produce full v241 video and two-column
v237/v241 common-physics-time comparisons, including stairs and terminal clips.
Keep every pause; no state interpolation, no future trajectory and black panels
after a recording ends. Verify all frame mappings, source hashes and full decode.
No baseline adoption or repeated-reliability/30Hz claim from one run.

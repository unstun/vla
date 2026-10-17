# v203 — one static terrain package, minimal Nav2 map shell

Parent: frozen v202. Implement step 4 only; keep the 1 Hz global planning policy
for step 5. No physics or whole-route execution.

One offline terrain package binds native PCT input, selected navigation support,
surface evidence, physical-floor presence and the negative-only support-gap mask.
One runtime publisher loads the three typed cloud payloads once and publishes them
on their existing separate latched topics. Preserve exact XYZ/cost bytes, origin,
resolution, source identities, source-clock gating and reset behavior. A shared
manifest supplies the native PCT file and SCAN static configuration.

Remove LocalMotion's 2D terrain projection publisher/timer. Default local/global
Nav2 costmaps have no active layers or inflation; retain small TF/lifecycle shells with
a nonzero update rate because Foxy activation waits for its first update.
Remove the unused Wait recovery server from the no-retry tree's launch.
Do not change native SCAN map, geometry, collision, support or optimizer code.

Validate byte-exact old/new static payloads, clock and malformed bundle handling,
real ROS publication with late subscribers, generated launch/profile contents,
real empty-costmap lifecycle and actual native support decoding. Build the
composed packages and run affected LocalMotion/terminal/tracking regressions.
Preserve old versions; update the source/version records and architecture HTML.

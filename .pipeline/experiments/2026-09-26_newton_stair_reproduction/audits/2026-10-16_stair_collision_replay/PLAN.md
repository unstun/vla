# Identical-input stair collision audit and explanatory video

User-authorized scope: diagnose the archived stair failure using identical cloud,
body pose and reference data; render on gpu5070ti. Do not change navigation code.

The diagnostic source of truth is this local audit folder. Production sources,
frozen versions, parameters and current/adopted pointers remain unchanged.
Standalone input extraction, read-only native probes and rendering scripts are
the only new code. Native probes call the installed frozen map implementation;
upstream comparisons use the pinned author rule and verified ROS 2 reference.

Selected recording: v217_linux_full_attempt01, which stopped upright at the
stair and exhausted navigation retries. Reconstruct its published sensor prefix
and evaluate identical query states. Preserve original sensor/body timestamps,
quaternion conventions and route changes. Ordered map reconstruction is not a
claim to restore the exact asynchronous worker scheduling of the original run.

Compare separately:
1. Author occupancy rule and supplied footprint on the recorded cloud prefix.
2. Author rule with current footprint, to isolate geometry from semantic gates.
3. Current native decision, decomposed into map bounds, support-gap veto,
   occupancy/terrain classification, unknown evidence, body-height/layer and
   footprint support, freshness, and known-footprint handling.

First match relevant recorded rejection locations, then test routes and a local
height-associated grid. Use original Building collision geometry and recorded
contact/support evidence as an independent diagnostic. Geometric clearance does
not certify a new locomotion trajectory. Do not run new policy/physics episodes.

Rendering: synchronized views, stable colors and camera, original recorded robot
states, native PCT traversability, spatial local feasibility, route/candidate
queries and first rejecting condition. Introduce layers sequentially and slow
the decisive moment; retain a visible source clock and replay-speed label.
No fabricated smoother trajectory, hidden failed interval or future data.

Remote output root: /data/sun/vla_mppi_20261009/stair_collision_replay_20261016.
Sync only this audit folder and explicitly required pinned reference files;
verify hashes before execution. Reference captures/builds are read-only inputs.
Full point clouds, reconstructed maps and rendering/build scratch remain remote.
Return allowlist: final MP4 (target under 80 MB), three PNG previews, compact
results and provenance (target under 5 MB excluding video). Preserve failures.

Acceptance: native replay completed; first rejecting predicates and limitations
documented; maps/queries refer to identical inputs; video fully decodes, has
verified frame/source indices, and visibly explains the decisive difference.
No claim of repaired navigation or general physical traversability follows.

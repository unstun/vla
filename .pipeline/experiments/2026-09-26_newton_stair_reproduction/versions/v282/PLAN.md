# v282 Conditional physical execution under frozen v280

Preparation only. Require the unchanged v281 fixed50+3 full-chain gate, ten
selected distinct routes, per-case zero-step native/profile/scanner checks and
one common execution freeze. Execute each selected route once; no formal retries.
Preserve RL, exact requested positions/headings, 0.35 m support/collision, 0.1 s
sampling and v237 deadline handling. Reuse v241 Warp CPU physics/recorder,
v248 bridge and explicit-heading v257 driver. Keep existing IsaacLab jobs intact.

The new physical fixtures retain all frozen v280 bytes and old voxel metadata.
New source_surface282.json explicitly binds the separate SURFACE271B descriptor
and both geometry dependencies. Both PCT and SCAN load that same descriptor.
Terrain/environment publisher metadata is refreshed without modifying geometry
or ENV225 scores. Verify the frozen execution source manifest on every formal run.

The inherited v196 resource gate is still active (20 GiB available RAM, GPU
compute list empty, 10 GiB free disk). The disk check follows the actual output filesystem.
New captures use `/home/sun/vla_exec/physical_runs_v282/` on the same host
(62 GiB observed free); existing data is not moved or removed. Recheck GPU and
RAM after the independent audits release their resources. All three inherited
thresholds remain unchanged. Offline and resource admission are separate.

Deliver complete attempt videos (including failures) to the local audit's
delivered/ directory, along with per-route global/local success, pauses >=0.5 s
and >=1 s, cross-layer metrics, minimum margins, arrival and terminal PD closure.
No claim of reliability from one attempt per route. No current physics/video.

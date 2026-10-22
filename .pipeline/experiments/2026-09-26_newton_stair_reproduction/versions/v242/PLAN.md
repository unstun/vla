# Building endpoint evaluation adapter

Parent: frozen v240 installed native navigation; v241 historical control reused.
Approved task: 10-18-v242-building-generalization, 2026-10-18.

The behavior gap is evaluation coverage: old probes force yaw zero and reuse a
historical sensor prefix, and the launcher only binds historical profiles.
v242 owns case discovery/freeze, original-ray case fixtures, installed-native
global/local adapters and compact batch results. v243 will own case-specific
physical launch and verification over v241. No native implementation changes.

Map candidates and every discovery query are preserved before a frozen 12-case
manifest and 60 scored fresh-process calls. Static support, static raw-cloud
oracle and case-observed LiDAR remain separate. ROS time is held at the actual
case capture epoch for the geometric component batch; wall timing is measured.
This does not test live scheduling continuity, which belongs to physical runs.

Remote raw/build root: /data/sun/vla_mppi_20261009/generalization_v242.
Physical captures: separate v243 per-case private trial roots. Return only
source/config, compact CSV/JSON/log receipts, plots and each complete MP4 to a
dated local audit's delivered/ directory; expected local return below 150 MiB.
Bulk scans, maps, archives and compilation products stay on gpu5070ti.

Preserve RL, ENV225, 0.35 m hard geometry, 0.1 s scan period, v237 absolute
deadline, original freshness/dynamics/epoch/PD/stop rules and all failures.
Do not repeat historical_full, repair native algorithms, replace failed cases,
or promote the selected v232/v233 baseline. Main session implements/checks inline.

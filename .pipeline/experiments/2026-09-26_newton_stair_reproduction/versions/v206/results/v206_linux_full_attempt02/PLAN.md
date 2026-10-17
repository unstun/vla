# v206 Linux recording — one physical attempt

User requested the actual v206 video. Execute one original historical_full
Building episode on gpu5070ti using the frozen v206 Linux build; unchanged v196
scenario/start/goal, v40 physics, V12 model, factory/PD startup and v198 telemetry.
600 simulation seconds maximum; 900-second wall supervisor. No tuning or retries.
A failure is retained and rendered as the actual failed attempt, not hidden.

Local source: this trial-only adapter and frozen v206. Remote execution copy:
/data/sun/vla_mppi_20261009/repo. Build:
/data/sun/vla_mppi_20261009/command_continuity_v206_20261015.
Raw run: /data/sun/vla_mppi_20261009/trials/v206_linux_full_attempt01.
Verify runtime/source/install hashes and loaded native graph before physics.
The adapter changes host paths, image/platform, Linux RSS units and version
binding only. No frozen navigation or physical behavior source is edited.

Keep raw/NPZ/logs on gpu5070ti. Return compact result/provenance/verification and
one finished regular MP4 (expected 15-100 MB; maximum return budget 150 MB).
Video contains the actual startup, navigation/pauses and terminal result at
causal original timing. Original full-route gates determine success separately.
Do not compare Linux wall performance directly against the Mac v204 run.

Attempt01 stopped before the first integration (initial-state witness at 0 s; no completed video-state sequence).
Its Linux launch shims inherited non-executable Mac file modes; the graph probe
also left ROS launch descendants in the same container. Preserve attempt01.
Attempt02 executes byte-identical shim copies from this owned bin directory and
recreates the probe container before physics. Navigation/physics code and
parameters remain frozen and unchanged.

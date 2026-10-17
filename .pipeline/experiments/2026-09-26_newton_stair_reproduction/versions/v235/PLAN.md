# v235: one gpu40901 original-route physical trial

Parent runtime: v234; navigation: frozen v232; execution/physics reference: v233.
Dr Sun authorized on 2026-10-17: prepare the complete host entry, pass preflight,
then execute exactly one full-route closed-loop trial and deliver comparison video.

The gap is the offline-only v234 entry. Reuse v233 launch/recorder/gates with
40901 paths, v234 native install/image/factory adapter, and isolated resources.
Own launch.py, native_graph.py, newton_episode.py, resource_gate.py, source/input
manifests and analysis/display adapters here. No navigation, policy, endpoints,
physics solver, control tolerance or 0.35 m hard guard changes. v234 evidence
and all frozen parents remain intact. A single trial cannot establish reliability.

Native: four CPUs / 6 GiB / cpu shares 128; host physics: two CPUs, nice 19,
CPU-only Newton and ONNX. No peer signals, configuration changes or GPU reservation.
Record peers before/after. Offline graph probe is separate from physical attempt.

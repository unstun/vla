---
origin: pinned_source+official_documentation+local_evidence+remote_checks
reviewed: false
date: 2026-09-09
status: surveyed_with_static_renderer_probe
---

# LightNav-0 visual reproduction continuation

Canonical source: https://github.com/lightorigins/LightNav-0 at
`d83fbfb9748ca6b497a2f2a7f4a3e95e2110e40c` (also the current head at the recorded
API check). Model revision `826dc5fbfa37afa8293d2e336d329b6ffc0bfb64`, original
BF16; both source/model Apache-2.0. Bundled scene provenance remains CC BY 4.0.

The investigated continuation preserves the official vLLM/MuJoCo case. Its main
requirements follow four source-backed findings: old recorder names overwrite
frames, HTTP image polling lacks exact capture metadata, the official overlay
has display-only trajectory/speed conventions, and its `realtime` export clamps
long intervals. Frame-bound state capture and offline visualization are selected
to avoid adding high-resolution rendering to the live control loop.

A real MuJoCo 3.11.0 static probe tested state save/restore and a world-fixed
orthographic view with only named ceilings hidden in a visualization instance.
The first camera-field-only attempt remained perspective; the corrected global
projection flag was verified in the renderer. No simulator step or VLA inference
was executed during this preparation.

Detailed evidence, source map, live-host snapshot and uncertainty:
[investigation](../experiments/2026-09-09_lightnav0_official_demo_rented4090/continuation_v3/RESEARCH.md).
The [manual Opus package](../experiments/2026-09-09_lightnav0_official_demo_rented4090/continuation_v3/EXECUTION_PACKAGE.md)
and [visual specification](../experiments/2026-09-09_lightnav0_official_demo_rented4090/continuation_v3/VISUAL_SPEC.md)
are prepared, not dispatched. The new recorder, moving-state replay, fixed runs
and navigation outcome remain executor work and require evidence-based review.

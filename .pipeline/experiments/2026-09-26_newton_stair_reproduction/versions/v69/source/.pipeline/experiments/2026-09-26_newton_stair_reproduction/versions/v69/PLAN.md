# Mac recorded-state review

Stage: experiment + analysis. Dr Sun requested a video of the latest Mac trial.
v69 is one display-only host adaptation, parent v68; the physical source is
v68_mac_trial01_attempt02 with frozen v63 native planning and v59 physics.

Reuse the frozen v51 renderer, streaming encoder, causal 30 FPS wall timeline
and original robot/Building materials. Reuse v61's close heading camera. Select
the already recorded external Mac run without copying or modifying it. Read
the verified Mac analysis for the overlay, preserving cross-OS clock mapping.
Use the Mac Cocoa OpenGL context with a hidden viewport instead of Linux EGL.
No physics, sensing, control, planning, safety or stopping changes are made.

Run through the original managed retention and bounded supervisor, with output
and caches at a unique /private/tmp/vla_newton_v69_* root. Before execution,
freeze owned source and pin renderer/physical manifests plus source-state,
geometry and analysis hashes. Inspect three sample frames; decode the complete
MP4 and verify causal source indices, final stop and unchanged source bytes.
Return only the requested review MP4 (under 128 MiB), three samples and compact
receipts. Keep all original raw captures outside the repository. Preserve failed
render attempts separately. Display FPS is not a planner-frequency claim.

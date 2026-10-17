# v197 display review of v196 Mac attempt 01

Stage: experiment + analysis. Parent v196; display parent v195; native implementation v196; physical source v196_mac_full_attempt01. The physical run must pass the unchanged full-route gate and be remotely archived before rendering.

Replay the complete recorded episode, including actual zero-step frame, factory startup, pauses, recovery and final PD hold. Startup follows original simulation time; navigation follows original wall time at 1:1. Preserve causal state selection, curve freshness and the original close following camera. Execute zero physics steps.

Source changes relative to v195 are run/version paths, a freeze_host entry point, and replacing prior-trial literals with measurements of this capture. Overlay and timeline behavior and their 14 unit tests remain unchanged. Frozen v196 and all earlier sources remain unchanged.

Execution: use the existing Mac runtime Python with PYTHONDONTWRITEBYTECODE=1. Run test_overlay.py, test_timeline.py and run_mac.py. The temporary render root is /private/tmp/vla_stop_audit_20261012/video_v197. Verify every causal frame, full MP4 decode, 1280x720 at 30 FPS, source hashes and final recorded PD hold. Inspect decoded startup, navigation and final frames; retain a contact sheet and visual QA notes.

Deliver the regular file delivered/v196_mac_full_attempt01.mp4. Archive the MP4 and compact display source/provenance to gpu5070ti:/data/sun/vla_mppi_20261009/mac_archive_v196_20261014/. Freeze only after successful display and archive verification. This creates no additional physical trial or reliability claim.

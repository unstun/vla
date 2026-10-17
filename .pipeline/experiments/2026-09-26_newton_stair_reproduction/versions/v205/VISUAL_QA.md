# v205 display QA of v204_mac_full_attempt01

Passed: complete 4,998-frame MP4, 1280x720, 30 FPS, 166.6 seconds. All causal
source-state indices and overlay timestamps passed. Full MP4 decoding passed.
There are 332 startup frames using original simulation time and 4,666 navigation
frames using original wall time at 1:1. No interpolation, pause removal, speedup
or extra physical step. First physical time 0.0 s; last 143.590896606 s.

Nine decoded samples covering startup, stairs, turns and final PD hold were
visually reviewed in returned/visual_qa/contact_sheet.jpg. The final sample was
also reviewed at full resolution: robot upright, Navigation: arrived
(nav2_arrived), no active cyan curve. Original global route remains orange.
The close camera, original robot/scene appearance and readable captions are
retained. No blank/corrupted frame or clipped caption was seen in those samples.

The ten unchanged overlay tests and four timeline tests passed. The first
preflight failed before rendering because the old manifest used repository-relative
reference paths. The display-only verifier now distinguishes old snapshot manifests
from version-relative component manifests; failure logs are retained. Navigation
and physical sources were not modified.

Delivered regular file: delivered/v204_mac_full_attempt01.mp4, 14,786,135 bytes.
SHA-256: 4adc8578d0cab2bfbb623c2c9c8c1636f729297d7514023c8f24ca1efaffa225.
The copy on gpu5070ti has matching size/hash. This is the display of the one
passed v204 capture; it adds zero physical experiments.

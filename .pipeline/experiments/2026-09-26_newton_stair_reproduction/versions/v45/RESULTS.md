# v45: physical navigation recording; timing and route gates not met

The frozen v45 execution ran the complete original Building and historical route from factory initialization with the original CPU solver graph, original PD/RL, geometric LiDAR, PCT and SCAN. Actual physics: 64880 steps, 64.8559875 native seconds. The delivered navigation view starts after initialization; startup evidence remains in the original run. No physics step was dropped.

Actual navigation RTF: 0.9400067. Local planning: 16.8619245 Hz (target 30), median nominal solve 42.2256 ms, 625 nominal budget overruns, 684 skipped slots. Raw controller: 29.9647549 Hz. Actual PCT global refresh: 0.9999814 Hz, 52 unique observed computations. Gated Twist counts include extra stop publications and are not controller timer frequency.

The run terminated on global_refresh_failed:pct_no_route before the 90-second observation bound. The original stop flow completed and Linux tmpfs copyback verified. Navigation was not accepted, local 30 Hz was not met, and simulation/native 1:1 was not met. Process exit 0 means the bounded recording supervisor completed, not navigation success. All 661 original returned files were SHA-verified locally.

Display-only v46 uses original wall timestamps at 30 FPS: one recorded wall second is one video second, preserving the actual lag and pauses. It does not convert playback FPS into runtime evidence. See runs/v45_realtime_preview01/recording_measurements.json and versions/v46/timeline_check.json.

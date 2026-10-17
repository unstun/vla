---
origin: ai+web
reviewed: false
date: 2026-09-21
status: surveyed
pin: isaac-sim/IsaacLab tag v2.3.2 (same Lab line as prior Building pin 37ddf626)
license: BSD-3-Clause (SPDX on the fetched file)
claim_boundary: "Read patterns_cfg.py from the v2.3.2 tag. Not cloned, not executed."
---

# Isaac Lab v2.3.2 ray patterns

Fetched:
https://raw.githubusercontent.com/isaac-sim/IsaacLab/v2.3.2/source/isaaclab/isaaclab/sensors/ray_caster/patterns/patterns_cfg.py

SPDX-License-Identifier: BSD-3-Clause.

## Public hook for a vendor table

`PatternBaseCfg.func(cfg, device) -> (ray_starts, ray_directions)`.
Isaac Lab has **no** Livox / MID-360 class. Stock patterns:

| Class | Role |
|---|---|
| `LidarPatternCfg` | Uniform spinning lidar: `channels`, `vertical_fov_range`, `horizontal_fov_range`, `horizontal_res` |
| `BpearlPatternCfg` | Vendor-specific **non-uniform** elevations (32 hardcoded RS-Bpearl angles) |
| `GridPatternCfg` / `PinholeCameraPatternCfg` | Height map / depth, not a spinning lidar |

The Building stand_probe that counted the unmapped box used
`LidarPatternCfg` (16 channels, 2° azimuth, VFOV −7°…+52°, 12 m). That is
Isaac’s generic lidar, not Livox.

The already-written Lite3 adapter maps Livox CSV windows onto this hook:

- `_mid360_pattern_cfg` returns `PatternBaseCfg(func=initial_pattern)`
  with `scan_window(0)` only as the **initial** buffer
  (`run_isaac_v12_fallback.py`).
- Each publish step, `_set_mid360_scan_window` copies
  `pattern_table.scan_window(scan_index)` into `lidar.ray_directions`,
  then `reset()` + `update(dt=0.0, force_recompute=True)`.

That is the surveyed Isaac Lab way to feed a non-stock pattern. It is
not an RTX LiDAR.

Docs (lead only):
https://isaac-sim.github.io/IsaacLab/v2.3.2/source/api/lab/isaaclab.sensors.patterns.html
https://isaac-sim.github.io/IsaacLab/main/source/overview/core-concepts/sensors/ray_caster.html
(example `LidarPatternCfg(channels=100, …)`).
---

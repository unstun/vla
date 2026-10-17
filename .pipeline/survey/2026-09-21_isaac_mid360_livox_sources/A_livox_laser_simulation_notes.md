---
origin: ai+web
reviewed: false
date: 2026-09-21
status: surveyed
pin: Livox-SDK/livox_laser_simulation commit 1cce1073633a062b92e30243a4c2920e45551bb5
license: MIT
claim_boundary: "GitHub API + raw LICENSE/xacro at the pin. mid360.csv was not downloaded; SHA-256 not rehashed this turn."
---

# Livox-SDK/livox_laser_simulation

Canonical URL: https://github.com/Livox-SDK/livox_laser_simulation  
Default branch: `main` (last push 2023-11-20 in the listing inspected).  
Pin re-checked: commit `1cce1073633a062b92e30243a4c2920e45551bb5`
(2023-03-29, message "Update README.md"; parent `e20c56f9`).
LICENSE at that commit: MIT, Copyright (c) 2021 livox.

## What it is

Gazebo 9 / ROS Melodic plugin. Original command from README:

```
roslaunch livox_laser_simulation livox_simulation.launch
```

Scan models are CSV files under `scan_mode/` (`mid360.csv`, `avia.csv`, …).
This is the table the local adapter already names as
`upstream_repository` in `mid360_pattern.py`.

## MID-360 files at the pin

`scan_mode/mid360.csv` exists at the pin (GitHub Contents API):

- path `scan_mode/mid360.csv`
- git blob SHA `536686c17fc58d2900a585fefbb6bf21cd5acdee`
- size **16 809 997** bytes
- raw URL:
  https://raw.githubusercontent.com/Livox-SDK/livox_laser_simulation/1cce1073633a062b92e30243a4c2920e45551bb5/scan_mode/mid360.csv

Local `mid360_pattern.py` expects SHA-256
`aa1fc08b6a4400608dbd6ee832b7ea3a9c3c37197e734f60f58fe5abf762269a`
and **800 000** rows. That digest was **not** rehashed here (file not
fetched). The CSV is **not** stored in this VLA tree.

`urdf/livox_mid360.xacro` at the pin:

- `csv_file_name` = `package://livox_laser_simulation/scan_mode/mid360.csv`
- vertical ray limits in the Gazebo ray block:
  `-7.22°` to `+55.22°`
- 360 horizontal samples in that ray block (plugin still drives rays from CSV)
- optional **gaussian** `noise_mean` / `noise_stddev`
- `laser_min_range` / `laser_max_range` are xacro args (README display
  example for Avia uses 0.1 / 200 m, not MID-360 datasheet 40 m)

## Do not reuse

- Gazebo plugin C++ as the Isaac runner.
- Treating the xacro 360×360 *ray* block as the Livox pattern (the CSV is).
- Claiming this plugin equals a physical MID-360 (no intensity/weather;
  gaussian range noise is optional and Gazebo-specific).
---

# ETH StepFilter source reference (2026-09-23)

Source: `https://github.com/leggedrobotics/traversability_estimation`

Pinned clean Git `HEAD` observed with `git ls-remote`:
`14d24c059e1c43466aadf328280adf6394d78039`.

Files copied byte for byte from `raw.githubusercontent.com` at that commit:

| Local file | Repository path | SHA-256 |
| --- | --- | --- |
| `StepFilter.cpp` | `traversability_estimation_filters/src/StepFilter.cpp` | `cdcf18ef0b6396770ea779fd03683b757ddd78640bc4817205377713186920f2` |
| `StepFilter.hpp` | `traversability_estimation_filters/include/filters/StepFilter.hpp` | `b9d787afad334d1e595c11d014fdaf66487d5bb143db0244110bebe3e48ddcfa` |
| `robot_filter_parameter.yaml` | `traversability_estimation/config/robot_filter_parameter.yaml` | `9e0fa7b5e274b9c784b57202746daa6790cf415fd797ae8e275d1e85ca3256bc` |
| `LICENSE` | root `LICENSE` | `c35a214548e537ac722906b28f3b9086d8edd75f2b0a192ce4f70b2ccccbc534` |

The license is the upstream BSD-style three-clause notice. This is a source
reference for a SCAN adaptation, not an import of the ROS node, a reproduction
of upstream behavior, or evidence of a working stair planner. Upstream runs
under ROS Noetic with Grid Map and an elevation input; this project uses a
separate ROS Foxy SCAN path. Any adapted source must preserve attribution and
record its local changes and tests.

The pinned example robot filter YAML sets step `critical_value: 0.12`, both
window radii to `0.04`, and `critical_cell_number: 4`. These are upstream
example parameters, not Lite3 capability measurements. The C++ constructor
defaults differ and `configure()` reads the YAML parameters.

# CMU terrain analysis source review

Repository: https://github.com/jizhang-cmu/ground_based_autonomy_basic
Commit: `7ae94b72206430a399ae012f49715cf51fadb0e0` (noetic).
Status: surveyed only; no build, execution, copied implementation or dependency.
The terrain-analysis package has no license file in this pinned tree. The only
license found is for the separate velodyne_simulator package and does not license
this terrain source. Do not treat this reference snapshot as a licensed code import.

Original launch: `roslaunch vehicle_simulator system_simulator.launch`; dependencies
and launch options are retained in the original README and package launch file.
This task inspected signed ground-relative height and unknown-space handling.
The v15 implementation reuses the existing licensed ETH helper and keeps the
local map, layer, step-height and obstacle-history contracts. It does not copy CMU
code or claim equivalence to CMU terrain analysis. SHA-256 and URLs are recorded
in provenance.json.

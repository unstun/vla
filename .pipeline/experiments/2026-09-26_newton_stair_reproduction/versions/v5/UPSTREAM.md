# Height optimization provenance

- SCAN-Planner `348e8a590a50a5a6bbab8d8c6dcfd171f009be26`, Apache-2.0:
  [native optimizer](https://github.com/wuyi2121/SCAN-Planner/blob/348e8a590a50a5a6bbab8d8c6dcfd171f009be26/src/planner/bspline_opt/src/bspline_optimizer.cpp).
  Existing executable implementation; both cost functions compute XYZ gradients
  and then explicitly zero Z. v5 only makes that final masking conditional.
- EGO-Planner `bfda51284c8c1b476043255a8145ef925a3778a5`, GPL-3.0:
  [three-axis gradient reference](https://github.com/ZJU-FAST-Lab/ego-planner/blob/bfda51284c8c1b476043255a8145ef925a3778a5/src/planner/bspline_opt/src/bspline_optimizer.cpp#L960).
  Surveyed online: rebound/refinement pass the already-computed XYZ gradient to
  L-BFGS. Its license is retained under the prior trajectory-diagnosis reference
  snapshot. No EGO source file, package, dependency or runtime is imported here.
- Prior local `scan42_geometry_v5` has optimizer SHA-256
  `6b7d4ae630a3f9c1c06b07773059278e7f89a2a840f41c76a58a224e260cc521`.
  Its height gradient was not masked. The later internal `scan42_geometry_v6`
  replaced only `bspline_optimizer.cpp` with the prior ROS port of original SCAN
  (`9744424bd58841213230e95b252706360b1d4db10eaf30e7f6bf34a857a87568`).
  These internal candidate suffixes are distinct from the user's integration
  versions v3/v4/v5.

Retain the current SCAN native objectives and local hard-PVA initialization.
Use the existing pinned ROS Humble build image and bounded build instructions
in `setup/build_scan_local.py`. Height optimization is explicitly enabled only
in `building_planner.yaml`; original geometry/dynamics/height limits remain.

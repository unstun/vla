# Exact-endpoint seed candidate: local verification

Stage: experiment and analysis. Local VLA remains the source of truth.

The native scan_24 search can return a collision-free lattice path which the
manager subsequently invalidates by replacing its final point with the exact
goal. The replacement changes the final segment's heading and therefore its
two-cylinder footprint. The controlled `changed_heading` fixture reproduces
an originally clear final edge becoming blocked at sample 0 after replacement.
This is a demonstrated code-level failure mechanism. The recorded Building
replay reports edge 74/sample 0 but lacks its original endpoints and path size;
the exact cause of that recorded rejection remains unconfirmed.

## Diagnostic package

`materialize_endpoint_trace.py` creates `builds/scan24_endpoint_trace` from the
hash-verified, successfully built scan_24. Only `planner_manager.cpp` changes.
After the first existing seed-edge rejection, it logs path size, edge index,
old/new endpoints and headings. It rechecks the original edge and reports the
rejected footprint. All extra queries occur after rejection, followed by the
original failure return. Invalid-input failures do not cause diagnostic float
to integer conversion. Acceptance rules and thresholds are unchanged. Extra
query/logging overhead makes this a diagnostic, not a timing control.

## Candidate

`reactive_stair/materialize_scan_25.py` creates a separate candidate directly
from scan_24. Only the AStar header, AStar implementation and planner manager
change; the diagnostic is not included.

- Manager seed search explicitly requests exact endpoints. It does not use
  the legacy start/end movement or post-search endpoint replacement.
- Each popped lattice node within two search steps of the requested goal,
  measured in 3D Euclidean distance, may try a complete terminal segment.
  The existing shared half-voxel predicate checks its direction and both
  endpoints. Unknown remains blocking.
- A rejected connection continues search, even at the snapped goal index.
  Success returns the actual requested goal as part of the checked path.
- Every search clears result state before validation. The default optimizer
  mode retains its adjusted-endpoint behavior. Invalid coordinates/steps are
  rejected before grid-index conversion.
- The original 0.2-second budget includes terminal checks, and the manager
  still rechecks every seed edge. Full sampled spline validation remains.

The finite terminal edges are an explicit graph extension. The heuristic still
targets the snapped index: no shortest-path or continuous rotating-footprint
guarantee is claimed.

## Local native results

Actual captured AStar C++ is compiled with Apple clang on macOS. ROS logging
and occupancy are test doubles. Eigen headers are read-only from the existing
local GTSAM 4.2 dependency under the sibling's dated local_macos runtime; no
sibling file is changed or imported. Each endpoint result records compiler,
commands, source hashes and a full Eigen header identity; the legacy result
references the same captured Eigen identity.

| Evidence | Result |
|---|---|
| `endpoints_scan_24_local_v1` | All five exact-endpoint contract cases fail as declared |
| `endpoints_scan_25_local_v1` | Initial seven cases pass |
| `endpoints_scan_25_local_v2` | Eight final cases pass |
| `legacy_scan25_local_v1` | Eight existing bookkeeping/segment cases pass |

The final endpoint cases cover changed heading with an alternate connection,
continued search after a rejected goal-grid connection, Unknown inside a
terminal edge, an occupied/Unknown exact endpoint, strict/failure/default reuse,
lattice/near/zero-distance goals, initialization failure after strict success,
the terminal-query wall budget, and 3D connector radius. Multiple assertions
share cases. `LOCAL_RESULT.json` contains result and binary hashes.

Independent review found no blocking source issue. Its two suggested coverage
additions, 3D radius and initialization failure after a previous success, are
included in the final eight-case run. This is local native search evidence,
not a full Foxy build, ROS replay, accepted spline, or live navigation result.

## Remote gate and next execution

Automatic approval review rejected `build_scan.py scan24_endpoint_trace`
before execution because authorization for source transfer to the specific
gpu5070ti destination was not recognized. An explicit user confirmation was
requested. Dr Sun subsequently replied “授权”, explicitly approving continued
source synchronization and bounded execution on gpu5070ti. The original denied
attempt remains recorded; execution resumes under that authorization. See
`REMOTE_APPROVAL_BLOCK.json`.

After destination authorization is received, use the already prepared local
packages and preserve the following order:

1. Build and capture install identity for `scan24_endpoint_trace`; replay it
   on `step6_body_reference/body_reference_030_inputs` under a fresh run ID.
   Read the exact last-edge/old-clear/new-blocked evidence before attribution.
2. Build and capture install identity for `scan_25`. Execute its endpoint
   fixtures in the pinned Foxy image, then replay identical corrected inputs.
3. Inspect seed, optimizer, full-spline and dynamic gates independently.
   No live walk until those gates are meaningful. Use a fresh live package
   containing the tracker V3 and explicit spawn/reference-height contract.

The pre-existing `walk_scan24_height030_right_v1` package remains unexecuted.
The earlier `stand_scan23_tracker_right_v1` video proves standing tracker
integration only. No successful stair-navigation video exists yet.

# v234: gpu40901 migration checkpoint

Status: **in progress; independent offline gates pass, original-artifact and
historical dynamic replay gates remain open.** No full-route physics was run.
The accepted physical baseline remains v232/v233 on gpu5070ti.

## What is available on gpu40901

Execution prefix: `/home/ubuntu/sun/vla_v234_20261017`. The local VLA repository
remains authoritative. Dr Sun confirmed gpu5070ti was powered off during the
transfer, so its original install/image could not be retrieved. All 317 native
source files were recovered from local pinned snapshots with exactly the
v232 source-inventory hashes. All14 packages were rebuilt in a new amd64 Foxy
image, `sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343`.
The receipt binds 883 installed files, all original 607 relative paths,
81 effective header resolutions and 44 resolved shared-library paths.
**This is a source-identical rebuild, not byte verification of the original
5070Ti installation.** See [receipt](results/native_rebuild_receipt.json).

Python 3.12.13 and the original hashed Linux package lock were installed in an
isolated environment. Core versions remain Newton 1.6.0, Warp 1.17.0,
MuJoCo/MuJoCo-Warp 3.12.0, ONNX Runtime 1.22.1 and USD 26.3. The original ARM
factory image and library are unchanged; the task-local Docker adapter runs
the pinned actor through a private static QEMU executable, without modifying
global binfmt. Media dependencies also live under this prefix.

## Executed gates

| Gate | New gpu40901 evidence |
|---|---|
| Frozen v232/v233 source | All 524 v232 archive files, 10 v233 binding files and 317 composed native files verified |
| Native build | 14 packages; original source contents unchanged |
| Fresh regressions | 165 distinct cases / 186 colcon records; zero errors, failures or skips; accepted attempt03 |
| Exception/failure closure | Existing delayed/stale-heading, callback containment and actual critical-subprocess-abort tests rerun |
| Scene and RL | 36 scene inputs; 1000 golden policy frames, maximum absolute error 0.005950927734375 against unchanged 0.01 gate |
| Terrain and soft field | Physical floor, support gap, coverage map, terrain bundle, raw ENV224B and ENV225 reproduce original hashes |
| PCT/SCAN environmental consumers | 30060 new static queries; zero mismatch |
| Installed Building admission | First request accepted;0/3821 rejected samples;3413 route points; exact goal |
| Route identity | Admitted shared-route CSV exactly equals frozen v232; SHA 3c30655acbc4e628f816f086a12470592590f11a234c2919a318a573540d37b9 |
| Actual ROS graph | 12 seconds, actual v232 graph/driver binding, generated profile passes original scalar gates; orderly exit0 and no false process failure |
| Factory and render | Original factory ready marker and2200-byte reply; actual EGL render plus original streaming encoder/decoder validates 2 frames |
| Newton integration | 0 steps in every host smoke; no full-route trial |

RL SHA 7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b,
the original historical_full endpoints and 0.35 m hard collision/support guards
remain unchanged. The offline route probe retains its original 0.35 m reference
height; the runtime graph retains the original 0.30 m reference/body clearance.
No navigation source, solver weight, goal tolerance or locomotion policy changed.

See [machine-readable summary](results/offline_summary.json) and
[source/install gate](results/evidence/final_source_install_gate.json).
All 209 compact returned evidence files, 3,941,503 bytes, were independently
checked against [return hashes](results/return_manifest.json). Build trees,
images, Python environments and regenerated binary fields remain on gpu40901;
none are included in the local evidence return.

## Shared-host storage and isolation

User-authorized cleanup removed 27,600,491,718 bytes of pip cache payload
(27,600,496,099 before; 4381 after). Free disk immediately rose to 143,285,907,456
bytes. After provisioning and concurrent shared-host work, the final snapshot
records 116,713,136,128 free bytes. No model, checkpoint, teacher bank or original
experiment was deleted. See [cleanup receipt](results/cache_cleanup_summary.json).

No peer process was signalled or reconfigured, and no shared environment,
driver or global binfmt was changed. Native jobs use task-owned containers,
at most 4 CPU quota, 6 GiB each and reduced CPU shares. Concurrent test/probe jobs
each use 2 CPU quota and separate ROS domains. CPU smokes disable CUDA inference.
The existing MPS server remains PID 589593 / 34 MiB in both GPU snapshots. Several
other previously observed processes exited and a new external GPU job appeared;
the snapshots do not establish unchanged peer performance or lifetime.
See [before](results/evidence/host_before.json) and
[after](results/evidence/host_after.json).

## Retained preparation failures

- Original Docker Hub endpoint timed out; the resolved ROS base digest was
  fetched through the mirror. The legacy builder required removing the
  unsupported progress flag. The accepted image uses the original dependency
  recipe with pinned GTSAM/pybind11 and recorded image identity.
- Atlas attempt01 lacked the transitive v81 diagnostic headers. Supplying the
  original headers allowed attempt02 to reproduce the exact original fields.
- Test attempts01/02 used generated fixture defaults inconsistent with the
  original component fixture: simulated clock and then base_link. Restoring
  wall time and base fixed the TF fixture; the complete attempt03 passes.
  Native source and runtime thresholds were not edited.
- Render smoke02 exposed missing private ffprobe dependencies. Extracting
  versioned Debian libraries into the private prefix allowed smoke03 to pass;
  the shared system was not installed into or upgraded.

## Required continuation

Temporarily make gpu5070ti available and transfer its original pinned native
image/install/underlays for comparison, plus:

```text
/data/sun/vla_mppi_20261009/stair_collision_replay_20261016/input
/data/sun/vla_mppi_20261009/stair_collision_replay_20261016/critical_input
```

The historical replay requires 508 original clouds with poses and 78 query
frames. Local summaries retain 1769 file hashes, not those input bytes. Static
probes and old verdict CSVs cannot substitute for the 126324+3 dynamic hard
decision replay. Recheck the original607 installed hashes and run that replay
before declaring full offline migration acceptance. Preserve v234's successful
independent gates and failed attempts. Arrange a physical route only afterward.

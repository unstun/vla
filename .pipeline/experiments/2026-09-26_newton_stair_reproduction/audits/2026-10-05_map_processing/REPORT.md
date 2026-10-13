# Why the v76 map input scope reached 977 ms

Stage: experiment + analysis, 2026-10-05. The recorded 976.721 ms is accumulated
work across **12 synchronous input refreshes**, including **seven different
scans** during one cold-recovery chain. It is not one packet taking nearly a
second to decode. Native replay locates the main intrinsic cost in voxel
occupancy fusion/inflation and sliding-map cell clearing. The original live
multiplier is not fully reproduced by the isolated replay.

## Original round, directly verified

The v76 round starts at native 29.235561 s and takes 1,307.535 ms. Its initial
warm connector fails; the native terminal-recovery A* hits its existing 200 ms
limit; prefix and fixed-height fallback continue. Fresh-input checks run at the
target, replan, warm, prefix, rebound and final boundaries. Seven single-cloud
drains apply newly arriving scans while that same round is still executing.
See [the actual 91-line round](original_spike.log) and
[parsed refresh sites/counts](original_flow.json).

| Original inclusive scope | Wall time | Same-thread CPU | Calls |
|---|---:|---:|---:|
| All input refreshes | **976.721 ms** | **941.490 ms** | 12 |
| Point-cloud callbacks | **725.773 ms** | 695.915 ms | 7 |
| Sliding-map function | **245.565 ms** | 242.500 ms | 21 |

Cloud callbacks contain sliding checks, so the three rows must not be added.
CPU is 96.4% of the input elapsed time: only 35.231 ms separates elapsed and
thread CPU in this aggregate measurement. Waiting/scheduling alone cannot
account for the complete delay. This does not rule out live memory/cache or
emulation/load effects increasing the cost of executing the same code.

The seven scans are 181–187, stamps 29.215572–29.815243 s, containing a total
of **102,266 points**. They match the recorded wire cloud widths and sensor
positions/quaternions exactly. The actual runtime `planner.yaml` hash also
matches the replay configuration. [Wire/config verification](wire_inputs.json)
checks published observations; it does not reconstruct native DDS take timing.
There is no evidence here that one identical scan was rebuilt 12 times.

## What the callbacks actually do

`refreshSensorInputs()` takes pending messages and calls the original pose and
cloud callbacks on the planning thread. The cloud callback converts points,
transforms them into world coordinates, classifies terrain returns, casts rays
through the voxel grid and immediately fuses occupancy. Fresh checks inside
recovery therefore execute mapping work before planning can continue.

The unchanged configuration is a **200×200×100 = four-million-voxel** local
grid at 5 cm resolution. Inflation radius is 0.35 m, with 0.55 m upward and
0.35 m downward inflation. The native offset list contains **2,755 neighbors**
for every occupancy insertion/removal. This is a computational consequence of
the existing safety envelope, not a proposal to shrink it.

Relevant exact native sources:

- `runtime/scan82_optimizer_failure_v63/src/plan_env/src/grid_map.cpp:947`
  — synchronous ordered refresh and callback dispatch.
- Same file, `:1030` — point conversion/classification and immediate occupancy
  update; `:601` — ray traversal; `:739` — cached voxel fusion.
- Same file, `:328` — occupancy state change and semantic-history erasure;
  `:304` — per-neighbor inflation updates.
- Same file, `:385` — sliding threshold, clear mask and outgoing-cell reset.
- `src/plan_manage/src/planner_manager.cpp:309` and
  `src/bspline_opt/src/bspline_optimizer.cpp:1001` — refreshes before replanning
  and inside rebound optimization.

Ray casting, occupancy integration and sliding/inflation loops are inherited
SCAN mechanisms. This integration additionally maintains terrain/nonterrain
history and explicitly refreshes inputs inside the recovery chain. Thus some
mapping cost is charged to an already running planner round. The original
upstream source is pinned in v71; this is not evidence that the original ROS1
demo has the same measured 977 ms delay.

## Native profiling result

Observation-only v78 replays all **188 scans from the start through scan187**
using exact archived point arrays and poses, then analyzes the seven relevant
scans. It uses the unchanged navigation/surface/physical-floor payloads and
configuration, an unmodified map executable and an instrumented executable.
There is no DDS, optimizer, simulator physics, rendering or controller in this
component replay. The two map dependencies and both executables build in the
same pinned amd64 Humble image on Mac, with three CPUs and 5 GB configured.

Three runs per executable, with reversed order in the second pair, all produce
the same final digest of occupancy/inflation/ray/count buffers, origin/counter
and terrain/nonterrain/history sets:
`da01d77d0e45f6f6a0884df0493dbcac3fae97bd42d13b96fffc44f8ec4a64af`.
Removing the observation additions reconstructs the exact parent map source.
This validates the measured component's state parity, not full navigation safety
or trajectory continuity. [Full summary](profile_summary.json) and
[selected per-scan measurements](../../versions/v78/profiles/attempt02/selected_scan_profiles.jsonl)
retain the source hashes and results.

The representative second instrumented run has these seven-scan totals:

| Stage | Measured wall time |
|---|---:|
| Occupancy fusion, including occupancy-triggered inflation | **163.691 ms** |
| Sliding-map work | **57.719 ms** |
| Point transformation and terrain classification | **49.746 ms** |
| Ray traversal | **37.653 ms** |
| PCL message conversion | **0.416 ms** |

Sliding is inclusive; its cell reset costs 56.436 ms while mask construction
costs 1.099 ms. Allocation of the large mask is not the dominant measured sliding
cost. Cloud/raycast sliding checks are nested; compare the end-to-end batch
time rather than summing every scope. Original refresh entry/exit timestamps
did not record these finer timings, so this table is **replay**, not a fabricated
decomposition of the historical 977 ms.

The operation counts are identical across all three instrumented runs:

| Work for seven scans | Count |
|---|---:|
| Input points | 102,266 |
| Terrain-return classification calls | 96,871 |
| Unique endpoint rays after deduplication | 57,900 |
| Traversed ray steps | 984,814 |
| Cached voxels fused | **926,950** |
| `applyOccupancyUpdate()` calls | **905,074** |
| Occupancy transitions | 7,525 |
| Inflation calls, including sliding removals | 9,138 |
| Inflation neighbor visits | **25,175,190** |
| Sliding checks / actual shifts | **21 / 3** |
| Outgoing cells cleared / occupied outgoing cells | **474,416 / 1,613** |

The inflation count is exactly `(7,525 + 1,613) × 2,755 = 25,175,190`.
About 927,000 voxel updates arise from only 102,266 measured points because
rays also update free space. Occupancy fusion invokes semantic set/history
maintenance and may visit thousands of neighbors for a single state change.
Sliding clears large outgoing slabs and removes the inflation contribution of
occupied cells. These loops explain why a modest point packet can require
substantial CPU work; packet conversion itself is small in this replay.

## What is established and what remains unresolved

The original input cost is real CPU-intensive synchronous mapping accumulated
between retries. The principal measured intrinsic hot path is occupancy
fusion/inflation, followed by sliding-cell reset and per-point classification.
The 21 sliding calls do **not** establish 21 map moves; the replay has only three.
Repeated freshness calls are not all expensive: empty drains do not replay a
scan, and eighteen of the replay's sliding checks return without a shift.

The unmodified seven-scan replay takes **266.600–312.992 ms**, median310.099 ms;
the original input scope is976.721 ms. The exact historical native callback
ordering/map history, active planner/cache context and concurrent live load
were not restored. Their respective contributions to the remaining difference
are **unresolved**. The isolated result is not a measured 68% optimization or a
complete reproduction of the original delay. Captured finer live counters are
needed to assign that multiplier precisely.

A cold search delays the next input boundary; new scans then arrive during
recovery, each carrying additional map work on the same planning thread. The
original trace directly shows this accumulation. There is no whole-round
mapping or recovery cost bound under the current architecture. Warm seed
optimization being fast therefore does not guarantee a 33.3 ms planner round.

The next useful instrumentation is per-refresh/per-cloud timing, real shifts,
cache sizes/clears and voxel/inflation counts in the **live native chain**.
Then optimize proven hot operations or provide mapping snapshots with explicit
freshness/publication rules. Do not infer that dropping old scans, skipping
occupancy updates, changing safety inflation or adding a v49 timeout is safe
from this component test. No such repair is implemented here.

## Provenance and storage

v78 is a frozen diagnostic child of v76/nativev63. Source/snapshot hashes,
paired support assets, actual wire poses/config and final component state parity
pass. Zero physics steps and no remote GPU job are executed. v48 remains the
runnable reference; v49 stays frozen/excluded; no goal/yaw/PVA/safety/stop rule
changes. The main30Hz/continuity repair remains open.

Original raw data remains at
`gpu5070ti:/home/sun/vla_artifacts/2026-10-04_corner_start/v76_mac_trial01_attempt01`.
Unique full profiling results are archived under
`gpu5070ti:/home/sun/vla_artifacts/2026-10-05_map_processing/v78_profile_attempt02`.
Source/config, compact selected measurements/report/hash receipts remain local;
selected input conversion and temporary builds are regenerable from pinned
sources and original member hashes. [Storage/cleanup receipt](storage.json)
records verified retention and any removed temporary bytes. Earlier unfrozen
selector/relative-path preflight errors are retained separately; neither ran
physics or profiling.

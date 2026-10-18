# v237 on gpu5070ti: one original-route/terminal pass

At Dr Sun's direction, execution returned to gpu5070ti. Exactly one new
physical attempt (`v237_linux_full_attempt01`) passes the unchanged original
spatial route, arrival and final measured PD gates. Native source/install are
v232; the original v233 host binding adds only v236's scanner deadline repair
and new execution/provenance identities. Original RL, endpoints,0.35m hard
collision/support guards and0.1s sensor period are unchanged.

| Measurement | v219 |v232 / runv233 |v232 + scanner repair / runv237 |
|---|---|---|---|
| Physical recording end |123.563721s |121.564819s |124.223358s |
|45–55s successful/completed local rounds |118/208 (56.73%) |273/275 (99.27%) |296/296 (100%) |
|45–55s measured pauses >=1s |1 (3.298s) |0 |0 |
| Final XY error |Preserved original gate pass |0.141198m |0.118992m |
| Final measured PD hold |Preserved original gate pass |4.397583s |4.377594s |

v237 ends FINISHED, process exit0. Original full-route gate passes no-fall,
original start/goal/yaw, no reset/continuous poses, final held heading/height
and shared execution-state checks. It retains5801 states, maximum consecutive
recorded position displacement0.048459615m. Final yaw error0.120769248rad and
height error0.001677322m remain inside unchanged gates.220 consecutive final
FIXED_STAND samples measure the4.377594s hold.

## Scanner and preflight

1132/1132 actual scans complete,0 deadline failures; mean22.719534ms,
maximum30.208718ms, maximum measured runnable wait0.728770ms. All are inside
the original100ms wall deadline. No early-check waits were required in this
physical run. That branch is exercised by the offline native-clock catch-up
regressions/probe, rather than inferred from this idle-host route.

[Preflight](../../versions/v237/PREFLIGHT.md) checks original317 source and607
installed hashes, seven regressions,250 original-ray/catch-up cases,1000-frame
policy golden and the real12-second graph/profile before physics. No native
rebuild or shared environment/peer mutation occurred. Host physics retains
original flexible CPU affinity; native Docker retains6 CPUs/6GiB. Do not
interpret the shared40901 versus idle5070Ti difference as algorithm speedup.

## Measured body-edge geometry

The original installed ENV225 probe evaluates actual recorded XYZ and planar
body yaw; radius0.35m/offset0.18m and original field bytes/FNV remain fixed.
For100 samples in[45,55): all floors known, minimum extra edge margin
**0.128962663m**, P05 0.149939753m,95% at the0.15m score cap,0 negative samples.
The same spatial stair region has50 known samples, minimum0.128962663m and
P05 0.136886068m. The measured spatial-region span is43.207882–48.105190s;
the fixed45–55s benchmark is therefore not identical to the entire spatial
stair traversal. All1132 whole-recording samples have known floor and no
negative margin. This is offline body geometry relative to the existing
0.35m envelope; it does not add leg-contact or selectedSurface-admission claims.

## Timing and acceptance boundaries

RTF0.999992745, mean successful local planning25.591114Hz, P95 solve32.802389ms,
maximum308.107173ms;16 rounds exceed100ms. The original analyzer retains
full_qualification=false and sustained_30hz_validated=false. The original
route/terminal gates pass while sustained30Hz, other starts/maps and repeated
reliability remain unvalidated. Existing accepted selection staysv232/v233
pending separate review. The40901 writer-backlog failure is retained and
unresolved; the256-item bound was not changed or exercised as a failure here.

## Videos and evidence

- [Complete actual attempt](delivered/v237_full_attempt01.mp4).
- [Same-host three-way physical-time comparison](delivered/full_physics_comparison.mp4):
  leftv219, middlev232/runv233, rightv232+scanner repair/runv237.
- [45–55s comparison](delivered/stairs_physics_45_55.mp4).

The individual video preserves the complete recorded startup/navigation wall
timeline, pauses, actual native local/global trajectory overlays and final
hold. Comparison uses a common physical-time grid, selecting recorded frames
at or before each grid time and black after an episode ends. No interpolation
or new physics. Full decode, every causal source index, nonfuture curve events,
current/snapshot hashes and terminal display are checked. The first render
correctly rejects a manifest-layout mismatch before any frame: v237 snapshot
paths are version-relative, while the old consumer assumes repository-relative
paths whenever snapshot_locations exists. The corrected adapter verifies both
current and preserved files under the declared version root. Failed root/logs
and original renderer sources remain intact; successful display uses
video_v237_render02. Physical source/manifest/capture remain unchanged.

Raw root on gpu5070ti:
/data/sun/vla_mppi_20261009/trials/v237_linux_full_attempt01.
Original archive330,322,822bytes /1136 verified members, SHA
fb4d1eab6dfaa92d3d485d8319b4cfa330003a8dd317b24cc76fbdd60f0d92f2.
Only compact results, source/provenance and review videos return locally;
raw arrays, archives, build outputs and CMake caches stay remote.
results/return_manifest.json and LOCAL_DELIVERY.json bind returned bytes and
local checks. Source commit6a9e531c freezes the execution adapter; this audit
records subsequent independent display/delivery checks and their limits.

## Verified local return

All77 declared payload files /34,009,167bytes match the remote return manifest
in size/SHA-256. Supplementary original causal-frame/host/quality receipts
also pass their cross-hashes. Individual video3720frames, common-physics full
comparison3728frames and stair comparison301frames pass full decode. Direct
initial,48s staircase and terminal-arrival visual samples pass. All executed
audit source hashes and v237 current/snapshot hashes match. No raw/build/cache
bytes are included. Local final file identities are in LOCAL_DELIVERY.json.

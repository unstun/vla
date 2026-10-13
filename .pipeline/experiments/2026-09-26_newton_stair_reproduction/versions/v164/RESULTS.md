# v164: local original-route arrival; Linux repetitions pending

Stage: experiment and analysis. The only native change from v163 expands
stopped steering proposals from five near-forward angles to twelve angles,
including side/back directions. Every in-place turn is checked at steps no
coarser than 1.40625 degrees. Full segment, endpoint, PVA, dynamics, freshness
and once-per-owner guards remain. At most five expensive planner attempts are
allowed. Maps, goal tolerance and the mission retry budget are unchanged.

The captured v163 stopped-stair replay changes from rejected to accepted:
a 5 cm curve, 0.659 s duration, 331 collision samples, and all original guards.
The older v156 corner replay still passes: 0.601 s and 306 samples. Controller
tests pass (37 unique cases / 40 colcon entries); inherited plugin tests and
nine gateway tests remain separate evidence. 18 host tests and the actual
Nav2 graph pass. Frozen source: 3,740 pairs and 618 runtime inputs.

`v164_mac_full_attempt01` starts at the original spatial origin and actual
physics time zero, reaches the original goal and completes measured PD hold.
The route gate, six stop-before-replacement proof checks and copyback pass.
Sensor path: 77.654 m; dense recorded path: 78.845 m. Final XY error: 0.142618 m;
final yaw error: 0.104984 rad (unchanged limit 0.25 rad). RTF: 0.991665.

One short steering curve (generation 4, trajectory 1447) has 17 nonzero tagged
raw commands. Its angle lies near the original 11.25-degree band; the recorder
pose is not the exact callback input. Do not claim that the wider offsets were
physically exercised by this event. Wider-offset acceptance is demonstrated by
the captured-stop native replay. One full arrival is not reliability acceptance.

All 291 physical files were remotely archived and verified: 481,423,360 bytes,
SHA-256 `22e731e8e6d66eb1320800d28d935ee1831c841c46ec1ba802d8098d40b16b7a`.
See the per-run results, proof audit, steering evidence and archive receipt.
v165 rebuilds the same 647 native source files on Linux for five independent
original-route trials; Mac and Linux outcomes must not be pooled.

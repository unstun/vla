# v229: support-aligned GPMP output height

Parent frozen v228, after the approved three commits. One behavior change:
repair GPMP output Z using the existing matched PCT layer, original canonical
PCT cell and source surface height. Preserve XY geometry, original goal/start,
all native thresholds, body geometry, RL and optimizer weights/tolerances.

The 26/3422 WrongHeight samples split into 13 true terrain-height errors and
13 navigation-height proxy depressions. DenseElevationMap GetHeight truncates
rather than using v228 cell identity. A band around that old height is wrong.

At canonical PCT cells, reuse ground_valid_, ground_, ceiling_, GPMP layers
and ENV225 source surface heights. Compute the intersection of the native
proxy's unchanged clearance/tolerance band, the actual surface body-clearance
band and original ceiling bound. Prefer surface+reference_height within BOTH unchanged native-tolerance
bands. Body clearance is nominal, not a new minimum: imposing it as a hard
lower bound incorrectly disconnects feasible steps. Keep a 5 mm inset from
the original tolerance limits for map quantization. Invalid/ambiguous association or empty
intersection rejects the candidate. Densify along the existing XY polyline,
intersect adjacent height bands so interpolation does not jump across cells.
Final native translation/rotation checking remains mandatory.

Owned modules: EnvironmentalField exposes source surface height (no admission
power); PCT adapter projects its GPMP Z; a small scalar-band helper and tests.
No native checker relaxation, physical-floor label grant, recovery connector,
feedback protocol, weight tuning or new physics. Disabled environmental mode
retains original output. Benchmark full actual plugin, one-check admission,
raw point-cloud clearance and unchanged v217 replay before freezing. Latency
~0.35s is a target to measure: v228 one search+smoothing is itself ~0.70s.

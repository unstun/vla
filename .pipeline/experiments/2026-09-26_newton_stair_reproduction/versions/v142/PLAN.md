# v142 actual zero-time recording

Stage: experiment + analysis. Local VLA repository is the sole source of truth.

The prior v141 video began with a real recorded state at native time 0.08 s. This recording adds the actual initialized body and joint state at native time exactly 0.0 and step counter 0, immediately before calling the unchanged factory initializer. The wrapper reads state without advancing physics, compares the state again, saves the zero-state witness, then calls the original initializer unchanged. It prepends this actual state to its returned video samples.

Native navigation remains the qualified v139 build02 installation. Maps, gains, factory startup algorithm, physics, stop/replacement gates, and local planning are unchanged. v141 is the preceding frozen source manifest; v139 is the host and native implementation parent. No native rebuild or new navigation acceptance is claimed.

Sync gate: freeze source pairs and runtime hashes locally, transfer v142 only to `/data/sun/vla_mppi_20261009/repo`, verify all hashes remotely, run host/ownership/graph checks, then execute one bounded original Building candidate recording. Keep all raw records on gpu5070ti; return compact provenance and a review MP4. Any failed attempt is retained and reported. This new recording does not enter the completed six-run v139 acceptance denominator.

Expected evidence: initial_state.json, video_states.json starting at exact 0.0 s, factory_video_states.json, native terminal/posture/copyback metrics, full source/retention hashes. Display starts at that measured state and preserves v141 causal simulation-time startup and wall-time navigation. No invented or reset display timestamp is used.

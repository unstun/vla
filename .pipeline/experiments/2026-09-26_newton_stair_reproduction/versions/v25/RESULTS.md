# v25 live full-profile attempt rejected

The actual run v25_historical_full01 correctly writes pct_layer=null, but
load_runtime_config silently drops None during default merging. The resolved
runtime therefore retains the old layer1. LayeredPctClient records explicit
start_layer=target_layer=1; native PCT returns145 points and17.243904m, ending at
body z1.860560 instead of the intended4.833031m. The live profile gates detect
this failure. The direct native planner preflight had correctly handled None,
but did not include this intervening configuration loader.

The run ends after26.297176s simulated, only.050461m forward, with odom_stale.
Command transport records two reconnects and two clock_observation_stale errors.
It has one moving curve, verified stopped PD state and copied-back evidence;
no goal arrival or complete-floor success. Config-layer forwarding and runtime
freshness are separate findings; fixing one does not explain away the other.

v26 will preserve explicit null only at map.pct_layer, keeping omission and all
unrelated None semantics unchanged. Regression must cross the actual config
loader, LayeredPctClient, TCP worker protocol and native PCT, preserving the
resolved configuration and forwarded request as evidence.

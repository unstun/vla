# v19 results

Original precision recovers 32 recorded floor endpoints at the unchanged 0.05 m
classification band. The same 86775 cells, XY and costs remain selected.
Host and Linux publisher tests pass; old 66/67-scan continuations and the v18
189-scan failure both pass with full native trajectory checks (new case repeated).

Physical trial `v19_building_route01` remains unsuccessful. It executes 45.187 s
of simulation, advances 2.159 m forward and 0.259 m upward, and generates six
moving curves before another sustained planning blockage. The later terminal
reason is `heartbeat_stale`; two command reconnects correspond to actual clock
estimate TTL expiry. No acceptance threshold was relaxed. The actual published
ground SHA is 97d2dfbdb60c91e8473ab57f348923360f139da1130b4e9b7dd57e8655c15ca2.

The older single-cell source investigation proves a missing top-surface sample
in the original PCD, not a global 0.05 m asset registration offset. That evidence
must not be generalized to the new stop without replay. The new fixture lives
under `audits/2026-09-27_v19_frontier`; the short stair route and original complete
building remain unvalidated.

# Step 1: A* bookkeeping repair

The isolated scan_20 fixes collision-rejected nodes being marked discovered,
zero initial infinite cost, and mutable-pointer heap keys. Open records now
capture priority, round and revision; decreased costs enqueue a fresh record,
and stale records cannot close a node or terminate at the goal. The original
0.2 s budget includes stale-record processing. Occupancy, heuristic, map and
track inputs are preserved.

The actual native source (with only occupancy/logger test doubles) reproduces
three scan_19 failures: blocked-first/free-later, heap decrease-key order, and
cross-round node pollution. scan_20 passes all six regression groups, including
256 fixed maps checked against an independent Dijkstra oracle. A controlled
mutation omitting the actual improved-cost enqueue fails fixture 0 (cost
13.0711 versus 11.6569), while the real candidate passes. The first test-wrapper
attempt failed its container-root path calculation before native compilation;
it is preserved as native_scan_19, and native_scan_19_v2 is the valid red run.

The pinned Foxy build and before/after source gates passed, with 454 installed
files captured. On the exact same recorded-input prefix, the 179 seed-search
failures become zero search failures and 179 seed-edge rejections. There is no
endpoint mismatch, search time-cap hit or moving spline. This confirms a real
change in native planning behavior, but does not establish executable navigation.

The next isolated fix (scan_21) aligns A* edge checking with the existing seed
half-cell sampling gate. It must preserve unknown blocking and final spline
validation. Recorded evidence is indexed by RESULT.json and each immutable
native/replay directory. One independent read-only reviewer checked source,
regression scope and mutation sensitivity. No live simulation was run in this step.

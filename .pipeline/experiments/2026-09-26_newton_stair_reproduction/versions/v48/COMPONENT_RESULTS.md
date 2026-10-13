# v48 component gate

Build02/test02 passed 34 native, 48 cache and 94 warm assertions. Both cold
geometry outputs equal their frozen oracle. Six paired warm-only solves pass
at roughly 3 ms versus 10.6–11.7 ms cold, with independent PVA/dynamics/whole-curve
checks and new native trajectory identities. Identity, clock, PVA, stale/bounds,
unsafe connector, route/emergency and original fallback/no-publication negatives
pass. Build01/test01 and its source are retained. See RESULTS.md for timings and
full-scene claim boundaries; the paired stopped states do not represent the live
tail distribution. All returned component/build files passed local SHA-256.

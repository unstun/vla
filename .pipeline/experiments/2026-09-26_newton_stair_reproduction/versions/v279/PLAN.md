# v279 Conservative height-envelope cache

Parent frozen v272. v278 uniform free-space indexing is not adopted: parity
passed but timing gains were negligible. A04 has 26,800 exact heights in only
90 intervals, fragmenting the exact-height source cache.

The original exact query and complete assessment stay unchanged. Positive cache
entries may additionally certify a whole 0.05 m height interval. Compute the
union of body vertical ranges and remove only source material valid throughout
that interval: full volumes eligible at both extrema and caps in the intersection
of strict step bands. The remaining obstacle set is a superset for every real
height in the interval. Its positive radial clearance minus XY movement is a
sufficient-free proof. Nonpositive envelope results are never collision verdicts;
retain exact-height witnesses for collision. No source/query coordinates change.

Require full legacy/source parity, dense edges, interval/bin-boundary controls,
all native tests and measured hard-route latency before freezing. No physics.

Development01 passes all checks including 102,477 full source comparisons and
12,000 interval-boundary checks, but A04/G05/D07 still take 1.828/1.789/1.858 s.
Development02 narrows the proof interval to 0.01 m to retain more common step
material; it asks the conservative envelope first and needs an exact query only
when the proof is inconclusive. This is a cache-performance parameter, not
height quantization or a support allowance. Both old/new bin-boundary suites
remain (24,000 checks). All previous implementation/logs are retained.

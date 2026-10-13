# v81 snapshot implementation results

Frozen source and all 102 files reproduce exactly through the materializer.
Eight native packages, 26 snapshot/pairing/freshness/support/failure/shutdown/
newest-curve checks, all 188 sync/async scan digests and original native/recorded
safety suites pass. Typical snapshot copying falls about 20–22 → 5–6 ms after
sharing unchanged support. These component checks do not establish live mapper
throughput. The integrated v82 runs fail continuity because stale completed maps
trigger existing emergency holds. v48 remains the reference; see the repair audit.

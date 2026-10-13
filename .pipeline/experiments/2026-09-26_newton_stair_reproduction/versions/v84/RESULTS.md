# v84: admission comparison completed; plain latest-only rejected

Stage: experiment + analysis. Six actual native component runs use the same
188 recorded scans, exact paired poses/support and unchanged v82 map. No
physics or upstream full-planner reproduction was run. Admission follows FIFO,
a 50 ms timer/latest slot, or a latest-slot consumer. The latter two adapt the
surveyed scheduling mechanisms, not ROG-Map's complete mapping implementation.

| Exposure / admission | Fused / skipped | Original occupied cells no longer occupied | Maximum age at map completion | Maximum age while the last map remains in use |
|---|---:|---:|---:|---:|
| Nominal / FIFO | 188 / 0 | 0 | 171.9 ms | 248.3 ms |
| Nominal / timer | 188 / 0 | 0 | 174.3 ms | 274.3 ms |
| Nominal / latest | 188 / 0 | 0 | 153.4 ms | 223.4 ms |
| Two 650 ms blackouts / FIFO | 188 / 0 | 0 | 676.3 ms | 776.2 ms |
| Two 650 ms blackouts / timer | 172 / 16 | 252 | 197.7 ms | 858.8 ms |
| Two 650 ms blackouts / latest | 176 / 12 | 173 | 186.6 ms | 859.0 ms |

The complete map digest for all three nominal arms and blackout FIFO equals
the original v78/v81 recorded-state digest:
`da01d77d0e45f6f6a0884df0493dbcac3fae97bd42d13b96fffc44f8ec4a64af`.
Blackout latest differs in 516 occupancy categories and loses 2,166 cells from
the original inflated set. These are map-evidence differences, not 173 distinct
physical objects. Timer selection varies with actual measured native service
time; this attempt skips 16 frames, while the interrupted earlier attempt
skipped 12. Neither result supports state equivalence.

The native synthetic negative offers eight observations of an unmapped obstacle
and then a different clear-direction observation within one blocked admission
window. FIFO retains occupied evidence; latest-only does not see the obstacle.
This fixture was deliberately constructed; it is not claimed to have occurred
in the captured physical run.

Both blackouts are controlled injections. Discrete-event admission time advances
by measured native service time; this does not reproduce historical DDS callback
ordering or concurrent physics load. Comparing CPU totals between differently
selected inputs is not an equal-work speedup. Completing a fresh map after a
stall does not remove the stale-map interval during that stall.

Decision: **do not enable plain newest-frame dropping in navigation**. Existing
250 ms freshness remains mandatory. First reduce real mapping service work or
qualify an evidence-preserving admission policy; separate sensor veto cannot
silently grant an expired map freshness.

Evidence: `analysis/attempt02/comparison.json`, per-arm returned events and
summaries, `results/attempt02/transient_attempt02.log`, `input_identity.json`,
`build_receipt.json`, and the shared storage receipt in
`audits/2026-10-08_mapping_admission/`. Initial environment/build and interruption
failures are preserved under `failures/`; missing initial temporary raw is
explicitly disclosed. Durable attempt02 is the qualification record.

# Ranked diagnosis and falsifiable predictions

1. **Evidence expires during avoidable terminal-neighborhood search.** If this
   causes the stops, the original prefix is clear before the search; advancing
   only query time past the original 0.35 s cloud-age limit yields StaleInput.
   Removing the unnecessary goal search while retaining a forward reference
   should remove its 200 ms cost without granting stale or blocked geometry.
2. **A real new obstacle blocks the current body/remaining curve.** If this is
   the primary stop cause, the chronological same-prefix replay should retain
   a geometric rejection with fresh evidence; removing goal search cannot
   clear that rejection. Preserve any such veto and its whole-curve check.
3. **Warm target connector/optimizer failure directly commands zero.** If true,
   the first failed nominal round should clear tracking. Trace actual safety
   transitions and emergency Bspline publications rather than inferring this
   from the warm_accepts CSV column. A failed seed has a same-round cold retry.

The original read-only extraction reproduces two measured short stops. The
native baseline reproduces the 200 ms target search and the stale snapshot
rejection. Hypothesis 1 explains both emergency episodes; 2 remains necessary
for other queries, and 3 is false as a general rule. The 109.0717 s optimization
failure is real but the old clear trajectory continues without emergency stop.

Paired replay uses the full published scan prefix and recorded map cutoff.
It deliberately does not claim to recreate DDS take batching, exact writer
completion times, continuous ROS-clock execution or new robot motion.

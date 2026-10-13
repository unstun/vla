# v169: bounded Mac Docker acknowledgement wait

Stage: experiment and analysis. Host parentv167; all native bytes remainv167.
Macv167/01 was interrupted at48.145simseconds by an exhausted3x100ms ACK
wait. Linux receipt records show the exact unmodified state1857 committed after
353ms; no native failure was recorded. Copyback is unqualified because hostlast
ACK was1856 while receiverhead1857. Raw failure is retained and must not count as
an arrival or a recovery test.

Keep the three idempotent attempts and100ms send timeout; allow400ms receivewait
per attempt. No physics advances inside the call. Original source timestamps,
2s applied-state reader freshness, all independent controller/scan/body freshness,
and stop-dwell evidence remain unchanged. No automatic timestamp refresh or
infinite retry. Test the observed350ms mechanism against old/new actual clients,
550ms retransmission, absent receiver bound, changed/reordered/expired evidence.

Require actual local graph and immutable nativev167 receipt. Freeze before a new
original-start fullroute; keep nativeLinuxv168 separate from this Mac hostchange.

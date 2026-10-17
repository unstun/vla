# Inline review of the local stair continuation

Stage: experiment + analysis. Review performed in the main session; no new
implementation/check subagent. The task remains in progress because stair
navigation and original Isaac A4 acceptance are open.

Owned implementation is confined to this experiment, plus the previously
qualified E1 scene seam. New boundary behavior is documented in
`.trellis/spec/backend/newton-clock-bridge.md`. All archived native source,
installed binaries, original runtime modules and scenario inputs match their
recorded hashes. No formal training, robot actuation, remote restart or sibling
repository change was performed.

Direct checks:

- Clock:1,124 cases against extracted upstream C++; fresh/stale/future,
 250ms watchdog and sync loss; actual Mac/Linux convergence and expiry.
- Executor: traced2/150 multi-threaded body callbacks versus149/149
  single-threaded; retain original callbacks and document selection.
- File fault: standalone overlapping/disjoint bind-mount probes preserve
  truncated JSON. Standard PyZMQ probe validates150 positive and four independent
  negative cases; no retry/ignore inside the original evidence reader.
- Full integration:15 checks in `stair_native_walk_v2_review.json`, including
  actual policy commands, paired raw/planner sensing, source-time mapping,
  source parity, byte-exact tmpfs return and measured stop.
- Video:350 frame hashes/source timestamps, full MP4 decode and first/middle/end
  inspection. The delivered file is a regular copy with the verified SHA.
- Syntax:27 owned Python scripts parsed successfully. No project-wide Python
  lint/type command is defined for these standalone experiment scripts.

Findings retained explicitly:

- Navigation failed with command_timeout. Driver FINISHED is recording status.
- Clock rejection caused10 command reconnects and22 zero-command updates.
-124 missing-state reader observations occur before the first snapshot;
  there are zero reader errors after it.
- The two earlier ZeroMQ probes' `docker cp` receipts do not prove Linux tmpfs
  byte identity. Their runtime ACK tests remain valid independently.
- Human physical collision/avoidance and full stair completion are untested.
- The published curve and timing logs establish34.250s retiming, but exact
  initializer seed samples must be captured before an offline root-cause claim.

Repository-wide `git diff --check` found four existing trailing-space lines in
the older `isaac_runner/runner_external_episode.patch`, outside this continuation.
They were preserved. Scoped current-edit checks are recorded in
`inline_quality.json`. Other dirty Isaac artifacts and project state were not
staged, committed, archived or reformatted by this continuation.

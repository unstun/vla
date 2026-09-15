# OmniVLA vision-language-action evidence audit

Status: runtime evidence synchronized and prepared for human review; no human
decision has been recorded.

This experiment applies one frozen, receive-only 24-forward matrix to each of
the pinned OmniVLA-original and OmniVLA-edge candidates. It preserves every
scheduled attempt, including failures, and prepares evidence for human review.
It does not decide whether either candidate is a VLA.

The local repository is the source of truth. Remote hosts are execution copies
only, and no panel may be reported as run until its artifacts are synchronized
back and local/remote hashes agree.

The frozen matrix completed with 48/48 successful, retained records: 24 on
OmniVLA-original and 24 on OmniVLA-edge. All declared three-repeat conditions
had zero observed repeat dispersion. Every counterfactual differed numerically
from its base trajectory, but this is not evidence of semantic correctness.
In particular, the `stop` outputs retained nearly the same forward extent as
`move forward`, and the left/right endpoints did not form a clean signed
lateral separation. See `analysis/observations.md` and the review page before
making any label or architecture decision.

The OmniVLA-edge frozen matrix did not require a live robot connection. After
that run, Dr Sun connected the Jetson to the Lite3 Wi-Fi and a separate
read-only snapshot confirmed `192.168.2.70 -> 192.168.2.1`, zero loss across
three probes, and an open SSH endpoint. This is connectivity evidence only,
not a latency test or a reason to relabel the frozen inference results.

The strongest justified claims are limited to: the pinned candidates were
`reproduced` for this frozen receive-only forward matrix; their callable output
paths were `integrated` into this experiment's immutable record contract; and
only that contract was `validated`. VLA identity, navigation utility,
calibration, closed-loop behavior, safety, latency, robustness, and real-robot
deployment remain untested. No output was sent to a controller.

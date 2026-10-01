# v27 component results

Native build passed17.272s. All97 native sources and515 install files independently
match their identity manifests. One C++ source change; other native source bytes
and every configured threshold remain unchanged.

Actual v26 stopped-state replay changes from failed continuation to an accepted
1.847894248m prefix, twice. The accepted curve duration is4.072214333s; all native
boundary/dynamic/minimum-cruise/full-curve gates pass. Independent SciPy six-boundary
PVA residual is6.19e-15; repeated accepted controls and knots are identical.
Earlier3.713m target shortcuts still fail optimization and are not accepted;
only the subsequent shorter native proposal passes.

All11 complete manager continuation replays pass, including nine old successes.
Eight complete unmapped fixture JSON outputs exactly match v24. Five mapped
structure fixture JSON outputs also match v24; this does not resolve the user's
pending known-low-protrusion semantics choice. Ground/body support contracts and
no-progress/out-of-map/stale rejection controls pass.

Real blocked-direct manager control: both v23 replays have free endpoints but
blocked direct segments. Their62/62/30-vertex seeds retain full original v24
seed payloads exactly and never take the shortcut. The original1.484612571m
continuation still passes. See independent_review.json and analyze_regression.py.

These are component outcomes. Complete-floor physics, eventual PD hold and the
separate emergency-hold/scheduling questions are not accepted by these tests.

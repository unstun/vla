# v192: shared applied-state harness over the qualified native v191 overlay

Stage: experiment + analysis. Parent: v191. Authorized scope: remove the
remaining synchronous 100 ms applied-state ZMQ lockstep and execute one full
Mac Building attempt. The unchanged ROS 2 source and compiled overlay retain
native_version=v191; the integration harness is v192. No native rebuild.

The episode writes current_command.json atomically through its existing ordered
asynchronous evidence writer. Both host and Docker read the same trial bind
mount, with no tmpfs shadow, applied receiver, ACK, or port 24603. The finish
request is read directly from that shared directory. Driver observation accepts
snapshots up to 10 seconds old and waits 15 seconds in the navigation loop to
tolerate transient VirtioFS visibility delays. Command watchdogs, native
freshness, geometry, policy, startup, route and terminal tolerances are unchanged.

Closed-state verification compares the host and container file hashes after
the producer and graph stop. Analysis rechecks these against the retained raw
files. This is a shared-file closure witness, not an ACK/copyback claim or proof
of per-step delivery. Failure or missing state remains a recorded failure.

Qualification order: host tests; real Docker overlay/lifecycle graph preflight;
protected-path hash comparison; qualify_mac.py; freeze_host.py freeze and verify.
Protected paths are v189/v190/v191 and recovery_v176/recovery_v189/recovery_v191.
The sole authorized v191 edit removes its trailing forward reference to a
nonexistent v192 display package; its original bytes are saved in evidence.
All v192 src bytes must equal v191 and the existing native source inventory.

Run run_mac_full.py --task-root /private/tmp/vla_stop_audit_20261012 --attempt 1,
then close_mac_trial.py for v192_mac_full_attempt01. Report route completion,
simulation/wall time, RTF, path, final pose/hold, command stops and measured
low-speed intervals. Compare with v189's 20 replacement stops / 34.225422 seconds
of cancel-to-proof waiting, without equating removed P2B proofs to physical
stillness or claiming reliability from one attempt. Preserve failed captures.

Only a full recorded route (route_arrived=true and FINISHED) permits the v193
display package, following v190's complete causal recorded-state replay with
zero physics steps. Deliver the regular MP4 at
v193/delivered/v192_mac_full_attempt01.mp4, verify full decode, frame causality
and representative visual frames, freeze v193, then archive to
gpu5070ti:/data/sun/vla_mppi_20261009/mac_archive_v192_20261014/.
Temporary Mac raw captures stay under the authorized /private/tmp task root;
the local repository retains source, compact evidence, reports and the review
video (expected below 100 MB). Heavy raw/render evidence is archived remotely
with member and archive SHA-256 verification before any cleanup.

No changes to frozen predecessors, native overlays, upstream projects, training,
or real-robot actuation. A failed frozen v192 run is not edited or retried under
the same attempt. Component/graph qualification is distinct from route results.

# Inline review of the v133 failure repair

Stage: experiment + analysis. Review performed inline; no delegated agent.

The exact installed v137 optimizer/planner hashes match the local source used
for v139. Native export construction checks each parent hash, and host freezing
checks source/snapshot pairs and 618 runtime inputs. The baseline is native v137,
the candidate is native v139 build02, and both use identical v135 global-map
bytes and the original v134 local static coverage. Rejected v138 is excluded.

## Safety and state flow

The nearby witness only creates optimizer constraints. It cannot mark occupancy
free, change ground heights, refresh timestamps, publish a command or release
an owner. The final controller-heading trajectory checker remains authoritative.
Endpoint control slots remain fixed. Cubic basis weighting applies to uniform
cubic curves produced by the existing boundary fit/refit, using the actual knot
interval. Post-refinement retries preserve original initial PVA and execution
epoch; their publication lease is local to each attempt and released on retry.
The existing boundary/dynamics/minimum-cruise checks run again before publication.
No scene-specific coordinates appear in production feedback code.

At most two additional complete feedback attempts are added after refinement;
the original optimizer restart bound, mission startup deadline and six-retry
limit remain. This can increase tail latency and is not a 30 Hz speed fix.
Finite sampled collision checks do not prove a continuous rotating-footprint
sweep. A missing free witness or collision affecting only fixed controls fails
closed. This is a scenario repair, not sensor-only unseen-gap detection.

## Direct validation

- Native build: 14 packages; 38 original tests pass.
- Seven bounded-hint checks cover mutable-control hints, fixed endpoints, no
  immediate curve mutation, clear query, no free witness and invalid arguments.
- Same 346 original sensor scans and measured torso state: v137 rejects the
  captured start/goal case; v139 build02 accepts and rechecks 567 full-curve
  samples, endpoint PVA and dynamics. Reconstruction and input digests match.
- Host physics/config identity tests, actual 10 s native graph startup and
  output ownership/writer checks pass. Initial copied-file execution permission
  error is preserved and corrected before freezing.
- Local Python syntax parsing and frozen-source verification pass.
- Three fixed independent v139 pilots arrive with measured final PD hold and
  no falls. A disconnected runner output caused BrokenPipeError after all three
  outcomes were saved; original record is preserved and a separate gate verifies
  their hashes. No pilot is rerun or replaced.

The three pilots are a separate denominator from the six fresh runs per arm.
The fixed six-fresh-runs-per-arm comparison is complete: v1375/6, v1396/6,
no falls. All11new replacement proofs pass. Local return verifies569files and
qualification hashes;30new raw trials are reverified remotely. The declared
scenario gate passes. Main physical30Hz, general navigation and Jetson/robot
acceptance remain outside this gate; fresh candidate max round706.406ms. Do not commit unrelated dirty/staged paths
or remove the pre-existing Git index lock.

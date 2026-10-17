# Recorded twist frame correction

The old extractor saved base_linear_velocity_world and angular_velocity_world,
but the replay publisher placed them unchanged in Odometry twist with
child_frame_id=base. SCAN's existing body callback rotates that twist to world,
so the recorded world velocity was rotated a second time. The live complete
body-state bridge correctly uses directly measured body twist and is unaffected.

New extraction retains both world and body fields from the same physics row.
The publisher prefers direct body fields and records the contract/version and
source counts. Legacy inputs can explicitly be converted from their known world
fields using inverse quaternion rotation; the paired acceptance below uses all
275 direct recorded body twists, with zero reconstructed events. Five writer
tests cover identity, yaw/roll quarter-turns, invalid data and direct-field use.

prepare_paired_inputs.py augments the original .30-height input without changing
existing event fields or any nonbody event. The cloud and planner byte hashes
stay identical. Maximum independently checked R(q)*v_body minus v_world error
is2.47e-8 m/s and1.92e-7 rad/s for angular velocity. The new manifest hash is
1a5e87dc39c8d0a2558590eb637b1ba2ef86467dda2641f6ffc084aeadce4652.

In independent network-isolated Foxy containers, scan27 still has75 accepted
seed chains and zero moving splines; scan28 has one accepted moving spline.
Counts are callback outcomes, not a performance comparison. The received scan28
curve preserves the recorded world start velocity within5.04e-11 m/s, the input
start acceleration zero, and the original zero terminal PVA derivatives.

Historical geometric/yaw comparisons remain facts about their exact recorded
curves, and source/unit/tracker results are unaffected. Historical ROS replays
must not be labelled as exact measured-world velocity continuity. Their source
and inputs remain preserved; they are not silently rewritten.

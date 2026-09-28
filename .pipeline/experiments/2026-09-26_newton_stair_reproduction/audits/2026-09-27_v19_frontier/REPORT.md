# v19 recorded stopping-state audit

The 30.000141144 s input contains 189 original paired scans and the actual body
message, plus the latest captured emergency spline and original global route.
Ground bytes match the actual v19 publisher. The probe executes the production
GEN_NEW_TRAJ start-state function and complete rebound planner. Original result:
no valid local target and no continuation; query support and prior nonterrain
history reject the candidate. Sensor provenance shows zero robot returns in all
341 episode scans; self-returns do not explain this run.

An offline counterfactual retains all original 2M PCD points and appends 8M
area-weighted samples from the same static mesh using pinned Trimesh 5.1.0.
The unchanged original CPU PCT generator produces 96705 selected points and ten
retained slices. This changes selection and elevation together; it is not a
safe superset. It extends the visible route frontier but still cannot produce
a complete accepted curve. It is not adopted in production.

The first start_occupied comparison was confounded by different target-derived
yaws. The fixed-yaw check corrects the interpretation: both maps return the same
values at the actual position for body yaw (-1.994691), -pi/2, the old failed
candidate yaw (2.54264767), and dense target yaw (-1.57547993): [1,0,1,0].
Do not claim the denser input alone cleared the actual start.

Exact endpoint inspection finds recorded tread returns whose own map cell has
no selected lower-floor support (only surfaces above 4 m). Examples near
[-5.697,3.550,0.467279] fall in selected cell [15,118], while adjacent selected
cells contain the correct 0.467279 m tread. They enter nonterrain history and
then inflate into the robot query. This demonstrates coupling of navigation
cost selection and raw-ground recognition. It does not authorize widening the
navigation support set: the earlier mapped low-box counterexample remains.

The next diagnostic keeps the original navigation support and changes only
raw ground recognition: ../2026-09-27_split_ground. No v20 is assigned yet.

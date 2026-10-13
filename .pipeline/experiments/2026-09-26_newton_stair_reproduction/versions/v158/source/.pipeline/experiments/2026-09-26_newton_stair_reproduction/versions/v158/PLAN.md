# v158 bounded steering-prefix feasibility probe

Stage: experiment + analysis. Native parent v151 and unchanged controller.
v157finds checked graph edges but its reversing seed fails full native spline
optimization; it is not a recovery fix and will not receive physical trials.
Before another native change, test a one-resolution forward prefix that gently
aligns with a longer clear corridor. At most five headings around measured yaw
(0,+/-5.625,+/-11.25degrees), unchanged gap/occupancy checks at the start rotation,
entire edge and stopped endpoint. Rank by the checked forward corridor, then
call the actual original manager with zero stopped PVA and require all original
optimization/PVA/dynamic/final checks. These are candidate-generation hints,
not permission to execute. No fixed-yaw lateral controller or safety relaxation.
If no actual accepted curve exists, park this proposal before implementation.


The unchanged native manager admits the selected5cm/0.600503s curve with all
306final samples, PVA, dynamics and unchanged minimum-cruise ramp exemptions.
Implementation now adds this bounded proposal only after normal reference
planning fails inGEN_NEW_TRAJ, with measured/start speed below the existing
0.1m/s rest threshold and fresh current heading/inputs. At most five headings;
one accepted prefix per owner generation. Original start PVA/epoch are retained.
Do not advance reference progress or cache a feasible reference window for an
off-reference endpoint. Keep the original publisher, controller and Nav2 owner/
stop gates. Physical acceptance remains required after native guard regression.

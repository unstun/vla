# v161: gpu5070ti execution port of v160

Stage: experiment and analysis. Local repository is the source of truth.
All646native source files must exactly equal the selected Macv160export.
Rebuild14packages on LinuxAMD64 from pinned147export plus six locally
frozen changed files. No ARM install or receipt reuse. No planner adjustment.

Sync gate: every manifest source/snapshot and618runtime inputs verified; native
source/export/install and Linuximage receipt rechecked before physical execution.
Preflight each trial requires20GiBavailable memory, noGPUcompute processes,
free owned ports and10GiBdisk. CPUphysics, one run at a time; never terminate
unrelated jobs. No physics until local original-route gate passes.

Run five closed, independent original-start full Building trials. Record all
attempts, never discard failed ones or pool Mac results with Linux. Require
originalgoal/XYZ/yaw and actualzero start, continuousstate, nofall, measured
stopowner handoff and finalPDhold, copyback and rawretention. Analyze failures
before claiming repair. Raw stays on5070ti; return compactmetrics, provenance
and reviewvideo to local repository. Missing/incomplete trials are unqualified.

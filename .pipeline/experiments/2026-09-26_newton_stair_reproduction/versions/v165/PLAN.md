# v165: Linux port of the v164 recovery candidate

Stage: experiment and analysis. The local repository remains the source of truth.
Rebuild all 14 packages from the verified v161 Linux export plus six local changes.
All 647 resulting native source files must equal the Mac v164 source export.
The controller, planner, gateway and BT plugins are rebuilt for Linux AMD64.

Before each physical trial, wait up to 120 seconds for the original ports to
become available, then require at least 20 GiB available RAM, no GPU compute
processes and 10 GiB free disk. Do not stop other jobs. Run sequentially with
CPU physics, the original map/start/goal, frame zero, factory startup and final
PD hold. Keep every closed failure. Return reports and SHA-256 provenance;
keep heavy raw records on gpu5070ti. Mac and Linux cohorts remain separate.

Require local v164 original-route acceptance before any v165 physical run.
Then execute five independent full-route trials. A passed component test or
single arrival is not a repeated reliability result.

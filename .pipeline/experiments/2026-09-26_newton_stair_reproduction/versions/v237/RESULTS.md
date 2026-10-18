# v237: single original-route pass on gpu5070ti

**The one new original-route physical attempt passes spatial arrival, unchanged
terminal gates and measured final PD stand.** Native source/install remain v232;
v237 combines the original v233 host binding with v236's absolute100ms scanner
deadline. This does not adopt a new baseline or establish repeated reliability.
The previously accepted source/display selection remains v232/v233.

| Measurement | Actual result |
|---|---|
| Run |v237_linux_full_attempt01, one physical launch |
| Task closure |FINISHED, process exit0 |
| Physical recording end |124.22335815429688s |
| Final XY / yaw / height error |0.118992007m /0.120769248rad /0.001677322m |
| Final measured PD stand |4.377593994s,220 consecutive FIXED_STAND samples |
| Original-state continuity |5801 states, strictly increasing times; max step0.048459615m |
| LiDAR jobs / completed |1132 /1132 |
| LiDAR deadline failures |0; mean22.719534ms, max30.208718ms |
| Largest LiDAR runnable wait |0.728770ms |
|45–55s local planner rounds |296/296 successful,100% |
|45–55s low-speed pauses >=1s |0 |
| Controller crash / fall |No recorded controller crash; original route gate passes no-fall |

[Preflight](PREFLIGHT.md): exact317-source/607-installed-file checks, seven
regressions,250 original-ray/catch-up samples (max24.203205ms),1000-frame policy
golden, effective profile and real12-second graph pass before physics.
Frozen source/current snapshot hashes and the original v219 input identity
are checked independently. Policy SHA7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b,
original endpoints, ENV225,0.35m hard guards and0.1s captures are unchanged.
No native rebuild, policy change, writer workaround or shared job mutation.

## Interpretation and limits

This idle original-host trial crosses the former40901 failures at12.802s and
35.592s, traverses the staircase and reaches the original goal. The writer's
256-job bound is unchanged; its failure on40901 remains unresolved. This run
does not prove that the writer tolerates the former shared-host workload, or
that hardware migration itself repairs navigation logic. Physical early
native-check waits were not needed here; the catch-up path is exercised by the
offline regression/probe. Do not credit a cross-host speed difference to the
planning algorithm or policy.

Mean successful planning is25.591114Hz, P95 solve32.802389ms and maximum
308.107173ms;16 rounds exceed100ms. The original analyzer retains
full_qualification=false and sustained_30hz_validated=false. The original
spatial/terminal route passes, while sustained30Hz and repeated reliability
remain separate targets. Stair-window results compare completed rounds by
native start time; they do not establish success on other starts/maps.

[Full audit, measured edge margins and videos](../../audits/2026-10-17_v237_gpu5070ti_physical/RESULTS.md).
Heavy raw evidence remains on gpu5070ti under
/data/sun/vla_mppi_20261009/trials/v237_linux_full_attempt01.
Original archive330,322,822bytes /1136 members, SHA
fb4d1eab6dfaa92d3d485d8319b4cfa330003a8dd317b24cc76fbdd60f0d92f2.
Raw/build/cache data are not committed or returned. Recorded-state display
adds zero physics steps; source indices, full decode and delivery hashes are
verified separately.

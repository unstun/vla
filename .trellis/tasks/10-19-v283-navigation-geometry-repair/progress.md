# v283 implementation checkpoint

User explicitly approved final PRD/design/implementation plan and all requested
offline/physical execution. Task is in_progress. Do not ask permission again.
Main session only; no subagents. 0.35 m / 0.1 s unchanged; no scene exceptions.

## Frozen native component

Version directory is experiment `versions/v283/` (experiment root is
`.pipeline/experiments/2026-09-26_newton_stair_reproduction`).
`native_manifest.json` SHA:
`caeea41b0dbb99ca10ae74b1cf6239535d4c2c4d25327f53988d8afe7b1393f4`.
Do not edit its `source_files` or overwrite the installed native. Physical
execution wrappers are separate, not yet frozen; final `manifest.json` pending.

Native mechanisms: endpoint hint exemption in the request's 3x3-attachment
region; same hard geometry remains; retained paths checked from nearest remaining
point; static readiness polling within original 1500ms query deadline; source
solid/static support wired into actual getInflateOccupancy; warm replans use
measured PVA when either double-cylinder center differs by over half a native
map cell (including yaw) from the predicted state. No heading-expansion change.

All 171 inherited tests pass (8 PCT targets + 12 regression XML targets).
New contract: parent endpoint 0/12, candidate 12/12; parent live-free/static-wall
query permits, candidate rejects; translated/rotated measured-seed controls pass.
Logs on remote ROOT: build04.log, unit04.log, regressions04.log, contract03.log,
parent_contract02.log. Earlier failed builds/tests are preserved.

## Crucial diagnosis

`results/recorded_summary.json` returned locally. In CD12's four SupportGap
samples (37.511013..37.810848 s), the latest recorded published curve is clear,
but actual body differs by 0.32..0.36m and yaw by 0.43..0.54rad. At first witness,
curve605 is only 0.019989s old yet begins far from the body, exposing continuation
from the old theoretical state. Recorded D07/CD12/CS03 solid excursions likewise
have clear reconstructed latest curves and actual tracking displacement. This
is recorded publication reconstruction, not an exact asynchronous tracker replay.
Static-query omission is real but cannot alone explain those physical excursions.

## Updated cohort

All 50 starts checked against actual native StaticSupportField/StaticSolidField.
Eight replacements: G05, CU04, CU08, CU11, CU12, CU13, CM01, CM02.
User was explicitly informed CM02 also needs replacement under the uniform rule.
50 distinct legal spatial pairs + 3 original illegal controls retained. Goals,
headings, strata remain. All changed starts have original-mesh path certificates.
`cases_manifest.json`, `start_admission.json` are frozen and returning locally.
Construction script SHA c2efae9a368b81faafcbfdd4d55aa55a8c802f070aeb5ecd875717737b70a95b
matches the generated manifest. Eight new zero-physics LiDAR fixtures captured;
all unchanged fixtures copied with verified request identity. 0.1s deadlines pass.

## Remote and current processes

SSH gpu5070ti -> sun@23.252.106.36 port60023; ordinary sandbox denies network,
use exec_command require_escalated (user has authorized the operation).
compute-helper was not on PATH and sidecar helper absent, so use SSH/rsync.
Remote repository: `/data/sun/vla_mppi_20261009/repo`.
ROOT: `/home/sun/vla_exec/navigation_geometry_v283` (chosen for free space).
ROOT/native: isolated source/build/install; parent frozen v280 remains untouched.
ROOT/cohort: 53 fixtures and geometry-only certificates.
ROOT/benchmark: scored full matrix, currently running once only.
ROOT/matrix01.log: concise per-case progress. Native timed cases precede audits.
Python: `/home/sun/vla_exec/envs/newton_worker/bin/python`.
Pinned container: sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4.

Current exec sessions: 48946 is SSH running run_matrix.py redirected to
ROOT/matrix01.log. 4633 is allowlisted rsync of native manifest/source snapshots/
cases/test inventories back locally. Poll completion before dependent work.
Earlier 31899/17817 build sessions are complete or stale; no need to repeat.
GPU was busy with another job and available RAM ~17GiB. Physical resource gate
requires the inherited 20GiB RAM / idle GPU / 10GiB output disk. Do not kill peers.

## Remaining work

1. Monitor/finish all53 offline calls + independent audits. `run_matrix.py`
   requires >=48/50 full-chain, 3/3 illegal, nonnegative independent margins,
   median <=1.5s, firstGPMP/admitted >=90%, and all ten fixed cases admitted.
   Preserve failures. Native is frozen: do not edit/rescore it silently.
2. Complete physical wrappers. Drafts copied/adapted from v282 already present:
   launch.py, native_graph.py, newton_episode.py, navigation_physical.launch.py,
   case_binding.py, preflight.py, preflight_runner.py, resource_admission.py,
   resource_probe.py, verify_case.py, verify_profile.py. They are NOT runnable
   until new identity.py / prepare_execution.py / freeze_execution.py exist.
   They must use native_manifest.json (not old v280 identity) and ROOT/native.
   Reuse original v282 geometry metadata/fixtures (same bytes) read-only.
   launch.py changed WORK to Path('/home/sun/vla_exec/navigation_geometry_v283/native')
   and keeps geometry_physical_v282 fixture mount. Verify every generated path.
   verify_profile.py now reads v283 native_manifest for support/source hashes,
   while retaining old v280 fixture inventory and geometry_physical_v282 metadata.
3. After offline passes, copy selection/gate/scenarios locally, bind execution
   source identity, run 10 zero-step/process/profile/scanner preflights, then
   freeze final execution manifest under v283 without changing native freeze.
4. Adapt audit run_physical.py from v280-source-generalization audit for v283,
   fixed list A04,G05,CU06,D07,S04,CD12,CM02,CM07,CS03,CE03, one formal attempt each.
   Physical captures `/home/sun/vla_exec/physical_runs_v283`; evidence under
   `/data/sun/vla_mppi_20261009/generalization_v283` in draft launcher.
5. Adapt original analysis/render/collection scripts to actual v283 install and
   source identities. Reports must distinguish arrival, PD, support/solid margins,
   errors, pauses and scanner timing. Render recorded states, no new physics.
6. Return compact full report and 10 real local MP4s, verify hashes/decode/coverage,
   inspect every route. Full raw captures/builds remain remote. Run trellis-check.

No commit made. Existing dirty v242..v282 and harness edits belong to other work;
preserve them. Task branch was recorded as main; final archive would need resolving
that metadata/branch without absorbing unrelated changes. No baseline adoption.

## Later checkpoint

Physical wrappers now include identity.py, prepare_execution.py and
freeze_execution.py. They remain unfrozen and unexecuted until the offline gate.
New audit directory `audits/2026-10-19_v283_navigation_geometry` contains adapted
once-only batch/preflight/render/analysis/collection scripts. Native source is
still exactly frozen; local native hashes were verified after wrapper creation.
Full matrix most recent status: 40/53 native calls finished, CS02 underway; CS01
still rejects globally. Other shown cases publish local curves. Resources became
available (25GiB RAM, GPU idle) after the peer job ended without intervention.
Remaining SSH session 48946 runs matrix; stdout is ROOT/matrix01.log.
New audit source rsync session95402 and directory creation77086 may need polling.
Source wrapper rsync74223 may need polling (likely done).
Local snapshot return4633 completed and all30 frozen source files verified.
All native builds/units/regressions now complete. Parent contract02 confirms
local_wall_rejected=0/live_verdict=0; candidate contract03 confirms wall rejected
with the same live-free input.

## Physical tooling prepared; native evaluation complete, audits running

All53 timed native requests completed; audit phase is running2 workers. Latest
ordered audit returned CU08 (11th case); source geometry audits may take minutes.
Execution wrapper generated-source dry check passed (correct private native
root, original read-only geometry fixture mount, v283 profile verifier).
The standalone readiness test is at versions/v283/diagnostics/readiness and
run_readiness.py, deliberately outside the frozen native source manifest.
SSH session64585 runs it; log ROOT/readiness01.log. It checks delayed readiness
resumes and unavailable evidence retains the original1500ms total deadline.
New audit source is synced. Before preflights, sync any later local physical
wrapper edits, call prepare_execution.py only after offline_gate.passed, then
run audit/run_preflights.py with the private Newton Python. Final execution
freeze uses freeze_execution.py after all10 preflight_passed receipts.
Draft launch metadata descriptions now correctly identify nativev283.
Audit summarize_physical.py now uses v283/native_manifest.json for native hash.
Audit postprocess_case.py mounts ROOT/native instead of the old native root;
physical_support_margins.py likewise uses the current install. Review runtime
seams before actual use; these adapted tools have not run yet.

## Current native-only totals

All53 native calls completed. Preliminary49/50 global admissions and49 local
publications; onlyCS01 has pct_no_route. CPU2 admitted median1.301129233s. These
are NOT the final independent-audit gate. Last audit progress aroundCD04; no
reported audit process failures. Session48946 still owns matrix/audits.
Standalone readiness test passed: delayed readiness resumes in0.030475s;
permanently missing evidence times out1.50008s (original1500ms request budget).
Compact build/unit/regression/contract/readiness logs returned locally to
v283/results; component_review.json binds their hashes.
Native source snapshot still verified unchanged. Pure adapted-launcher AST
checks passed for WORK root/fixture mount/profile verifier.

## OFFLINE GATE PASSED — physical preflights now running

All53 native calls and all53 independent audit jobs completed successfully.
Final gate:49/50 full-chain legal passes (98%);3/3 illegal controls refused;
firstGPMP47/50 or47/49 admitted; CPU2 global median1.301129233s, p951.803866708s,
max1.956207846s. No admitted global/published local negative independent margin.
CS01 is the retained no-route failure. All ten fixed physical cases admitted.

Session48946 finished exit0. Session31258 is compact offline results rsync to
new audit/offline/ (all per-case summaries/audits/metrics, full gate/table/ledger).
Session23521 executes prepare_execution.py then run_preflights.py with the
private Newton Python. Log ROOT/preflights01.log. It is zero physics only.
Next: inspect/fix unfrozen physical wrapper problems if any; complete ten
preflights; freeze_execution.py; return final manifest/source identity/scenarios
locally and verify; then run the ten-once physical batch. Do not modify native
manifest/source or rerun the scored cohort. Native freeze is unchanged.

## RESOURCE WAIT — no physics yet

Execution identity prepared (SHA a852d34c4d513b1a5479e5f54dbc66daf2e9b64c56f42d8ebb28c1c72719421c)
and returned locally with selection/fixture_binding/scenarios. Offline compact
return completed. OFFLINE_RESULTS.md written locally with full denominators and
changed-cohort comparison boundary.
Preflight23521 is still running but waiting at A04 resource admission. A new
IsaacLab peer PID1347950 occupies~11612MiB GPU and ~30.5%RAM; available RAM
~18.2GiB below unchanged20GiB gate. Its elapsed time was13:19 at inspection.
Do not stop/modify it or lower gate. User has been informed and automatic wait
continues. No physical attempt or zero-step graph preflight has begun.
Status JSON: newaudit/results/preflight_batch_status.json. Check this and
ROOT/preflights01.log. When gate clears the existing process automatically
continues all10 preflights; inspect failures if any.

## Execution frozen and physical batch launched

All ten zero-physics preflights passed on invocation01. All58 execution/native
source entries and snapshots plus ten receipt hashes have returned locally and
match. Execution manifest SHA8d22f7e0ebeb90432b6811462d95dd175613bb3e4902d5b4634fe6b0ca38cc71.
The fixed ten-once physical batch is now launched; ROOT/physical01.log and
newaudit/results/physical_batch_status.json record progress. An owned resource
observer records overlap once per minute and stops after batch completion.
No native or execution source changes are allowed after this freeze.

## 2026-10-19 lossless disk recovery; frozen batch waiting

The first dispatcher wrote formal-launch ledgers before validating the episode.
A04/G05/CU06/D07/S04 then each exited at the inherited disk check before
simulator construction/import/stepping (six entry files only; exact traceback
at executed_trial_entry.py:128; process exit1 after about0.03s). Original batch
status falsely inferred a formal start from the early ledger; it is preserved
unchanged beside an explicit evidence-based reclassification. These are five
zero-physics launch rejections, not five physical attempts. All original task
folders and execution receipts were moved without byte changes to remote
launch_failures01 / execution_launch_failure01. Compact copies, inventories
and original launch logs have returned to the audit results/recovery directory.

37 files /5,288,964,998bytes from the inactive mac_archive_20261012 were copied
to /home/sun/vla_exec/relocated_archives/mac_archive_20261012; source and target
SHA/modes were checked before freeing the redundant original. The old absolute
path is a symlink. /data free rose from10,550,161,408 to15,839,219,712bytes.
Inventory and relocation receipt are local. No frozen source or gate changed.

New owned coordinator PID1367138 runs audit/execute_batch.py detached, logs
ROOT/physical02.log, with resource observer PID1367149 and dispatcher1367150.
Both frozen manifest hashes and full inherited source identity passed. Waiting
at A04 because peer IsaacLab PID1366414 uses10208MiB GPU and available RAM
is~19GB (<20GiB gate). No real physics has begun as of this checkpoint. The
existing process will continue when resources clear. Do not start another batch.

Unfrozen analysis tooling now runs the physical support audit after each video,
retains numbered failed-analysis logs/render attempts, and collects typed
endpoint/readiness rejection lines. Native/execution frozen files remain intact.

## Seven physical routes closed; original batch still active

After transient chat interruptions, the owned detached coordinator remains
active with no duplicated dispatch. A04/G05/CU06/D07/S04/CD12/CM02 are closed,
all process exit0 (process success is not navigation acceptance). CM07 is now
running. D07/S04/CD12 result.json says FINISHED with measured PD; A04/G05/CU06/
CM02 says FAILED. Their full support/solid audits are still pending.

A04 has one typed endpoint rejection: start at(8.5738249,-2.5569251,2.0021091),
yaw0.73307, support10=WrongHeight, solid0,repair0,live_hint0. It has14feedback
updates. G05/CU06/CM02 have no endpoint-pose rejection lines and12feedback
updates each. Do not call A04 a live-hint mis-abort or infer geometry clearance
for any arrived route. Direct result durations: A04210.723s,G05193.502s,
CU06203.814s,D07278.701s,S0448.905s,CD12308.248s,CM02160.047s.

Owned after_physics.py PID1374537 waits for all ten closed cases, then runs
postprocess_all.py and collect_physical.py with zero new physics. Log ROOT/
analysis01.log and receipt ROOT/after_physics01.json. All raw/source gates remain
frozen. Independent analysis tooling is synced and captures all PCT failure
lines, endpoint/readiness attribution, support/solid/raw margins, and videos.
Do not start another physical or analysis coordinator.

## All ten physical attempts closed; analysis/rendering active

The unchanged frozen dispatcher finished all ten, one actual attempt per route.
All process exits0; result.json navigation outcomes are FINISHED for D07/S04/
CD12/CM07/CE03 and FAILED for A04/G05/CU06/CM02/CS03. CM07 and CE03 each have
one pct_native_traversability_timeout line yet subsequently finish. CS03 also
has that timeout and fails. Do not conflate a planner action failure with the
final task result, or a successful process with arrival.

After_physics01.json is now stage recorded_state_analysis, physical_attempts10.
First A04 numerical audit:1959/1969 navigation support samplesFree;10WrongHeight
(10), source/raw solid minima+.15m with0raw negatives. No SupportGap conclusion
for CD12 yet. A04 render01 is actively producing the entire210.723s recording.
No video delivery certificate exists yet as of this checkpoint.

Physical batch status returned locally. Current after_physics process owns
sequential numerical audit/render/support audit for all ten and final compact
collection. All raw captures remain remote. Continue inspecting analysis01.log
and per-case /data/.../v283_CASE_analysisNN.log; repair only unfrozen tooling if
needed, never repeat physics or edit frozen v283. Final report generator is
prepared locally but requires returned evidence and honest visual_review.json
after inspecting two frames from every actual local MP4.

## Six videos verified; critical physical result and command-owner gap

A04,G05,CU06,D07,S04,CD12 numerical/render/support pipelines passed tooling
checks (not all physical acceptance). Six real MP4s are already local. A04/G05/
CU06/D07/S04 two-frame visual inspections are recorded; CD12 still needs local
visual inspection. Remaining CM02/CM07/CS03/CE03 are held by the original GPU
gate while peer IsaacLab PID1433472 runs (~4668MiB GPU at inspection). Do not
kill it or duplicate postprocess_all. Existing coordinator will continue.

Actual geometry so far: A0410WrongHeight samples;G052WrongHeight;CU062WrongHeight,
all with positive source/raw solid margins. D07 arrives but source solid minimum
-0.002731725m (raw+.000241357). S04 arrives but has new source/raw regression
-0.130589169/-0.128263878m. CD12 arrives with2927/2927supportFree and source/raw
minima+.015583396/+.017665336m: no SupportGap. Final hard-gap margins are in
physical_support_summary and will be returned by the owned collector.

Additional recorded reconstruction (zero physics) is local under audit/results/
candidate_recording. D07 at270.462830s has nominal published-curve position error
.0078985m/yaw error1.629964rad; applied command[0,0,+1]. S04 at37.610958s has
.312647m nominal endpoint position error, applied command[0,0,-1]; at first
negative sample36.511562s command0 but speed~.423m/s in STAND_SETTLING. Complete
inspected curves are source/support-clear. These are nominal published-time
reconstructions: tracker internal phase freezes in yaw branches, so do NOT claim
exact internal-phase replay or actual expiry just from the nominal end time.

Direct source read/hash checks: TrackingNode::cmdCallback emits terminal or
in-place yaw via publishStop(yaw_rate) before phase advance. sampleCommand calls
this; LocalMotion::command validates finite twist but no measured-body swept yaw
query. This existing command-owner gap is not repaired by the new local geometry
query/measured warm seed. Both D07/S04 negative actual envelopes remain failures
under unchanged0.35m; no tolerance waiver. Focused spec updated with this limit.

All10 post-physics source/install hashes passed identity.verify_sources and the
receipt is local. Physical resource history has38observations, no sampled GPU
overlap/gate failure, minRAM25044774912bytes/minoutput46489845760bytes; not an
exclusive-host or continuous guarantee. Actual terminal bill returned locally:
G05FailedToMakeProgress;CU06/CM02NoExecutableSCANtimeout;CS03progress +
terminal_settle_timeout. Solver-1008 appears on successful routes too; do not
treat it alone as the terminal cause.

Finish remaining four analyses/videos when resources clear, return physical_return
and MP4allowlist, run summarize_physical.py, inspect all ten local frame pairs,
then write_report.py (requires visual_review alltrue). Report AC6 as FAILED and
preserve the S04 regression. No frozen candidate changes or physical retries.

## Zero-physics rendering resource separation and resume

The inherited physical gate was unintentionally also used by postprocess_all,
causing a needless wait after6videos while new peer1436152 used11612MiB GPU.
Physical execution was already fully closed. Kept all frozen physical source/
gates unchanged and separated recorded-state resource admission:8GiB available
RAM,2GiB freeGPU,10GiB disk; nice10 per-case processing. This applies only after
all10physical rows are closed and creates0physics. The source case renderer and
all numerical geometry remain identical. User was informed before this change.

Verified no active case writer; stopped only owned waiting dispatcher1422025,
preserving original first6status/logs and render_dispatch_transition.json.
Original after_physics01 correctly terminates on that owned signal; its receipt/
log stay intact. New after_physics02 PID1437647 resumes original closed cases,
skips6verified videos, and will collect all10. Log ROOT/analysis02.log. Do not
start another coordinator. render_resource_observations.jsonl records capacity
and foreignGPU use; first shared probe RAM19382550528bytes/freeGPU3976MiB.

CM02 numerical audit is now complete:1465/1465supportFree, source/raw minima+.15m.
Its first video render is active. Five prior visual reviews plus CD12 have been
recorded (6cases total) in results/visual_review.json; all_reviewed staysfalse
until remaining4actual MP4s are opened/inspected.

## Final v283 delivery — physical acceptance remains failed

All ten local final MP4s total171510095bytes; primary compact bundle465files/
20481372bytes. Every transfer hash, stream/full-decode/source-coverage check and
local visual review passes. CM07 camera03 fixes pillar occlusion/full-leg framing
from the same physical recording; earlier camera masters/source/visual failure
are retained. Numerical case fields are identical before/after display changes.

Full report, video index, all50old/new start CSV, physical CSV/JSON, final check
and source/provenance receipts are local. Final_verification verifies58frozen
files/snapshots,30native files,10preflights,66Python files,10unique actual epochs,
all14881scanner jobs completed at0.1s with0deadline misses. Physical outcome is
5/10goal+PD,2/10goal+PD+geometry(CD12/CM07). D07/S04/CE03solid negatives and
14WrongHeight samples remain. CD12 has0SupportGap, gap minimum+.114431m and
solid+.015583m; G05post-PD gap+.073256m. No frozen code/threshold/scene exception.

No owned physical or rendering job remains required. Preserve all raw data on
gpu5070ti, selected baselinev232/v233, and task in_progress because AC6fails.
Do not silently edit v283, retry a route, archive the repair task or claim fixed.
No commit was made. Any later logical repair must use a new integer version.

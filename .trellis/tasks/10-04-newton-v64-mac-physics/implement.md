# Execute

## Latest failed-pilot continuation, 2026-10-10

Stage: experiment + analysis. Dr Sun authorized continued failure diagnosis,
repairs and repeated gpu5070ti runs. v133 fails after its left-front foot enters
a floor seam falsely covered by a coarse static cell. v134 supplies negative
coverage; all three pilots stop early. v135 makes global PCT respect it; 2/3
pilots arrive. v136 fixes queued mission delivery and emergency-exit target loss;
2/3 pilots arrive. v137 preserves a pending reference across transient stale
input; 2/3 pilots arrive. All failed runs remain retained.

The v137 failure then repeatedly smooths a local curve into the support veto.
v138 applies an all-heading local envelope, but all three pilots fail at the
start; reject it. v139 returns to v137 and feeds controller-heading collisions
back into rebound optimization through final refinement, preserving original
boundary PVA, execution epoch and safety gates. Its first build still fails the
captured case; the second passes with identical recorded map/sensor input.
14 packages/38 native tests, seven hint checks and host/graph/writer gates pass.
Frozen v139: 3,220 source pairs, 618 inputs. Three independent pilots finish
with measured PD hold and no falls. Original runner BrokenPipeError after the
last saved outcome is preserved; a separate hash-verified gate permits the
predeclared six-fresh-runs-per-arm comparison. It completes: v1375/6,
v1396/6arrivals, no falls, all11candidate replacement proofs pass. Thirty new
raw trials are reverified remotely;569compact files and every qualification
hash are verified locally. The declared Building scenario gate is validated;
maximum fresh candidate round706.406ms leaves broader acceptance open.

Keep the main task in_progress and broader references unchanged. No new MPPI
adaptations, real-robot actuation or training. Heavy bytes stay on5070ti;
scenario stop-proof and remote/local provenance checks now pass.
See audits/2026-10-10_v133_posture/REPORT.md under the Newton experiment.

## Authorized recovery repair, 2026-10-10

Dr Sun now authorizes diagnosing and repairing stop/recovery from the old system,
with repeated gpu5070ti validation. His follow-up asks explicitly about the
pre-MPPI version: unchanged native v114 is an additional control and the v128
repair parent, excluding all MPPI adaptations. Historical v122 results remain
labelled v122. The prior read-only repeat plan no longer restricts this new repair.

See `audits/2026-10-10_nav2_recovery/PLAN.md`. First run three unchanged v114
episodes. A real plugin callback regression must expose negative native safety
being hidden as normal zero commands until no-progress timeout; only then change
its notification to Nav2. Keep normal cancellation, goal hold and measured-stop
ownership gates. Separately inspect rejected replacement routes before claiming
the mission recovery problem solved. Freeze each logical change and retain
failed pilots; perform six fresh comparisons per arm on the final candidate.
No production acceptance, MPPI adoption, real-robot actuation or automatic commit.

Current checkpoint: v128-v133are frozen and component checked; all35physical
trials and compact returns are verified. Original v114has1/3initial arrivals and
2/6in each later control batch. v128comparison2/6versus2/6and v131comparison
1/6versus2/6(one candidate fall) fail reliability gates. v133post-search refresh
passes the original due-body regression, but its fixed pilots are2/3arrivals
with nofalls, so the next full comparison was not started. Full repair remains
unaccepted; no candidate adoption, task archive or reference promotion. Next
separate first-map readiness from tilted settling/start-geometry rejection.
See the report and return_verification.json in the recovery audit.

## Authorized repeated diagnosis, 2026-10-10

Dr Sun now requests repeated frozen v122/v127 comparisons on gpu5070ti to
distinguish original instability from adaptation3 regression. The new audit
`audits/2026-10-10_mppi_step3_repeats/PLAN.md` supersedes early stopping for this
investigation only: six fresh trials per arm in BAAB/ABBA/BAAB order, complete
all navigation outcomes, then compare captured inputs and direct stop events.
Do not edit navigation code, adopt a candidate, or start adaptations4–5.

Completed: all 12 fresh runs retained and verified. v122 has 0/6 arrivals,
five action failures and one fall; v127 has 1/6 arrivals and five action failures.
28,720 captured curves, 11,691 epochs and nine reconstructed map queries agree
between actual installs. Original instability is established; no captured-input
validator regression was found, but live scheduling/tail equivalence is not
proved. Eight of nine detailed rejection events have fresh ages: the shared
`scan_safety_evidence_stale` label also covers negative native verdicts. Next
investigate shared curve rejection and recovery; retain v122/v125 and keep
v126/v127 parked. Report: `audits/2026-10-10_mppi_step3_repeats/REPORT.md`.

## MPPI adaptation 3, 2026-10-10

Dr Sun keeps step 2 parked and authorizes step 3 from native v122 / host v125.
Version v127 extracts the stateless native trajectory-validation interface;
all original retry, 3D/support/PVA/clock/owner contracts stay intact. Component
checks pass: 376 fixed-input comparisons, exact native curve/proof/snapshot
regressions and 36 plugin tests. First same-host pair: v122 arrives, v127 fails
after stale-evidence and progress recovery. Apply declared early stop and park
v127; retain v122 / host v125. No second pair or steps 4–5, no robot actuation.
See audits/2026-10-10_mppi_step3/REPORT.md.

## MPPI adaptation 2, 2026-10-10

Dr Sun authorized the next isolated change. Native v126 has one reference-path
recovery-chain owner per round; parent v122 and host parent v125 are immutable.
Actual retry-flow regressions, recorded-map trajectory parity and one same-host
pair ran on gpu5070ti. Components pass; v122 arrived, v126 failed navigation.
Apply the declared early stop: park v126, retain native v122 / host v125. No
second pair or steps 3–5; no Jetson actuation or main-task acceptance promotion.
See audits/2026-10-10_mppi_step2/REPORT.md.

## Current host and sequential MPPI adaptation, 2026-10-09

The latest user instruction moves compilation, physics and analysis to gpu5070ti.
Use the MPPI incremental PLAN and v123/v124 host plans. v122 implements diagnostic
classification only; v123 rebuilds the unchanged baseline/candidate for x86_64
Foxy; v124 repairs Linux output-parent ownership after a pre-physics failure.
Both native variants passed 36 tests remotely, the diagnostic native probe and
source-decision parity tests passed, and host/real-Docker ownership checks passed.
The final v125 baseline/candidate physical pair both reached the goal and measured
PD hold; copyback and retention passed. All 1055 candidate rounds were classified
with exact success agreement. The same-input native probe also produced identical
control points/knots/duration and preserved stale-input rejection. Step 1 is kept
as diagnostic instrumentation; no speedup or population success-rate claim.
See the MPPI incremental REPORT and hash-bound remote_results/curve_results.
Keep the main task in progress and the reference at v48.

Current execution follows the ordered four-version implementation and acceptance
checks in `audits/2026-10-05_safe_mapping_repair/PLAN.md` under the Newton
experiment. Implement/check inline; freeze after component checks, retain every
failed attempt, and report full-runtime acceptance separately. The v64 steps
below remain historical execution context.

1. Verify local Python/Newton/IPC/factory and all source/geometry/policy/map identities.
2. Copy the minimum v59 runtime files into v64, reference unchanged dependencies; add explicit host build/entry/storage scope and negative source/build gate tests.
3. Build exact v63 in the cached local ROS image; return hashes and qualify installed bytes. Derive/hash the physical input in temporary storage.
4. Freeze the v64 source/config/host launch identity without a physics-success claim; execute a bounded 90-second actual Newton Building trial, repeating the independently initialized trial if the full duration and host setup pass.
5. Analyze original captures and produce compact metrics/time-series/report, bind results to version/host/clocks and preserve failures. Recheck cleanup/source hashes. Update task/spec state; no automatic commit or broad staging.

## 2026-10-05 repair review state

v79–v82 implemented/frozen; builds and component/native/recorded tests pass.
Both independent Mac corner trials complete 89.962 s with healthy heartbeat
but FAIL continuity/30 Hz due mapper lag beyond the unchanged 250 ms scan age.
v82 remains a failed candidate; v48 reference and v49 frozen exclusion remain.
v83 actual review MP4 passes decode/visual QA. Full report, plots and remote
storage receipts are in audits/2026-10-05_safe_mapping_repair. Keep this main
task in progress for the reviewed mapper throughput/handover repair. Commit
pending: pre-existing zero-byte index.lock and other Git processes observed;
do not remove another process owner lock or stage unrelated dirty work.


## Actual native-zero review video, 2026-10-11

v141's earliest captured state was0.08s. v142 captures the actual unstepped
state at0.0s before the unchanged factory initializer; nativev139 navigation
stays pinned. One bounded gpu5070ti recording arrived without a fall and passed
applied-state copyback. All closed raw bytes/archive members verified remotely.
v143 full55.733s video passes exact-zero, all1672causal indices, full decode
and three-frame visual review. Actual MP4 and28compact/visual files returned
and hash checked. Frozen integer versions preserve earlier deliveries; no
acceptance-denominator/reference/MPPI/Jetson promotion. Main task staysin_progress.


## Original spatial start and complete route, 2026-10-12

Dr Sun clarified the original lower-floor spatial start, not clockzero.
v144first historical_full trial fails after23.126m/no fall; v145failure video
is preserved. v146same435-scan/reference/body replay through actual installed
production methods proves3prefix proposals reject and6accept a safe1.24s
translation with original PVA/dynamics/126full-curve samples. v147single bounded
proposal-depth change passes14packages/38native tests, host/writer/graph/profile
checks and is frozen3357pairs/618inputs. One fresh uninterrupted full route
arrives76.883m/118.207s, no fall, final measured PD hold/copyback pass; both
replacement proofs qualified. v148full117.967s video passes3539causal indices,
all-frame decode, clock/curve/visual QA and actual local regular-file hash.
Full-route report and RESULT.json preserve failed/pass boundaries. Main task
staysin_progress, reference/MPPI/Jetson/30Hz gates unchanged; no automatic commit
and originalindex.lock retained.


## Original full-route repeats and host incident, 2026-10-12

Stage: experiment + analysis, unchanged frozen v147/v148 on gpu5070ti. The
pre-reboot six-trial cohort has three closed navigation failures, one raw
FINISHED result without copyback/retention, and two unstarted trials. The
separate post-reboot cohort has one qualified arrival and one failure; attempts
10–13 remain unstarted because other GPU work appeared and resource admission
stopped the runner. Preserve both cohorts and every failure; no repeatability
acceptance, denominator replacement or main-reference promotion. All five closed
runs have remote inventory/archive/stop-proof verification and 74 compact files
returned with exact hashes. The partial attempt05 is retained without inventing
closeout metadata. See audits/2026-10-12_original_full_route_repeats/REPORT.md.

Dr Sun confirms manual reboot followed SSH losing response. Same-boot records
show continuous clock/backend computation around the power key, largest clock
gap 0.270 s; one SSH login was accepted during that interval. Last pre-power RAM
sample has 13.33 GiB available, and no matching OOM/kernel/GPU error is logged
in the inspected window. Existing Cloudflare errors also occur during successful
SSH access. Root cause is unresolved; manual shutdown is not the initiating
cause, and no sustained whole-host freeze is demonstrated in the covered trace.
10 compact incident files returned and hash verified. No service/driver change
or crash reproduction. See audits/2026-10-12_gpu5070ti_freeze/REPORT.md. Keep
main task in_progress; remaining runs require original resource admission.


## Navigation resumed; resource admission held, 2026-10-12

Dr Sun explicitly put the host-incident investigation aside. Continue navigation
work with frozenv147. A hash-bound continuation for declared attempts10–13passed
six preservation/admission guard tests on5070ti, but31checks over600seconds
admitted no launch. It has exited; no new physical trial and parent08/09unchanged.
Read-only triage of02/03/04/08/09identifies terminal missing-trajectory versus
negative-safety paths; successful08also recovered from similar stops. Installed
source checks show the A-star pool message means spatial index bounds, with no
causal conclusion from error counts. Six compact triage files returned and
SHA-verified. See original_full_route_repeats/FAILURE_TRIAGE.md and
RESUME_HOLD_RECEIPT.json. Main task staysin_progress; no acceptance promotion.


## Authorized local reproduction and repair, 2026-10-12

User now authorizes the Mac port, same original map/spatial start, latest failed
v147attempt09 reproduction, stop/recovery repair and later repeated Linux full
routes. v149host preparation uses unchanged nativev147:631source/config/license
files materialized from matching frozen local bytes,15historical export receipts
returned separately, both additional map payloads SHA-identical. All618runtime
inputs and all seven physics/inference/transport package versions match the
recorded Linux environment. Ten local host/route/zero-frame tests pass. Cached
Docker was started; a separate ARM64 Foxy dependency image is built. Native
build/tests are in progress under /private/tmp/vla_newton_v149_j338wipj. No
physical Mac trial, recovered failure or fix is claimed yet. Freeze before
physical execution; preserve v147/v148 and Linux cohort08–13unchanged.


## v149 physical baseline and v150 diagnostic checkpoint

v149 is frozen with3396source/snapshot pairs and618inputs;14ARM64 packages and
38native tests,10host tests,15-second real graph smoke pass. Three original-start
Mac attempts retained:01sensor deadline before first scan publication;02actual
navigation FAILED after28.406m/no fall, RTF0.985, copyback/retention verified;
03runs about69.906navigation seconds then applied-state ACK times out at3497,
with copyback mismatch against last confirmed3496. No accepted local full route
or reproduction of the exact Linux failure claimed. All raw under the owned
/private/tmp/vla_newton_v149_j338wipj root; original frozen code remains unchanged.

Read-only v150diagnostic preparation/build complete, not yet frozen. Latest Linux
attempt09curve2366has clear/blocked decisions25msapart at unchanged map1191 and
observation104.474s. Original data return285575000bytes verified.935published
scans reconstructed; mapper reported931(apparent startup difference, disclosed).
Both selected body observer stamps equal the recorded safety check stamps.
Native four-way curve/body/time probe running with unchangedv147libraries.
Need inspect V150_QUERY output and require original clear-to-blocked behavior
before causal/fix claims. Source preparation's first count assertion failure
is retained; no navigation gate changed.


## v150 mechanism and v151 candidate, 2026-10-12

v150frozen diagnostic reproduces original curve2366clear atbegin0 and rejection
atbegin0.024986267with unchanged map. Earlier-body counterfactual still rejects;
later-clock/body full-interval counterfactual passes. Native check sample-grid
movement misses a narrow support-clearance region on the initial grid.
935published/931mapped discrepancy retained; not a full historical map restore.

v151candidate preserves every old sample and adds four interior checks per
interval, preserving original predicates and fail-closed maximum sample budget.
Compiled7-case exact sample-superset regression, narrow-region/budget/invalid-time
checks pass. On the original reconstructed fixture the new checker rejects the
previously accepted bad curve before motion and retains all negative cases.
Single changed native header,14packages/38original native tests and10host tests
pass. Actual candidate graph preflight running. v151not frozen or physically
validated yet; no recovery-fix claim until real original-route runs.


## Continued local diagnosis, 2026-10-12

v151frozen; attempt01navigationFAILED33.803m/no fall, copyback/retentionpass.
Attempt02infrastructureACKtimeoutatsequence1437(lastconfirmed1436), returned
server log shows serveraccepted1437; mismatch remains unqualified. Attempt03
currently running with read-only cgroup scheduling observation. No local arrival.
v152actual cold native manager finds safe replacement under v147/v151; candidate
FSM original generation7reference also finds a valid replacement. Fixed-clock
replay188ms is not live recovery. Source audit corrects verdict6toUnknownObstacle,
not support-clearance. v151checker samples also feed warm-seed density, so the
change is not initialization-invariant. Preserve all failures and integer versions.
Remote resource check1791805673:16.243GiBavailable, two unrelated GPUevaluations;
not admitted under original20GiB/noGPUcompute gate. No new remote physical run.


## Interrupted local workspace recovery, 2026-10-12 17:00UTC

Old owned temporary root is now absent; cause not established. Raw Mac captures
and native installs were not remotely archived before interruption and are
unavailable. Retain existing compact results but explicitly retract complete
raw-retention claims for this cohort; no local full-route acceptance. Linux
failure09remains the authoritative replay input. v152cold replacement diagnostic
frozen3446pairs. v153transport has18Mac/8Foxytests and real graph pass; frozen3474
pairs, but attempt01failed before physics because quality omitted the launcher
package-count field. v154prepares metadata repair and rebuild receipt; v155is an
unbuilt draft of warm-seed/safety-count separation, not an executed candidate.
New owned root/private/tmp/vla_newton_v149_recovery_20261012; each new trial must
archive immediately to5070ti before subsequent long work. Task remains in_progress.


## v154 closed failure and v157 candidate checkpoint

Newv154trial01FAILED36.197m/no fall,102.655native seconds,RTF0.997365; final
23.387s low-speed pause at[7.04303169,6.46533394,3.3614]. No transport retries.
All291physical files archived/verified to5070ti,316231680-byte tar SHA557cd3e...
(seev154results/archive_receipt). Rebuilt environment also remotely verified.
v156diagnostic frozen3518pairs: support-gap mask rejects nominal start yaw;
ordinary8grid and8knight edges all fail, but5–20cm continuous directions pass.
The prior ground-inflation idea is not supported and no mask relaxation is made.
v157native parentv151/hostv154adds body-aligned retry only after first search
expands only its isolated start, sharing the original200ms deadline; preserves
normal successful searches and all world-space edges/final gates. Only dyn_a_star
header/source change. New native workspace recovery_v157building; coordinate
regression and captured full-manager probe still due before freeze/physics.
v155unbuilt/unfrozen draft remains parked. Remote was idle26.87GiBavailable at
17:01UTC; do not run remote physics before local repair qualification.


## v157 parked; v158 full-native steering prefix, current checkpoint

v157frozen3557sourcepairs with quality.passed=false.14packages/38tests,
88coordinate and18host cases pass, but the actual original-map FSM fails all
6reference-prefix proposals. Checked graph seeds reverse direction and spline
optimization rejects. No physical run; do not selectv157as parent.

v158direct nativev151probe on the samev156fixture admits a5cm/0.600503s steering
curve,306full-curve samples, original PVA/dynamics/minimum-cruise ramp check.
Angles0,+/-5.625,+/-11.25degrees around measured heading, start yaw sweep and
full straight-edge/stopped-endpoint checks. Preferred checked corridor0.2m.
Newv158implementation derives nativev151and hostv154; only scan_replan_fsm.h/cpp
change. After ordinary reference attempts fail inGEN_NEW_TRAJ, require fresh
body/map, measured and immutable start speed<0.1m/s, start within half a cell
of measured body; at most5proposals, one accepted prefix per owner generation.
The original manager/publisher/controller still own every numerical and safety
gate. Off-reference endpoint never advances reference progress or warm hint.

Nativev158building under/private/tmp/vla_newton_v149_recovery_20261012/recovery_v158
with log evidence/v158_native_build.log (unifiedexec5779).18host tests pass.
Before freeze: require build38tests, compile CMake in a NEWreplay_v158_contract_build
(directory replay_v158_build belongs to old direct probe/nativev151), run actual
contract_probe with REPLAY_INPUT=/task/replay_v156_input PREFIX_BUDGET=6; require
FULL_ROUTE_PREFIX_VALIDATED and V158_GUARDS_PASS. This restoresGEN_NEW_TRJ stage
and checks once-per-owner, moving/wrong-state/missing-heading/missing-scan and
unchanged global progress. Then graph/receipt/freeze before physical trials.
No remote physical run started. Newclosed trials must archive immediately via
v154orv158/archive_trial.py; v154trial01and rebuilt nativev151environment already
verified remotely. v155unbuilt draft remains parked.


## v159 closed; v160 goal hold capture

v158trial01FAILED43.884m; source/291rawfiles remotely verified. v159controller
queues future TF input, uses stillfresh previous due source, preserves100ms gate.
Frozen3603pairs/618inputs;36unique controller tests/39colcon plus unchangedterrain,
18hosttests and mapped-library graphpass. v159trial01FAILED after77.078m: six
mid-route stops recover, but goal hold canceled at edge of yaw tolerance; by
1s measured stop proof yaw drift exceeds0.25rad.288proofs show this is not
missing evidence. Full raw archive031cb841...verified remotely. v160draft
stricter half-tolerance goalcapture and tracker deadband, samefinal acceptance.
Parent redregression currently building; no v160physicalrun yet. Taskongoing.


## v160 local closeout, v161Linuxrebuild

v160frozen3647pairs/618inputs. Parentactualpluginred;37uniquecontrollercases
(40colcon),18hosttests,actualmappedlibrarygraphpass. Goalholdrequireshalf
yawtolerance,finalGoalCheckerunchanged0.25rad/physicalproof. Mac01FAILED
35.235m(PCTno_routeafterprogresstimeout);02FINISHED77.571msensorpath,
78.699mdensepath,5replacementproofs,frame0originalspawn,finalPDhold,
XY0.165869m,yaw0.102538rad.1/2arrivalsisNOTreliability. Both291filearchives
verifiedremotely;02SHAf3da1b71585a0ff1c58145db910695fb38aa1f5ea27d1b1e7ef4bd5ef9328bcc.
v160environmentarchivealsoverified. v161native646filesequalv160,full14package
Linuxrebuildpasses42colconentries. ActualLinuxgraphpasses;hosttestsandfreeze
pendingbeforefiveoriginalfull-routeattempts. LocalrootstillT/recovery...;
noheavyrawcopiedintorepo. v155draftunbuilt;v157parked;v161notyetfrozen.


## v162closed1/5; v163local candidate running

v161frozen3704pairs but failedbeforephysics(Macrootguard); v162Linuxhostfix
frozen3745pairs,15hosttestsincludeactualsupervisorentry/reuse/childexit.
Same646native sourcefiles asv160. Fivephysicalattempts01/03/04/05/06yield
1/5accepted(03),0falls;02portpreflightfailurepreservedseparately. All61returned
analysis/provenancefiles verifiedremoteSHA. Raw292filesperrunremain5070ti.
Threefailuresat34mhavePCTno_route;06safetyrevocationsconsume6retrybudgetat64.6m.
ActualPCTreplaywith4recordedbodyposes: startcost50>20, no route; diagnostic
18cmsnapfindsroute but omittedconnector isNOTvalidated.

v163nativeparentMacv160: Nav2Remember/RestoreGlobalPath BTnodesofferoriginal
PCTreferenceonly; gatewayrequires explicitpct_no_route, samegoal/mission/map,
matchingphysicallyreleasedpreviousowner andnoactiveowner/binding. Oneuse
bindpermit, nofabricatedPCTsuccess. ExistingSCANNativefrommeasuredbodymust
passallgates. Nativeoverlaybridge/plugins647sourcefiles.5colconpluginentries
(3uniquegtests),9actualPythoncallbackswithmockPCT/IO,18hosttests,15srealgraph
plusmappedBTlibrarycheckpass. Native receipt610ce43ad046c393315bd6841fec9c11b99a401150fc393f6cdace9e164c2f7c.
v163frozen3695pairs/618inputs. Localv163_mac_full_attempt01currentlyrunning
inT=/private/tmp/vla_newton_v149_recovery_20261012; unifiedexec59974runs
physicsTHENarchive_trialimmediately. Do not overlapanotherlocalfulltrial.
No v163physicalacceptanceyet. v155draftremainsparked; noWarmcountfixintroduced.


## v164 local arrival; v165 Linux cohort running

v163 Mac01 FAILED27.067m. Its new BT cache did not trigger. Recorded stop at
body[8.346364,-0.937815,2.274289] has clear current footprint but no near-forward
5cm segment;33/65 planar directions are clear. Native parent FSM replay fails.
v164 changes ONLY scan_replan_fsm.cpp:12direction proposals, full rotation sweep
<=pi/128 steps, still max5full-manager attempts, same all other guards. Actual
new-stop replay accepts0.659s/331samples; previouscorner0.601s/306samples and
all guards pass.40controller colcon, inherited5plugins/9gateway,18hosttests,
real graph/mapped-library checks pass. Native receipt f50b4d3d845cf8024112d0db217cdb652858be78dc724a80910d9ad92cb941d2.
Frozen3740pairs/618inputs. audit prepare_v163_stop.py is INCLUDED in this freeze;
do not edit that script in place. v164 Mac01 FINISHED77.654m sensor/78.845m dense,
6qualified replacement proofs, finalPDhold, XY0.142618m/yaw0.104984rad. One steering
curve has17nonzero rawcommands, but observedangle is nearold11.25degree band;
do not claim widenedoffset physicalcoverage. Raw291files/481423360bytes archived
SHA22e731e8e6d66eb1320800d28d935ee1831c841c46ec1ba802d8098d40b16b7a.

v165 Linux full14package rebuild,647sourcefiles equalMacv164.45colconentries
(40uniqueGTests),15hosttests,9gatewaycallbacktests and realgraphpass. Frozen
3789pairs/618inputs. Portpreflight nowwaits up to120s BEFORE creating an attempt,
then20GiB/noGPU admission. Five serial full-route physical trials currently run
via unifiedexec42999. Native root/data/sun/vla_mppi_20261009/recovery_v165;
results/results/v165_full_repeats; runids v165_full_candidate_attempt01..05.
NO outcomes read yet. User goal remains incomplete until checked repetitions.
Mac temp T=/private/tmp/vla_newton_v149_recovery_20261012; no local physics active.
Five old local tar DUPLICATES removed only after re-verifying remote hashes;
raw local trial directories retained, cleanup receipt under audit/results.
T approximately4.4GiB,6GiBtemporary budget. v164 environment archive still due.


## Active checkpoint: v165 failed; v166 host and v167 reverse candidates

v165 five attempts gave no accepted arrival.01/02/03/05 navigation failed;
04 advanced startup physics then EADDRINUSE before navigation. Preserve all.
Stopped replay01 current heading clear but turn swept support-gap mask; a5cm
backward curve at fixed measured heading passes native PVA/dynamics/collision.
Parent actual controller instead gives vx0 and yawrate1; regression confirmed.
v166 host-only24600-24603/24651 isolation tests18 and actual15sgraph pass;
native165 unchanged, freeze pending. v167 six native source changes add explicit
short reverse intent, full message-consumer rebuild underway; not yet accepted.
No physical simulation currently active. No change to masks, original map/start,
goal thresholds or measured-stop ownership. Task remains incomplete.


v166 nowfrozen3831pairs/618inputs. v16548returnedfiles and v1664files verified
againstremoteSHA. v164 nativeoverlay archive verified remote SHA681a3b0cd84b23421fcce857fe207a1ae1cfe4cd309ed165a1c353dded144e8c.
v167 frozen3790pairs/618inputs.14packages,47colconentries(39controller+3BTunique),
18hosttests,3capturedcases(actual reverse publication and fixed-yaw checking),
actualgraph+mappedlibs pass. Receipt20d56d59709069e489dc8f1a27c58227f97bc3e81309f043b7de6d6b661198ff.
Macfull01 active via unifiedexec70290, automaticallyarchives thenaudits outcome.
v168 draft Linuxhost166/native167 full14package build active via13180; noLinux
physicalruns authorizedbylocalgateyet (needv167 accepted). Analyzeversionlabel
corrected locally+synced. Newv167verifierincludesfinalyaw fromLinuxverifier.


v167Mac01 interrupted at48.145simseconds (no result.json), appliedACK1857arrived
at353ms afterold3x100msclientexhausted. HostlastACK1856/receiver1857 =>copyback
unqualified. No recoveryphysicalcoverage. All288files archivedSHA5a4a3a659ba63b31988331d248a3555ea44637a0d24b8571dd3a6a117c33e3c9.
v169Mac-only400msACKreceivewait x3, send100ms; originalsource2sageandallother
freshness/stopgatesunchanged. Observed350msclass oldfails/newpasses,550msretry,
absentreceiverbound and19tests/actualgraphpass. Nativev167unchanged. Frozen3829.
v169Macfull01active via37376 withautomaticarchive+audit. v168Linux14packages,
47colcon/18host/actualgraph+mappedBTpass; notfrozen, noLinuxphysicsyet. Newgateway
callbacksuiteongoing. Localv169acceptancewillgate theLinuxv168cohort.


v169full01 FAILED74.060m at129.774s, RTF.981574; communication/copybackpass,
6matchingreplacementproofs. Seventhstop exhausted the cumulative6retrybudget
atthree meters shortofgoal; distinctposes showrecoveredprogressbetweenevents.
No reversecurve observed. Raw291files427161600B archived SHA23a7e1cf92e1f2ced8c1436e571ccbf3c998f22c83ce5f18debe9a462171b3d0.
v170nativeparent167/Machost169 adapts pinnedNav2.4.7RecoveryNode commit
a947ab5656e46ae3aa1afdf95e1706a16e478974 (Apache2 source/license underaudit/upstream).
Preservechild/stopsemantics, renew6retrybudget onlyfreshTF<=100ms and>=2mfrom
allpriorcheckpoints; max256, revisits/stale/futurecannotrenew. Actualstock/new
BTtests on7recordedposes oldaborts/newcontinues;5otherguardtests pass.
FirstunfrozenbuildcaughtstringInputPortdefaultoverloadbug, source/logpreserved;
fixedthree-argumentdefault andemptyframeguard. New12BTcolcon(9unique), inherited
42controller(39unique),9gateway,19host, actualgraph/mappedBT+controllerpass.
Frozen3881pairs/618inputs,649native sourcefiles. Receipt37f1d88029ca599a940d9487b598c25fef4c232e31403008b49c323779fd8956.
v170Macfull01 active via71158 withautomaticarchive+audit. v171Linuxdraftsources
syncing via4640; nativeparentexecution168 expected==frozen170649files, newfull14
packagebuild pending. v168componentverifiedbutunfrozen/physicallyunqualified.
Fourlocaltar duplicates(v163,v164,v167,v169)removedonlyafterremote+localSHA
verification, freed1302067200B; rawlocaldirsandremoteallfilesretained.


v170Mac01 FINISHED77.683796m,157.408035s,RTF.999946,6qualifiedreplacementproofs,
XYZ/yaw/hold/copybackpass. Raw291files512010240B remoteSHA731de99c70032dba2c0a68093d5a754df00f932d13fd344abb4a143541a36859.
BUT newbudgetbranch inactive: realNewtonbaseframe=base, plugin defaultbase_link.
NoV170renewallogs. Thisarrivaldoesnotvalidatebudgetrepair. v171Linuxfull14build
54colconpass butno physicalgate, staysunfrozen/unadopted.
v172 framecontract profilegeneratesperrunBTXML withconfiguredframe, preserving
allothercode. 649nativefilesparent170,2sourcechanges(profile.py+testframe).
13BTcolcon(10unique),42inheritedcontroller,9gateway,2profile,19hosttests andactual
graphgeneratedXMLbase+mappedlibrariespass. Frozen3927pairs/618inputs. Receipt
ea43fc9fa119388246b58697bf123bcdf8a976b98bd9edbb3ee9ebf4930b29c3.
v172Macfull01 active via97994, automaticarchive+audit. At112simseconds actual
V170_RECOVERY_BUDGET_RENEW logsfreshbody posesat50.049,101.376,109.012s; traversed
newspaceafterrecovery andcontinuedpastcumulative6limit. Notyetarrived.
v173Linuxdraft source649mustmatchfrozen172, buildernativeparent171; synced and
full14build active via35450. NoLinuxphysicalruns yet. Needlocal172arrival+actual
renewal, thenhost18/gateway9/profile2/realgraph/library/framechecks, freeze and5
serialfullroute trials. Allparentmanifests/source chain synced before173freeze.
Nativev167 and170 archives uploaded, hash verification active via unifiedexec98747.
v170localtar duplicate removedafterfreshremote/localSHA; rawlocalretained.


Latest: v172 Mac01 FAILED after79.570m/173.562s despite reaching goalregion.
Budget renewal DID run fourtimes (actual logs);10replacementproofs allpass.
PCTworker then aborts exit-6 at GPMPOptimizer::SubSamplePath path.size()>1 on a
singleton nativeA*route (cell[7,99,66]); subsequentplannerRPCs fail. All292files
archivedSHA49adb91cdb99e5219889f66bb754f5eb2fd48462e3f0bd1b24a7487d3a4cf6b6,
578119680B. v173Linuxfull14build55colconpassed butno graph/physics, unqualified.
v174 draft parent172 guards<2pathpoints inOfflineElePlanner andbothGPMPmodes.
Actualoldnative recordedmap/pose abort reproduced(exit134) via74860, logunder
T/evidence/v174_parent_pct_crash.log. Newbuild first missingOSQPprefix, preserved;
fixedpinnedprefix167. Nativebuildpassed but liveworkerregression catches another
lifecyclebug: afteridenticalendpoint emptysearch, nextfullqueryreturnsno_route.
Astar::Search resetsnodeg/parents ONLY ifprevioussearch_resultnonempty; empty
successful/failedsearch canpoisonnextquery. Fresh old full control subsequently passed with649points. The initial guard-only v174 regression had not yet passed. Source still
unfrozen,3nativefileschanged, plan/testrequireworker survives+subsequentfullroute.
Needverifyfreshcontrol then fixper-queryreset aspartdegenerate-querylifecycle,
preservefailedguard-onlysource/log. Parentarchivesv167/170 hashverified (98747),
v172nativeenvironmentstill due. NoMacphysicalactive. Taskgoal still incomplete.


## Current checkpoint: v174 frozen; local run active; v175 Linux build active

The unchanged fresh PCT planner accepts649points for the original full request.
The guard-only candidate rejected the captured singleton but its next full query
failed after a start-equals-goal request. A* only reset g/f/parent state when the
previous search result was nonempty. v174 now resets on every search, retaining
all static map values. Four native source files change. Both actual optimizer
modes reject three short requests, survive, and produce a subsequent649point
full route. The old native singleton crash is reproduced (exit134, no core).

v174 native receipt: be2caf79fa20fd2311c40a7e930aa3428c657481a8281d70d5f2290241239b5e.
19host tests and the actual graph pass; mapped PCT is recovery_v174, BT is
recovery_v172, controller is recovery_v167. Frozen3977sourcepairs/618inputs.
v174_mac_full_attempt01 is running via76541 with automatic archive and audit.
v175 is an unfrozen Linux port:649source files must matchv174, full14package
build plus55colcon and actualPCT lifecycle tests active via73119. No Linux
physical cohort yet. Need local arrival/coverage, then Linux host18/gateway9/
profile2/actualgraph tests, return hashes, freeze, five serial original routes.

Local cache is about4.7GiB before current capture. Removed only fully verified
remote-backed raw caches v160Mac02 andv164Mac01 and the duplicate v172tar;
source/reports/manifests/review videos retained. Restore paths and hashes are
in audit/results/raw_cache_cleanup_v174.json. Nativev172/v174 environment tars
are uploaded via51777; hash verification still due. Nativev167/v170 archives
are already remotely verified. No real robot action or training is running.


v174 Mac01 qualified: original start/actualtime0 to original goal,77.343536m,
140.287674s,RTF0.999974, finalXY0.190564m/yaw0.116303rad, finalPDhold/copyback.
Fourmatchingstopproofs andfour actualbudgetrenewals; no reverse-mode spline.
292files465336320B archiveSHAc86c0ad67907b848666608a5452f730d7893342604ea866431ba7b199087d4b2.
Native172/174 environments now uploaded and hashverified (seeenvironment_archive).
v175 Linux source649equalsMac174, full14build55colcon/PCT2mode lifecyclepasses,
18host/9gateway/2profile/actualgraph/frame/controller+BT+PCT mappings pass.
Nine qualificationfiles returned and remoteSHAverified. Frozen source sync via
currentrsync; next action is remote freeze_host verify then run_cohort.py (five
serialfullroutes). No physicalLinuxv175 trial hasstarted yet. Preserveallfailures.


v175 is frozen4029sourcepairs/618inputs. Remote freeze verification and five
serialfullroute repetitions were dispatched via unifiedexec24089. Runids are
v175_full_candidate_attempt01..05, under/data/sun/vla_mppi_20261009/trials.
Compact closeouts go to results/v175_full_repeats; all failures count. Do not
launch another cohort or overlapping physical run. Read this active session and
remote outcome files, then return+hash-verify all outputs. Goal is incomplete
until the repetition outcomes are assessed; no result is assumed from dispatch.


## v175 cohort closed: 2/5 qualified; next diagnosis active

All five Linux episodes are closed. Attempts01/04 arrived;02 failed65.399m at
[7.510949,6.538245,4.823115],03 failed64.832m at[7.851264,6.369422,4.834992],
05 failed10.315m at[-4.723900,-3.569340,1.842005]. All replacementstopproofs qualify.
Do not claim stable or fixed. Fullcompact cohort return active via71244; final
SHA return verification remains due. No physicalsimulations nowactive.

Read-only inspect_v175_failures.py is locally saved and synced; remote diagnostic
is starting to identify missing versus incomplete short curves. A local v172
stair diagnostic already shows5cm prefixes1146/1150 ended with8–11cm targeterror,
then almost10s zeros; the generic15cm endpoint deadband accepts that error.
Applied commands did enterRL, so a hypothetical high stand-release threshold is
not supported (actual deadband0.001). This is a hypothesis for the latest Linux
failures until their native logs are read. No v176 source change has been made.
Goal remains incomplete; continue targeted diagnosis/fix then a fresh cohort.


The complete v175 cohort has55compact files returned and SHA-verified. Summary:
2/5arrivals,0falls,35qualified measured-stop handoffs. No v176 execution change.
Native failures have no first recovery curve; steering_prefix is attempted but
never accepted. Recent logs show fresh inputs during these failures, so a pure
latency explanation is insufficient. Heading lookahead is0.8s in both collision
checking and tracking; do not attribute the failures to a lookahead mismatch.

Recorded sensor reconstructions exist remotely: replay_v175_attempt02_input
(query121.610s,1104scans), replay_v175_attempt05_input(query53.872s,427scans).
The initial03collision query104.849s precedes its final stop and is retained only
as a pre-stop diagnostic. The explicit stopped variant is
replay_v175_attempt03_stopped_input(query106.823196411s,957scans),0.5s after the
first owner without a curve, nominal150ms sensor lag. All are ordered recorded
prefixes, not exact asynchronous map/DDS replays. Each identity now hashes route
as well as points/poses. Preparer source and original variant are locally saved.

run_v175_replays.py is local-authoritative and synced. Native175 isolated CPU
replays are active via unifiedexec56652, output/data/sun/vla_mppi_20261009/results/
v175_native_replays. Builds frozenv167contract_probe against actual175libraries,
then runs02,03_stopped,05 with core dumps disabled. Inspect outputs before choosing
a repair. No physical simulation is active. All native environments through174
are remotely archived and verified. User goal remains incomplete.

## v175 entry trace and v176 terminal-capture candidate

All three native stopped-pose diagnostics are closed and locally returned.
All measured final footprints are occupied, but distinguish the causes:
02/03 enter the pinned negative support mask after stop;05 has no mask veto,
but its front cylinder lacks an accepted surface support layer. Earlier broad
wording that all three were mask vetoes is incorrect.

Production SupportGapMask was compiled unchanged and evaluated on every actual
telemetry pose in all five trials.01 has no mask intrusion;04 has14brief samples.
02 first sustained intrusion105.414s, after native stop103.740s,13.3cm from the
nearest reference point;03 sustained intrusion105.494s after stop105.039s,5.7cm
from the curve. References at the compared headings remain clear. This is static
negative-mask geometry, not a reconstruction of each asynchronous live map.

05 curve361 finishes about25.76s. At25.997s actual XYerror4.9246cm lies within
the inherited15cmfinishdeadband. Nearly9s of zeros permits drift before the
owner fails. Native tracking counterfactual reproduced oldzero and candidate
2cm-tolerance inward correction(vx=-.033763,vy=-.020302);1cmerror stillstops.
v176 changes ONLY generated SCAN.finish_dist=.02. It does not claim to fix02/03.
Native profileoverlay+recordedtrackingprobe pass; actualgraph+19hostchecks are
active via97351/17759. No new physics yet. v176 is currently unfrozen. Preserve
all v175failures; continue local originalroute and assess before remote cohort.

## v176 local qualified; v177 frozen and five-trial Linux cohort dispatched

v176 Mac01 qualifies originalroute77.659312789m,142.281692505physics seconds,
RTF0.962589. Six stop handoffs qualify. FinalXY0.139395m,yaw0.116816rad,
height0.006926m,no fall,PDhold/copybackpass. Actualrunningcontroller parameter
readback0.02.295rawfiles archived and verified (478064640B), SHA
70149c556dc894f177892aeff75d8e72963956fd5f40fc153ac1267036a1b2c8.
Native176environment archived SHAec70606b38e4ad7321e1b3ad2a5bde55156424b0eef3ebd8a7f7c974a56a7b12,
underlay174. Localduplicate tarremoved;rawretained. Cacheabout5.5GiB.

v177 Linux reuses verified175binaryunderlay and rebuilds ONLY profilepackage.
All649native sourcefiles exactlyequalMac176; native recordedterminalprobe,
2profilecases,18hostchecks and actualgraph/mappedcontroller+BT+PCT pass.
55colcon tests inherited from unchanged175. Two preflight issues preserved:
first invocation omitted vendoredPYTHONPATH; immediate rerun hit old46200test
TIME_WAIT; a clean admitted rerun passed18/18. No productionport change.
v177 is frozen4079sourcepairs/618inputs. docker/lsof executablemodes copied
from175 and synced before launch. Five serial original-route Linux trials are
dispatched; inspect active unifiedexecsession returned in chat and remote
/data/sun/vla_mppi_20261009/results/v177_full_repeats. Do not overlap another
physicalcohort. Fullrepair is still unvalidated until all outcomes assessed.

## Request closeout: v1775/5; full v178 video returned

The complete five-run Linux cohort closed and qualified. Attempts01–05 have
12/4/8/3/3measured-stop recovery handoffs (30total),0falls, fulloriginalstart/
route/finalXYZyaw/PDhold/copyback acceptance. Sensorpath lengths76.846/76.946/
77.097/76.871/76.910m; RTF~0.99999. All55compact returnfilesSHAverified locally.
Heavy raw runs remain remotely with293files per trial and per-file manifests.
See versions/v177/RESULTS.md and results/cohort_summary.json. SingleMacv176pass
is separate. No process or physicalcohort remains active.

The declared original-map repetition request is complete, with limits explicit:
longest low-speedpause10.694s, planningmax497.846ms, no30Hz/smoothness/Jetson or
general-recovery claim. The old occupied-pose replays remain blocked; the
post-revocation drift class is documented, not claimed causally eliminated.
Optional lower-controller per-leg latch is a read-only parked lead only.

v178 full first-trial video is returned as a regular local file:
versions/v178/delivered/v177_full_route_attempt01.mp4.162.366667s/4871frames/
19986833B; SHA2315e907b8e3c28e72733d69bfce64737b32b63e0a24594e641af8c333877854.
Nativeframe0, full startup, all pauses, actual admittedcyanlocalcurves/orangeglobal
route and causal solve times are retained. Full decode/all4871indices and
start/middle/end/activecurve(frame1500)visualchecks passed. No physics was run
for this display. The native source and source snapshots are frozen and checked.

Finish-work archive/auto-commit step was not executed: task-owned work is
uncommitted alongside the pre-existing dirty repository and index-lock history.
The skill's dirty-work gate stops before automatic archival. Preserve these
changes for review; do not touch the user's unrelated staged changes or lock.
The wider task's30Hz/smoothness objectives remain open. No further navigation
change, formal training or real-robot motion has been started.

## v177 stop-cause audit: arrival does not qualify physical holding

Dr Sun requested every stop explained and substantial upstream source review.
Read-only audit:35/35 controller revocations matched cancellation owner/reason;
30recovery events separate from5final stops;33low-speed intervals include5final
holds. Sufficient trigger groups:20source-age violations,3fresh-input curve
rejections,3progress timeouts,4missing-first-curve timeouts. Source age does not
exclude simultaneous geometry failure; original timing cannot apportion all
input, map compute, publication and scheduling delay.

Three fresh rejections reproduce native first-collision phase/sample count in
ordered recorded-sensor checks (unknown voxel, negative support mask, missing
front support). Three long-stall endpoint checks and four failed recovery-body
checks add geometry evidence. Initial diagnostic matrix-layout and stale-timer
selection mistakes are retained and excluded. All six corrected curve probes
complete locally. Remote native execution was held by resource admission; only
read-only low-priority export/analysis ran remotely. No new physics or version.

Critical:run01actual mask intrusion starts79.6878357s, before progress revocation
80.187561s. During80.187561–96.048843s,661gated commands are zero. Excluding the
first0.2s,783telemetry samples all have effective zero command and STAND_SETTLING;
measured displacement0.956651m. Four-contact, speed, tilt and support-balance
gates prevent fixed stand. This keeps stop/recovery repair open despite5/5arrival.

13upstream repositories inspected, including exact Nav2Foxy and newer MPPI,
official Lite3 deploy, Unitree deploy and legged_gym.27existing pinned source
files reverified against canonical GitHub bytes; additional fixed sources carry
manifests. No upstream run or import into navigation. See
`audits/2026-10-12_v177_stop_causes/REPORT.zh.md`, `stops.html`,
`DIAGNOSTIC_LIMITS.md`, and `.pipeline/survey/2026-10-12_v177_stop_recovery_upstream_survey.md`.
v177freeze verification still passes4079source pairs/618runtime inputs. Next
implementation priority:qualify stopped-pose retention before optimizing away
transient route cancellations. Keep safety gates and frozen predecessors.

## RL zero-command follow-up: revise the proposed repair, no execution change

Dr Sun challenged the assumption that a hold transition can solve underlying RL
stopping limitations. Seven locomotion repositories were inspected, tracing
active robot-specific reward configuration rather than function names alone.
32 new upstream text files have source manifests; earlier legged_gym and Lite3
references were reused. See `.pipeline/survey/2026-10-12_rl_zero_command_upstream_survey.md`.

The bridge-bound machine-dog commit8c3fdffa84b85be0704a10ea5b2533817d543822 was
read without modifying the sibling. V12's nominal zero-command branch only
clears XY and leaves sampled yaw; stand_still is not wired and standing posture
multipliers are1.0. Original training-run overrides and true-zero frequency were
not verified. These source findings do not establish the sole drift cause.

The earlier per-leg hold candidate and2cm/10s target are not proven capabilities
or selected implementation. Next isolate fixed-policy move-to-zero behavior on
flat/landing/stairs, distinguish stepping from sliding and feasible support,
then compare policy-only/current hold before choosing a repair. No new version,
policy/gain/controller edit, physical run, training or hardware action occurred.

## v179 policy-only tests executed; v181 review video preparation

Dr Sun explicitly approved disconnected-navigation flat/stair move-stop-restart
tests and video. v179frozen135source files; six phase/analysis tests and1000-frame
existing golden-policy tolerance pass. Twelve Mac CPU episodes completed, six
per terrain, with24nominal10s stops. Each stopped sample verifies effective zero,
policy ownership and20/0.5gains. The original factory startup/REJOIN precedes
detachment; no physical reset occurs in a trial. No model or locomotion fix.

Four of12flat stops and seven of12stair-scene stops exceed5cm maximum late
excursion after the first2s. Flat worst late31.15cm / total endpoint60.81cm;
stairs worst late14.54cm / total endpoint31.92cm. All second walking phases move
0.49–1.38m. Stair scene includes the flat approach; first slow stops01–02start
before the first riser. This proves drift without navigation in current Newton,
not a sole training cause or a cross-simulator/real-robot result.

All12closed raw archives,13members each, verified on gpu5070ti under
`/data/sun/vla_mppi_20261009/policy_stop_v179_mac/archives/`; local compact results
and receipts are `versions/v179/results/`. Peak child RSS842MB. gpu5070ti still
had other tasks; its20GiB/no-compute admission was not weakened. Local raw remains
`/private/tmp/vla_policy_stop_20261012/`. v180retained a visual-QA failure from
Mac Retina overlay coordinates; v181corrects rendering only. Video delivery
remains pending until full decode and visual/source-frame checks complete.

## 2026-10-13: correct the speed precondition and complete v182 diagnostics

The preceding v179 interpretation omitted Dr Sun's existing 0.6 m/s minimum
planned cruise contract. Its 0.2/0.35/0.5 m/s trials remain low-speed controls,
not nominal-range qualification. The standing-takeover/training remedy is
withdrawn as a selected next implementation. The training sampler's dynamic
per-axis exclusion is a separate fact, not a fixed 0.6 m/s training minimum.

v182 changes only walking amplitudes to 0.6/0.8/1.0 m/s, with the same six
duration conditions per terrain, model, gains, scene, startup and stop windows.
All twelve Mac episodes and twenty-four 10-second policy-only stops completed.
Flat late excursions over the descriptive 5 cm flag change from 4/12 to 0/12;
largest late excursion changes from 31.15 to 3.67 cm. Stair-scene flags change
from 7/12 to 4/12, maximum 14.54 to 10.08 cm. Stair stopping positions differ,
so these are not isolated estimates of a speed-only effect on stair contacts.
Measured flat means are about 0.57/0.78/0.99 m/s for 0.6/0.8/1.0 commands.

All twelve v182 raw archives and thirteen members each are verified on the
user-designated gpu5070ti storage host. v182/RESULTS.md, speed_comparison.json,
raw receipts and parent_binding.json preserve results and source provenance.
v181 low-speed videos are fully verified; v183 higher-speed video production is
complete: all twelve clips, both six-trial combined videos, frame/source hashes,
full decode and representative visual review pass. See v183/DELIVERY.md and
DELIVERY.json; v181 retains all low-speed controls. Physical work was local Mac,
not a Linux repeat. Navigation and the
original v177 automatic-hold failure remain open; no repair or retraining claim.

## 2026-10-13: actual RL input speed around all historical v177 stops

Dr Sun requests actual commands, not configuration: inspect all five original
routes around each stop, separate normal ramps/zero/yaw from prolonged low
walking, and assess the link to instability. The new read-only audit is
`audits/2026-10-13_v177_rl_speed/`; navigation and physical versions are unchanged.

30,741 original 50 Hz samples match effective commands, observation[6:9] and
the term-major ONNX command history[60:90] exactly, with no sample gaps.
Every nonzero horizontal command matches a recent original tracker output;
requested and effective commands also match. Five intervals contain endpoint
correction. The clearest is R1 58.82–69.01 s below 0.6; after its initial braking,
59.86–69.01 s remains at median 0.0175 m/s with about 2.19 cm endpoint error.
This matches gain 0.8 against the current 2 cm finish threshold; RL ownership
persists. Seven other >2 s intervals are curve-boundary transitions and remain
separately qualified, not declared faults solely from duration.

The worst zero episode is 80.20755–96.07883 s: 794 actual all-zero input samples,
maximum 0.95825 m excursion, 0.90180 m after the first 2 s, all STAND_SETTLING.
Long low commands therefore explain a real endpoint/standing interface problem
but do not alone prove the later zero-command drift cause. No matched-state
counterfactual or repair was executed. All 35 events have plots and windowed
statistics, three targeted tests pass, and raw member identities are verified.

## 2026-10-13 terminal capture candidate

- Surveyed six pinned sources: Nav2 Foxy, ROS navigation, CMU Go2, TEB, SCAN, EGO.
- v184 adds per-curve completion and3cm capture; only three native files differ
  from v177. RL/stance/physics/map/start/mission gates unchanged.
- Reexecuted39 unique native controller tests (colcon42 summary), native
  terminal regression, two profile tests, actual graph/library inspection.
- Preserved v184 attempt01: refused before physics due missing quality metadata.
- v185 is an independently built AMD64 port;649 native source hashes match
  v184,18 host tests and live graph checks passed. Source frozen before physics.
- gpu5070ti five-run cohort in progress; first full-route arrival and four
  measured-proof recovery replacements passed. Endpoint-speed audit pending.

- v185 cohort closed:3/5 arrival, endpoint criterion4/5; candidate rejected.
  Actual RL command/history audited across24,075 frames with exact equality.
- v186 keeps2cm completion and adds bounded1s/5mm progress monitoring inside
  a3cm terminal region; native regressions passed. No RL/stance/safety changes.
  Capture logging distinguishes tolerance completion from no-progress release.

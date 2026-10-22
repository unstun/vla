# v290 checkpoint 2026-10-21

Local parent v289 is unchanged and its378 declared file hashes were verified. v290 native source has332 files. No subagents, staging, commits or new physical actuation.

Private ultra9 workspace /home/ubuntu/sun/vla_v290_20261021; local version versions/v290 and audit audits/2026-10-21_v290_terrain_terminal/ultra9 under the Newton experiment.

Implemented: terrain representation independent of exact endpoint admission, original exact start and terminal connector retained; nonexact obstacle retreat stays on terrain with per-XY support association; terminal kp_pos distance speed ceiling before original capture, phase scaled only when the terminal ceiling binds. Original capture/slew/PD/emergency contracts unchanged.

Native build01 full14 passed299s; build02 incremental14 passed36.8s. Components03 all14 functional package suites pass plus synthetic stair/repair/tracker probes; parent fails exact-stair(0/2 vs2/2), terrain-retreat and new approach assertions as intended. Inherited3 Nav2 lint checks explicitly excluded as in parent.

Development failures retained: components01 probe CMake missing copied spawn_margin.cpp; components02 found an unintended generic-speed-clamp phase change, fixed in build02; diagnostics_launcher01 used the old component receipt name and stopped before replay. diagnostics01 completed10 parent/candidate captures after corrected launcher02, no new physics.

Captured-neighborhood replay uses complete measured prefixes, synchronous mapper, exact measured starts and rounded original log targets; it is not exact async/FSM state. All8 seed requests still fail in candidate and parent. Four late measured starts become verdict7. Contributors show A04/CM02 terrain=1,current_nonterrain=0,historical_nonterrain=1 cells; current ground labels do not erase old nonterrain evidence. Do NOT waive obstacles or clear history. Classification probe now compares original actual measured points against existing qualified physical-floor evidence. extraction shows2412/3700/137715/182 points in flagged cells for A04/G05/CU06/CM02; large CSVs stay remote.

CD12 actual Controller/LocalMotion/TrackingNode pose+spline replay has4977 ticks,0 exceptions each parent/candidate. At0.262m goal distance speed drops0.4943->0.2096m/s; at first recorded crossing pose parent0.2001,candidate0. This proves changed command behavior, not repaired physical geometry. Original applied physical command at that pose was0.4066; callback schedules differ. Never call the replay a new physical success.

Classification running via migration/classification.py (launched PID3813353), receipts evidence/classification01.json and classification_launcher01.log. A-star/terminal changes are NOT frozen yet. All53 scoring and new physics not started.

Prepared strict53 helpers: source/run_native.py,run_matrix.py and migration/benchmark.py; evaluator native_probe compiled. evaluators01 failed geometry because probe271.env was not sourced, after successful evaluator compilation; local evaluators.py now supports tag02 and sources it. It has NOT rerun yet. Classification guard correctly requires only the successful build, not geometry stage. Diagnostics and components adapters remain development versions; update final receipt tags only after validated source changes.

Next: finish actual point classification; if source mismatch confirmed, fix raw ground classification at its original evidence owner with negative obstacles preserved, then full native rebuild/tests and captured replay. Do not freeze/score before these source defects are addressed. Only after component closure derive final manifest/strict53. No new physics currently authorized by the v289 closure; present concrete validated v290 for the final physical-run decision.


## Current authoritative checkpoint — v290 frozen, formal physics started

Final navigation production changes are7native/testfiles. raw_return_classification recognizes a legal adjacent selected-tread riser from either side. rawContributorOccupancy retains raw occupancy/history and excludes only entire source voxels below the query-associated selected support floor. Existing terrain, freshness, support and real above-floor obstacle gates stay. No physical-floor-presence cast or source mesh query was added. Exact A-star endpoints remain exact; intermediates/retreat use terrain; terminal kp_pos speed ceiling and matching phase preserve original capture.

Build04 and components05 pass. The single old shared-support test assertion depended on asymmetric riser classification; it now independently checks unchanged exact source-grid/tread classification, legal riser and above-both-treads rejection. All14 functional suites pass. Parent controls fail intended exact-stair/riser/terrain-retreat/terminal assertions.

Captured diagnostics02 passes8/8 actual measured-start/rounded-log-goal requests, versus0/8 parent and terrain-only candidate. Every returned endpoint is exact. Candidate results are locally returned under H/captured_results02. CD12 actual-controller recorded-pose replay4977ticks0errors shows approach slowdown; this is not new physical geometry.

Official frozen native manifest SHA2d69f0cf2ca458bca0f30c533f017f229d31dad625a6445905c8516721641c2a;351declared files,332native files. All351localbytes verified. NEVER edit frozen V290 files. Extra result/admission artifacts are separate. RootR=/home/ubuntu/sun/vla_v290_20261021, localV=Newton/versions/v290,H=Newton/audits/2026-10-21_v290_terrain_terminal/ultra9.

Complete strict53 gate passed:49/50legal,3/3illegalrefusal,global median1.361381101s,p952.029224516,max2.048112248;47/49firstGPMPpass. All53 independent audits finish0; admitted and local source/raw margins pass; selectedten pass. All50starts pass extra support/solid min0.1499999046/0.1441991991m. Original2CPU timing under shared CARLA/ROS load, no timing exception. Native code/GPMP/global profile untouched during scoring. H/offline compact results returned.

Physical runtime is a private copyR/repo, with separate materialized execution bindings in H/runtime_version and H/physical_template.py. Frozen351navigation source remainsR/source; installedmainR/native. The runtime v290 directory holds only execution bindings plus aliases to frozen src/manifests; do not confuse it with new navigation code. Old nestedv289launch transformations were materialized into one common template (A04/D07normalizeidentical); no route-specific navigation branch. Resource policy remains approved16GiBavailable,10GiBdisk,GPUobserved,CPUphysics/policy.

Zero-physics assembly failures retained: empty Docker-createdR/native/fixtures mountpoint interrupted prepare01; fixed resumably without touchingparent. A04preflight01found a fixture symlink resolving generated YAML into parent absolute path. H/materialize_fixtures.py replaced only our symlink with byte-identical private copies;27?fieldidentities recordedevidence/fixture_paths01.json. Allten preflighttag02passed,0steps, matching singlemain installation and original numerical profile. No actual attempt is consumed by these preflight failures.

Physical execution manifest SHAbe6275e1238e1a477ea95aa920addb65e127e6520cb9188ca2dc6b7a79776512,8262files. Local proof:8250byte-exactmatches,12heavygeometryfilesretainedremote with verified hashes;all8262remoteverified,0mismatch. Newcode/config all local. H/dependency_return01archives27missing compactbindings without modifying older local versions. H/evidence/execution_local_return01.json was copiedback toR/evidence. Execution reviewstrictpassed recordedR/source/execution_review.json and returnedlocalV asartifact.

Formal ten once-only physical batch launchedPID3748078 via M/batch.py run. Never restart it or a started positive-step route. ReadR/evidence/physical_batch_status.json,physical_batch01.log,physical_<CASE>_attempt01.log. Fixed order A04,G05,CU06,D07,S04,CD12,CM02,CM07,CS03,CE03. ActualrunR/physical_runs/v290_<CASE>_attempt01/runs/v290_<CASE>_attempt01. Batch tolerates legacy wrapperexit2 if positive result/once ledgerexists; nativefinish+measuredPD+geometry determine outcome. Preserve all failures.

Frozen physical-critical M files: physical.py,physical_template.py,batch.py,preflight.py,physical_setup.py,benchmark.py,execution_policy.py and runtimehelpers/bin/profile/source refs. DO NOT edit them afterbe6275freeze. New analysis/report/render helpers outside physical manifest are allowed; no navigation modifications/reruns.

Remaining work: monitor10physical attempts, prepare/reuse recorded-state analysis and render helpers (old H289 scripts available locally), render10complete videos and return compact data + actual MP4s, SHA/full-decode/20-frame visualreview, ChineseRESULTS_zh.md and galleryHTML. No postphysics analysis helper is launched yet. After physics, preserve raw captures despite legacy lsof retentionwarnings; existing v289 nonpruning capture_snapshot workflow is available. Complete local source/physical manifest recheck and parent378hash unchanged. Update versionindex/spec/taskreview after actual results; no baselinepromotion or commit.


## Physical continuation checkpoint

Originalbatch01closedA04withFINISHED/PD;G05abortedafterscan326deadline122.908254998ms(period100ms),workerCPU39.502217999ms,runnablewait76.357431ms.Lastactualtelemetry43780physicssteps43.767574s;noresult.jsonordriverresult.Neverretryit.Theoldbatchmisclassifiedmissingresultasstartup_failure;preserveoriginalstatusandlogs. M/continue_physics02.py recordsseparateprovenanceandcorrectedconsumedprefix,thenonly8never-startedcases.PID667837. Status=evidence/physical_batch_continuation02_status.json.

A04andCU06andS04andCM02andCM07nowhaveactualFINISHED+measuredPD;geometrypending.D07FAILED144.376s(7noexe,78insideobstacle;verdict7voxel2late);CD12FAILED124.503s(terminal_settle_timeout,noexe0,inside0,2pool/endpointand6Astarmentions).Noalgorithmpatchesorretriesafterfreeze.CS03currentlyrunning,CE03remaining.

Analysis-onlyhelperspreparedlocalArootandH;matchingremoteArootandM. M/analyze_case.py adaptersreuseparentanalysiswithactualprofile/sourcechecks,rawsourceoracle,source/supportandcommandaudits. prefix_analysis.pyuseslastactualtelemetrymetadataforanabortedrecordingandnevercreatesresult.json;verifyroutefailsifmissing.Prefixdriver/windowsfallbackusesthefirstactualvideo_stategoal_sent,notinventedarrival. Newanalysis_verify_case.pyusesvirtualv290filepathtoreuseoriginalpreciseendpoint/PDcontract,withoutaddingfilesintofrozenruntimeversion. Render_case includesRECORDER_FAILEDcaptionandactualfullprefix. Analysisretryverifiesoriginalcapture_snapshotmemberswithoutresnapshottingderivedfiles.

Firstafter_physics01watcherexitedbecauseitreadunchangedoldstartup_failure;logretained. after_physics02.py(PID792899)watchescontinuationstatusandwaitsforphysical_batch_complete.json,thenrunsanalyze_all.py(twoCPU/recordedrenderjobs,nophysicalsteps).Needmonitorandfixanalysisadaptersasnecessary,preservefailedlogs,nevereditfrozenphysicalcriticalhelpers. All53passed,localXMLreturn270cases(256functional+14cppcheck/lint_cmake),0failure/error/skips.

LocalH/build_gallery.pyandwrite_report_v290.pyarepreparedbutnotexecuted;case_diagnoses.jsonawaitsactualaudits. Needcompleteallten,analyze/render,collect_results.py,thenstartup/inputorder/boundary/mechanismverification,syncreturnedreports+10actualMP4s,localmedia_qa/local_decode,visual20frames,gallery/ChineseRESULTS,manifestandparentverification,versionindex/taskreview. Noresultclaimuntilactualdata.


## Final delivery checkpoint — ten attempts and media closed, physical acceptance failed

All10formal positive-step attempts are closed, exactlyonceeach;825000recordedstepslowerboundbecauseG05/CS03lackfinalresult. A04,CU06,S04,CM02,CM07,CE03recordFINISHEDandpassoriginalPD/endpointverification. Combinedsampledfactory+recordedphysicalgeometrypassesA04/CU06/CM02/CM07(4/10). Strictall-Free-staticverdictcombinationis3/10,keptseparatefromactualsupport/solidgeometry.

D07FAILED(-27.598cm),CD12FAILEDterminal_settle_timeout(-13.770cm);S04FINISHEDbut-2.949cm,CS03scanabortedafter-4.655cm,CE03FINISHEDbut-1.967cm. Allfivefirstcrossingsoccurwithin0.163mofgoal.Nativesignals0,secondaryunresponsivemarkers2afterrecorderscanabort,regressedbodyerrors0,globalgeometrypreserved10/10. Logs:pool2,endpoint2,Astar27,inside88,strict-1008lines773,noexe13. DoNOTcallCD12fixedorv290accepted.

Confirmedremainingcodestructure:Controller.cpp173-180canentergoal_braking_in25cmpositionbandandreturnLocalMotion::brakeCommand(),whichcallsTrackingNode::publishStopbeforecentering. TrackeritselfalsostopsXYwhenyawisinband. Currentearlyapproachcapisthereforeinsufficient. D07firstcrossingwz1rad/swithonly~0.028m/sXYat8.48cmgoalerror;worstunderSTAND_SETTLING. CD12firstcrossingat9.48cmgoalerrorunderRL;worstSTAND_TRANSITION. Staticgoal-center330querydiagnostic:CD12specifiedyaw+5.71mm,all-yawsminimum-11.28cm. Thisdoesnotaloneattributeitsactualnegative-yawincident;exactcenternearbynegativeyawprobesareclear. Keepactualoffset/PDslipandstaticyawfeasibilityseparate.

Analysisbatch01failedbeforeanalysisbecauseprefiximportpathmissing;fixedanalysis-onlyprefixadapter,batch02passesall10. Nonpruningsnapshotsretained,andoriginalrawsareunchanged. post_collect01startup/input-order/boundary/mechanismauditspass;initialfinalverificationfailswithschemaKeyError(filesvssource_files),retained. Standalonefinal_verify_remote02passesthecorrectparentschema:378parentfiles,8262frozenexecutionfiles,0activeownedcontainers,16foreigncontainersleftalone,38.9GiBfree. Candidate351andparent378localdeclaredfilesalsopasshashverification.

All10ordinaryMP4s119 million bytes(118997605exact)arelocallyreturnedandSHAmatch,fullffmpegdecodepasses,20realframesvisuallyinspected. LocalHTMLdelivered/index.htmlandChineseRESULTS_zh.mdarecomplete. Browsertoolfile://automaticpreviewwaspolicy-denied;noalternateprotocol/surfaceworkaroundwasattempted. HTMLdata/relativefiles/DOMIDs/JavaScriptparsearecheckedstatically;donotclaimbrowserUIplaybackverified.

FinalHartifacts:RESULTS_zh.md,acceptance.json(false),physical_summary.json,physical_table.csv,case_diagnoses.json,delivered/index.html+10MP4s,MEDIA_STORAGE.md,final_delivery_inventory.json,component_return01,offline,startup_return,physical_return,evidence,terminal_geometry01. All763compactreturnedfilesandfrozenanalysisadapterswereverified. Only10exactvideopathsignored;per-fileSHA/storage/regenerationdocumented.NoGitstage/commit,baselinepromotion,rawdeletionoradditionalphysicalattempts.

VersionindexandnewV290/RESULTS.mdreflectactualfailedacceptance;frozenV290source/README/manifestnotedited. Taskremainsin_progresswithdelivery_complete=true,physical_acceptance=failed,terminal_repair_open=true. Anynewnavigationchangemustbeaseparatenewintegerversion;doNOTretunefrozenv290orretryitsroutes.

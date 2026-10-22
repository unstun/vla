"""Write the v287 report strictly from returned, hash-verified run evidence."""
from pathlib import Path
import csv,hashlib,json,statistics
H=Path(__file__).resolve().parent
E=H.parents[2]
B=E/'audits/2026-10-19_v286_supported_air_refinement/migration_ultra9'
load=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
fmt=lambda value,places=3:'n/a' if value is None else f'{value:.{places}f}'

def main():
 s=load(H/'physical_summary.json');old=load(B/'physical_summary.json');g=load(H/'offline/offline_gate.json')
 bill=load(H/'physical_return/failure_terminal_bill.json');parent=load(B/'physical_return/failure_terminal_bill.json')
 inventory=load(H/'physical_return/return_inventory.json');startup=load(H/'startup_return/summary.json')
 assert s['formal_attempts']==10 and len(inventory['videos'])==10 and g['calls']==53
 for n,r in inventory['videos'].items():assert (H/'delivered'/n).is_file() and not (H/'delivered'/n).is_symlink() and sha(H/'delivered'/n)==r['sha256']
 rows=s['cases'];errors=[]
 keys=list(bill['cases'][0]['target_errors'])
 for key in keys:errors.append(dict(metric=key,v286=sum(r['target_errors'][key] for r in parent['cases']),v287=sum(r['target_errors'][key] for r in bill['cases'])))
 with (H/'error_comparison.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=['metric','v286','v287']);w.writeheader();w.writerows(errors)
 stages={r['case_id']:load(H/'physical_return'/r['case_id']/'results/local_stage_latency.json') for r in rows}
 all_legal=[r['metrics']['global_s'] for r in load(H/'offline/matrix_summary.json')['calls'] if r['expected']=='admit']
 coupled=sum(r['goal_pd_and_all_recorded_physical_envelope_clear'] for r in rows)
 factory_good=sum(r['sampled_factory_envelope_clear'] for r in startup['cases'])
 accepted=bool(g['passed'] and coupled==10 and factory_good==10 and s['native_process_failures']==0)
 audit=dict(offline_passed=g['passed'],goal_pd=s['goal_and_pd_passed'],goal_pd_and_recorded_envelope=coupled,factory_envelopes=factory_good,physical_acceptance_passed=accepted,version='v287')
 (H/'acceptance.json').write_text(json.dumps(audit,indent=2)+'\n')
 lines=['# v287 complete offline and single-attempt physical report','',
  f"离线：{g['positive_passed']}/50 合法路线、{g['illegal_correct_rejections']}/3 非法对照，全局中位数 {g['global_median_s']:.3f} s。实跑：到达并完成 PD {s['goal_and_pd_passed']}/10；到达且后续完整传感器记录几何通过 {coupled}/10；起立记录包络通过 {factory_good}/10。原生进程故障 {s['native_process_failures']} 次。完整物理验收：{'通过' if accepted else '未通过'}。",'',
  '## Scope and immutable identities','',
  'The local VLA repository is the source of truth. v287 is a new329-file native composition from frozen v286; nine production files change. No scene, route or coordinate navigation branches were added. The hard source radius stays0.35m and the scanner period/deadline stays0.1s. Factory PD/policy, freshness/starvation limits, static global reference retention and tracker are unchanged.',
  'The remote execution copy is /home/ubuntu/sun/vla_v287_20261020 on ultra9 (Core Ultra9 285K, RTX5070Ti). v286 raw data and earlier frozen versions remain preserved. No additional storage deletion was performed. Geometry and all53 zero-step captured inputs are reused byte-exact from v286 on the same host; every scored planner call and physical recording is new.', '',
  '| Identity | SHA-256 |','|---|---|']
 for label,path in [('Local v287 source/cohort manifest',E/'versions/v287/native_manifest.json'),('Native installed/input/evaluator manifest',H/'evidence/native_manifest01.json'),('Physical execution manifest',H/'evidence/physical_manifest01.json')]:lines.append(f'| {label} | `{sha(path)}` |')
 lines += ['', 'The offline/build container is pinned to ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343. Physical Nav2 uses the task-owned GDB image af529e408d9d130ba7b15a1eb2b78dc7b5408953a0de994ea05cccb43972fbec. The factory logical image, policy and original input identities remain unchanged. Release/O3 builds retain line symbols and frame pointers. Shared system settings and foreign jobs were not changed.','',
  '## Implemented changes and native evidence','',
  '- Removed exact-source rebound helpers and their L-BFGS calls. First-stage environmental scoring uses the existing precomputed ENV225 table; refinement still excludes environmental terms. Exact source geometry remains in global/static admission and independent audit.',
  '- Replaced both capped penalties by max((target-margin)/target,0), and retained edge/solid derivatives below zero margin. Identical negative/zero/positive finite-difference checks fail4/8 on immutable v286 and pass8/8 on v287. Synthetic ENV queries take approximately0.2microseconds, with no added spatial searches; this is not a whole-planner latency claim.',
  '- Removed the supported-air source collision call/cache. Normalization requires in-map, zero inflation and a complete passing support/layer/edge/freshness decision. Raw-unknown classification again precedes inflation/contributor classification. Actual native negative controls retain stale, inflated, unsupported, unassociated-height and out-of-map refusal.',
  '- Added checked endpoint/neighbor pool access and safe empty AStar ownership initialization. Positive-tolerance terminal-border and out-of-pool tests exercise the actual search. The parent already checks all axes in Coord2Index; no old crash stack establishes an out-of-bounds cause. The new access guards are tested prevention, not proof of the old SIGSEGV cause.',
  '- Completed aligned allocation declarations for missing Eigen owners/results. GridMap, SCANReplanFSM and BsplineOptimizer already had declarations, and the affected packages already use C++17. Alignment alone is not established as the old crash cause. All14 packages were rebuilt cleanly to avoid mixed class layouts.',
  '- Native Nav2 children run under a signal-preserving GDB wrapper. Five zero-physics SIGSEGV/SIGBUS/SIGABRT/SIGILL/SIGFPE injections each return their signal exit status and retain all-thread, symbolized stacks. Python children enable faulthandler. Actual fault receipts/stacks are retained when present.',
  '', 'Qualification includes174 inherited native executions,18 repair checks,8 field checks,4 terrain directions,4 tracking clock cases,5 signal tests and50 legal-start checks. Development fixture-format and ROS-log-directory failures were preserved separately; they are not scored routes or physics attempts.', '',
  '## Full 50+3 gate','',
  f"All53 calls and independent geometry audits finished. Legal {g['positive_passed']}/50; illegal refusals {g['illegal_correct_rejections']}/3. Admitted-route global median {g['global_median_s']:.6f}s, all50-legal median {statistics.median(all_legal):.6f}s; admitted p95 {g['global_p95_s']:.6f}s, maximum {g['global_max_s']:.6f}s. Gate {'passed' if g['passed'] else 'failed'}. Initialization is excluded from the timed global call and is retained per case.",
  'All50 legal starts pass: minimum extra edge margin0.1499999046m and source-solid margin0.1441991991m. No requests were resampled after results. Full case details and timing are in offline/matrix_summary.json and matrix_table.csv.', '',
  '## Ten single physical attempts','',
  'Each route ran once after the complete offline gate. A failed prefix with clear sampled margins is not a completed geometric success. The table reports minimum margins over all recorded10Hz body poses, including terminal/tail poses; factory startup is audited separately below. Margins cap at+0.15m.','',
  '| Route | Goal + PD | Goal + full recorded geometry | Duration s | Measured path m | Support extra cm | Source extra cm | Raw extra cm | Max low-speed pause after motion s |',
  '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
 for r in rows:lines.append(f"| {r['case_id']} | {int(r['goal_and_pd_passed'])} | {int(r['goal_pd_and_all_recorded_physical_envelope_clear'])} | {r['simulation_duration_s']:.2f} | {r['measured_path_m']:.2f} | {100*r['all_recorded_support_gap_min_m']:.3f} | {100*r['all_recorded_source_solid_min_m']:.3f} | {100*r['all_recorded_raw_point_min_m']:.3f} | {fmt(r['maximum_pause_after_first_translation_s'])} |")
 lines += ['', f"Original global-reference geometry is retained on{s['cases_with_original_global_geometry']}/10 routes. Native process faults:{s['native_process_failures']}. Scanner jobs:{s['scanner_jobs']}; deadline failures:{s['scanner_deadline_failures']}. Per-case command, pure-yaw, settling, pauses, terminal pose and PD evidence is in physical_table.csv and physical_return/*/results/.",'',
  f"Actual navigation RTF ranges {min(r['actual_rtf'] for r in rows):.6f}–{max(r['actual_rtf'] for r in rows):.6f}; dropped physics steps total {sum(r['dropped_physics_steps'] for r in rows)}. Target pacing stays1.0. Debugger startup/fatal stops can perturb wall timing; original recorded clocks are retained and no faster-than-recorded physical performance is claimed.",'',
  '## Local latency and error counters','',
  'Stage timing comes from actual V50_PROFILE log records. Optimizer timing is reported separately from complete local rounds, which also include search, input refresh, seed preparation, refinement and final checking. A low median does not imply every round met50ms.','',
  '| Route | Whole-round median / p95 / max ms | Optimizer median / p95 / max ms | Optimizer reports >50ms |',
  '|---|---:|---:|---:|']
 for r in rows:
  t=r['local_solve_ms'];o=stages[r['case_id']]['stages']['optimizer']
  lines.append(f"| {r['case_id']} | {fmt(t.get('median'))} / {fmt(t.get('p95'))} / {fmt(t.get('maximum'))} | {fmt(o['median_ms'])} / {fmt(o['p95_ms'])} / {fmt(o['maximum_ms'])} | {o['over_50ms']} / {o['reports']} |")
 lines += ['', '| Same literal log counter | v286 | v287 |','|---|---:|---:|']
 for r in errors:lines.append(f"| {r['metric']} | {r['v286']} | {r['v287']} |")
 lines += ['', '### Recorded solid-boundary witnesses', '',
  'D07 first crosses at116.767456s while RL owns joints and the applied command is[0,0,1.0]; XY distance to the requested goal is0.125061m. Its worst source margin is-0.016354m. CD12 first crosses at126.162292s with[0,0,0.501875] and goal distance0.106848m; the worst-0.042260m occurs during STAND_TRANSITION with zero command. Full measured state/command witnesses are in boundary_state_audit.json.',
  'At the worst D07 sample, the latest causal curve is0.040s old and its nearest spatial point is0.017837m from the body. That point has+0.076694m source margin at its planned tangent heading; measured body yaw differs by128.350degrees and its actual margin is negative. CD12 nearest-point distance is0.039597m, with+0.070176m planned-heading source margin and23.500degrees body-heading difference. The last curve there is1.399s old. These are geometry/command comparisons, not a reconstruction of scaled tracker phase or proof that an old curve is currently executable.',
  'Both first crossings coincide with terminal pure yaw, which the inherited tracking_node.hpp:310-323 branch permits inside XY/Z tolerance. The corrected optimizer gradient therefore cannot by itself certify the actual final-turn/PD envelope. No scene-specific fix or publication veto was added to hide this result.', '']
 lines += ['', 'Actual native fatal signals and their fault-thread frames:', '']
 for case in bill['cases']:
  for fault in case.get('native_faults',[]):
   project=[line for line in fault['fault_thread_frames'] if any(x in line for x in ('GridMap::','AStar::','/work/src/'))]
   lines.append(f"- {case['case_id']}: {fault['signal']}; {fault['fault_instruction']}; first source frame: {project[0] if project else 'see full stack'}.")
   if fault['allocator_messages']:lines.append('  Allocator evidence: '+str(fault['allocator_messages']))
 lines += ['', 'A04 faults in terrainCellLayers cache lookup, CU06 in rawContributorOccupancy cache lookup, and CM02 reports double-free/corruption during A-star queue-vector growth. These are observed fault sites; an earlier invalid write/free or concurrency error can corrupt those containers. The stacks do not establish Eigen alignment or the endpoint pool as the root cause. Point4 remains unvalidated. Frozen v287 was not modified or retried to hide these results.',
  'The unmodified literal counters above remain directly comparable. Application-only counters excluding debugger dumps are separately retained for every case; inspect them if a debugger frame contains an error literal. PCT core keeps its inherited O2/C++14 configuration; the affected local libraries use C++17/O3 with line symbols and frame pointers.', '']

 lines += ['', 'Counters are retry-inclusive line mentions, not independent failures. First contexts and stage-specific line-search failures are preserved in failure_terminal_bill.json. The inside-obstacle string comes from a control-point collision walk and is not itself a measured-trunk collision. Inspect typed verdicts and actual geometry separately.', '',
  '## Startup, geometry and video integrity','',
  f"Factory startup uses{startup['audited_factory_frames']} original video-state poses, separately from the later10Hz sensor stream. Maximum sampled PD XY drift is{max(r['maximum_recorded_PD_xy_drift_m'] for r in startup['cases']):.6f}m. Startup sampled envelopes pass{factory_good}/10. Nominal crouch-height WrongHeight is reported separately from support-gap/source-solid clearance. No states were interpolated to certify safety.",
  'Source-solid, registered raw-point and support-gap audits operate on measured recorded poses. These are sampled body-envelope checks, not continuous-time or foot-contact certification. No change to the0.35m threshold is hidden by reporting precision.',
  'Ten complete regular MP4 files reproduce original factory and navigation states at30fps, with causal original trajectory overlays. No physics was rerun for rendering. Every video passes full decode, source/state/overlay checks and local SHA verification. See delivered/README.md for all10 file links, sizes and hashes.', '',
  '## Delivery and remaining acceptance boundary','',
  f"Physical acceptance {'passes' if accepted else 'does not pass'}: {coupled}/10 completed with a clear entire later recording and {factory_good}/10 startup envelopes were clear. This single fixed-cohort run does not establish statistical reliability. Remaining failures or timing outliers are preserved as results, not retried or relabeled.",
  'The frozen geometry-start receipt retains a legacy migration field navigation_source_changed=false; that field describes no geometry/input edit and is not the source-change claim for v287. The source manifests and nine-file changes.patch explicitly record the production changes. Legacy all_recorded sensor windows begin after factory startup, which is audited in startup_return/.',
  'Raw captures, snapshots and build bytes remain on ultra9; compact reports, provenance and all10 actual review videos are returned locally. Reproduce analysis/rendering from unchanged raw states using the locally versioned ultra9 adapters. Preserve all frozen parents and failed records.','']
 (H/'RESULTS.md').write_text('\n'.join(lines))
 (H/'delivered/README.md').write_text('# v287 complete physical videos\n\nEach is a regular local MP4 file, one complete single attempt.\n\n'+'\n'.join(f"- [{n}]({(H/'delivered'/n).resolve()}): {r['bytes']}bytes; SHA-256 `{r['sha256']}`" for n,r in inventory['videos'].items())+'\n')
 print(json.dumps(audit))

if __name__=='__main__':main()

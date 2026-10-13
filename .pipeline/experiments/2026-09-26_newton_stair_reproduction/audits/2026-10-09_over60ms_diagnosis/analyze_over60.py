"""Read-only attribution of the six recorded >60ms complete native rounds."""
from pathlib import Path
import argparse,csv,hashlib,importlib.util,json,re,zipfile

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
REPO=BASE.parents[2]
SOURCE=BASE/'versions/v47/analyze_trial.py'
sha=lambda data:hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-root',type=Path,required=True);args=parser.parse_args();root=args.run_root
    archive=zipfile.ZipFile(root/'raw_capture.zip');raw=archive.read('nav2.log')
    manifest=json.loads((root/'raw_capture_manifest.json').read_text());assert sha(raw)==manifest['members']['nav2.log']['sha256']
    observations=archive.read('artifacts/reactive_observations.jsonl');assert sha(observations)==manifest['members']['artifacts/reactive_observations.jsonl']['sha256']
    events=[json.loads(x) for x in observations.splitlines()];text=raw.decode();lines=text.splitlines()
    spec=importlib.util.spec_from_file_location('frozen_round_parser',SOURCE);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    class OriginalLog:
        def read_text(self):return text
    starts,rounds=module.parse_rounds(OriginalLog())
    csv_path=BASE/'versions/v116/analysis/attempt02/latency.csv';csv_rows=list(csv.DictReader(csv_path.open()))
    report_path=REPO/'output/2026-10-09_nav2_local_planning/delivered/timing_data.json';chart=json.loads(report_path.read_text())
    assert len(starts)==len(rounds)==len(csv_rows)==len(chart['rounds'])==900
    assert sha(csv_path.read_bytes())==chart['meta']['latency_csv_sha256']
    source_manifest=json.loads((BASE/'versions/v114/manifest.json').read_text())
    owned_sources=[BASE/'versions/v114/src/plan_manage/src/planner_manager.cpp',
      BASE/'versions/v114/src/plan_manage/src/scan_replan_fsm.cpp',
      BASE/'versions/v114/src/scan_nav2_controller/src/controller.cpp',
      BASE/'versions/v114/src/plan_env/src/grid_map.cpp',
      BASE/'versions/v114/src/plan_env/include/plan_env/reactive_collision.h',
      BASE/'versions/v114/src/plan_env/include/plan_env/planning_profile.h',
      BASE/'runtime/scan_nav2_foxy_v86/src/path_searching/src/dyn_a_star.cpp',
      BASE/'runtime/scan_nav2_foxy_v86/src/bspline_opt/src/bspline_optimizer.cpp']
    checked_sources={}
    for path in owned_sources:
        name=str(path.relative_to(REPO));value=sha(path.read_bytes());assert source_manifest['source_files'][name]==value,name;checked_sources[name]=value
    rows=[]
    for index,round in enumerate(rounds):
        ms=round['wall_s']*1000
        assert abs(ms-float(csv_rows[index]['solve_ms']))<1e-7
        assert abs(ms-chart['rounds'][index]['ms'])<1e-7
        if ms<=60:continue
        begin=round['start_line']-1;end=round['end_line'];chunk=lines[begin:end]
        profiles=[json.loads(x.split('V50_PROFILE ',1)[1]) for x in chunk if 'V50_PROFILE ' in x]
        assert len(profiles)==1
        profile=profiles[0]
        # Target includes goal_search/proof, seed includes warm_seed and initial
        # control-point A*. Inputs overlap other stages. Do not sum all fields.
        hotspot=max(['target','seed','optimizer','refine','final_check'],key=lambda k:profile[k]['wall_ms'])
        item=dict(number=index+1,video_s=chart['rounds'][index]['t'],simulation_s=round['ros_s'],
          wall_ms=ms,success=round['success'],rebound_attempts=round['rebound_attempts'],
          prefix_proposals=round['prefix_proposals'],fixed_height_attempts=round['fixed_height_attempts'],
          start_line=round['start_line'],end_line=round['end_line'],profile=profile,
          hotspot=hotspot,hotspot_fraction=profile[hotspot]['wall_ms']/ms,
          hotspot_cpu_fraction=profile[hotspot]['cpu_ms']/profile[hotspot]['wall_ms'])
        item['astar_exhaustion_warnings']=[dict(log_line=begin+i+1,seconds=float(m[1]),queue_loop_iterations=int(m[2]))
          for i,line in enumerate(chunk) if (m:=re.search(r'A-star path search took ([\d.]+)s, iter=(\d+)',line))]
        item['clouds_received_during_round']=[dict(relative_ms=(e['wall_monotonic_ns']/1e9-round['start_wall_s'])*1000,source_simulation_s=e['data']['stamp_ns']/1e9)
          for e in events if e['event']=='cloud' and round['start_wall_s']<=e['wall_monotonic_ns']/1e9<=round['start_wall_s']+round['wall_s']]
        item['input_refreshes']=[dict(log_line=begin+i+1,site=m[1],age_before_s=float(m[2]),age_after_s=float(m[3]))
          for i,line in enumerate(chunk) if (m:=re.search(r'input_refresh site=(\S+).*cloud_age=([\d.-]+)->([\d.-]+)',line))]
        item['evidence_file']=f'round_{index+1:03d}.log'
        (HERE/item['evidence_file']).write_text(''.join(f'{begin+i+1}: {line}\n' for i,line in enumerate(chunk)))
        rows.append(item)
    assert [r['number'] for r in rows]==[1,123,165,670,703,899]
    assert all(r['profile']['cloud']['wall_ms']==0 and r['profile']['sliding_map']['wall_ms']==0 for r in rows)
    assert all(r['hotspot_cpu_fraction']>.95 for r in rows)
    # Preserve the adjacent safety/snapshot evidence as original numbered lines.
    followup=[]
    for begin,end in [(26535,26579),(27803,27870),(35598,35640)]:
        for number in range(begin,end+1):
            line=lines[number-1]
            if any(token in line for token in ['input_refresh','SCAN output revoked','V82_MAP_SNAPSHOT','emergency stop']):
                followup.append(f'{number}: {line}\n')
    (HERE/'freshness_followup.log').write_text(''.join(followup))
    report=dict(run=root.name,native_version='v114',recording_version='v116',threshold_ms=60,
      rounds=900,over_threshold=len(rows),over_threshold_fraction=len(rows)/900,rows=rows,
      interpretation='Retrospective measured attribution, not a runtime counterfactual or a fix. Profile stages overlap; never sum all columns.',
      source_sha256={'nav2.log':sha(raw),'reactive_observations.jsonl':sha(observations),'latency.csv':sha(csv_path.read_bytes()),'frozen_parser':sha(SOURCE.read_bytes()),'analysis_script':sha(Path(__file__).read_bytes())},
      checked_native_sources=checked_sources,raw_archive_remote='gpu5070ti:/home/sun/vla_artifacts/2026-10-09_local_curve_timing/attempt01/vla_local_curves_v116.tar.gz',
      runtime_changed=False,safety_thresholds_changed=False,new_physical_run=False)
    (HERE/'attribution.json').write_text(json.dumps(report,indent=2)+'\n')
    with (HERE/'attribution.csv').open('w') as f:
        writer=csv.writer(f);writer.writerow(['round','video_s','complete_ms','success','attempts','hotspot','hotspot_wall_ms','hotspot_thread_cpu_ms','inputs_ms','final_check_ms'])
        for r in rows:writer.writerow([r['number'],r['video_s'],r['wall_ms'],r['success'],r['rebound_attempts'],r['hotspot'],r['profile'][r['hotspot']]['wall_ms'],r['profile'][r['hotspot']]['cpu_ms'],r['profile']['inputs']['wall_ms'],r['profile']['final_check']['wall_ms']])
    print(json.dumps({'passed':True,'original_rounds_matched':900,'over60_rounds':[r['number'] for r in rows],'all_hotspot_cpu_fraction_above_95_percent':True,'native_source_hashes_verified':len(checked_sources)}))

if __name__=='__main__':main()

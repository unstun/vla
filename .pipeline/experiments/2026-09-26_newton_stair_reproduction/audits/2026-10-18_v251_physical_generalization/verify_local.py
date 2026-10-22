"""Verify returned sources, outcomes, full videos and retention boundaries."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import ast,hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;VERSIONS=HERE.parents[1]/'versions'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((HERE/'return_manifest.json').read_text())
for rel,row in manifest['entries'].items():assert sha(HERE/rel)==row['sha256'],rel
for version in ('v251','v252'):
 root=VERSIONS/version;m=json.loads((root/'manifest.json').read_text())
 for rel,h in m['source_files'].items():
  assert sha(root/rel)==h,(version,rel)
  assert sha(root/m['snapshot_locations'][rel])==h,(version,rel,'snapshot')
final=json.loads((HERE/'results/final_source_gate.json').read_text());assert final['passed']
assert final['gate']['native_source_version']=='v251' and final['gate']['execution']=='v252'
assert not any(n.startswith('v252-') for n in final['remaining_containers'])
installed=json.loads((VERSIONS/'v251/results/installed_files.json').read_text())
linkage=json.loads((HERE/'results/live_native_linkage.json').read_text());assert set(linkage)=={'A02','G07','R11'}
for record in linkage.values():
 assert len(record['processes'])>=2
 for process in record['processes']:
  for name,h in process['mapped_native_libraries'].items():assert installed[name.removeprefix('/work/')]==h,name
def video(cid):
 root=HERE/'physical'/cid/'results';delivery=json.loads((root/'display/delivery_verification.json').read_text())
 p=HERE/'delivered'/f'v252_{cid}_full_attempt01.mp4';assert p.is_file() and not p.is_symlink()
 assert sha(p)==delivery['video_sha256']
 probe=subprocess.run(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=nb_read_frames,width,height,r_frame_rate,duration','-of','json',str(p)],text=True,capture_output=True,check=True)
 assert not probe.stderr,probe.stderr
 stream=json.loads(probe.stdout)['streams'][0]
 assert int(stream['nb_read_frames'])==delivery['frames']
 decoded=subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(p),'-f','null','-'],text=True,capture_output=True,check=True)
 assert not decoded.stderr,decoded.stderr
 assert delivery['passed'] and delivery['complete_first_and_last_recorded_states'] and delivery['no_future_curve_events']
 outcome=json.loads((root/'outcome.json').read_text());expected=cid!='A02'
 assert outcome['full_route_gate_passed']==expected and delivery['full_route_gate_passed']==expected
 assert outcome['terminal_status']==('FINISHED' if expected else 'FAILED')
 ledger=json.loads((HERE/'preflight_and_execution'/cid/'execution/physical_launch_once.json').read_text())
 assert ledger['authorized_attempts']==1 and ledger['run']==f'v252_{cid}_attempt01'
 return dict(case_id=cid,passed=True,sha256=sha(p),bytes=p.stat().st_size,stream=stream,
  original_delivery_sha256=sha(root/'display/delivery_verification.json'),full_decode=True,
  physical_route_passed=expected,last_physics_s=delivery['last_physics_s'])
with ThreadPoolExecutor(max_workers=3) as pool:videos=list(pool.map(video,('A02','G07','R11')))
parsed=0
for p in HERE.rglob('*'):
 if not p.is_file():continue
 assert p.suffix not in ('.npz','.f32','.pcd','.o','.so','.a','.pyc','.jsonl'),p
 assert 'CMakeFiles' not in p.parts and '__pycache__' not in p.parts,p
 if p.suffix=='.py':ast.parse(p.read_text(),filename=str(p));parsed+=1
summary=json.loads((HERE/'results/SUMMARY.json').read_text());assert summary['formal_attempts']==3 and summary['full_route_passed']==2
assert summary['scanner_total']==2439 and summary['scanner_deadline_failures']==0
assert all(r['stair_pauses_ge_05s']==r['stair_pauses_ge_1s']==0 for r in summary['rows'] if r['overall_result']=='PASSED')
report=dict(passed=True,returned_file_hashes_verified=len(manifest['entries']),returned_bytes=manifest['return_bytes'],
 source_snapshot_parity=['v251','v252'],final_remote_source_gate_sha256=sha(HERE/'results/final_source_gate.json'),
 actual_native_linkage_verified=True,authorized_formal_attempts=3,physical_route_passed=2,
 full_video_checks=videos,python_ast_files=parsed,no_local_raw_arrays_or_build_cache=True,
 source_of_truth='Local VLA repository',claim='Deliverables verified; two single route passes and one retained failure, no reliability claim')
(HERE/'results/local_quality.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(passed=True,returned_file_hashes_verified=len(manifest['entries']),videos=len(videos),formal_attempts=3,physical_route_passed=2)),flush=True)

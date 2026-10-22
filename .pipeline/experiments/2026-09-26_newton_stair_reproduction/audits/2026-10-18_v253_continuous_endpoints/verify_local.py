"""Local source/returned proof and full media verification; no physics execution."""
from pathlib import Path
import hashlib,json,subprocess,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent;EXP=HERE.parents[1];V=EXP/'versions';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((HERE/'return_manifest.json').read_text())
for rel,h in r['entries'].items():
 p=HERE/rel;assert p.is_file() and not p.is_symlink() and p.stat().st_size==h['bytes'] and sha(p)==h['sha256'],rel
for version in ('v253','v254','v255'):
 root=V/version;f=json.loads((root/'manifest.json').read_text());assert f['frozen']
 for rel,h in f['source_files'].items():
  assert sha(root/rel)==h,(version,rel)
  assert sha(root/f['snapshot_locations'][rel])==h,(version,rel,'snapshot')
for version in ('v253','v254'):
 receipt=json.loads((V/version/'results/acceptance_receipt.json').read_text());assert receipt['passed'] and receipt['first_gpmp_static_pass']>=55
 assert receipt['frozen_manifest_sha256']==sha(V/version/'manifest.json')
assert json.loads((V/'v254/results/native_receipt.json').read_text())['unit_test_cases']==48
link=json.loads((HERE/'results/live_native_linkage.json').read_text())['A02']
installed=json.loads((V/'v254/results/installed_files.json').read_text())
for p in link['processes']:
 for path,h in p['mapped_native_libraries'].items():assert installed[path.removeprefix('/work/')]==h,path
attempts=json.loads((HERE/'results/batch_status.json').read_text());assert len(attempts)==1 and attempts[0]['attempt']==1 and attempts[0]['stage']!='running'
root=HERE/'physical/A02/results';outcome=json.loads((root/'outcome.json').read_text())
video=HERE/'delivered/v255_A02_full_attempt01.mp4';assert video.is_file() and not video.is_symlink()
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=width,height,r_frame_rate,duration,nb_read_frames','-of','json',str(video)],text=True))['streams'][0]
subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(video),'-f','null','-'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
original=json.loads((root/'display/video_verification.json').read_text());assert original['status']=='passed' and original['full_decode_passed'] and original['sha256']==sha(video)
assert int(probe['nb_read_frames'])==original['frames']
assert float(probe['duration'])>=outcome['physics_duration_s']-.5
proof=dict(passed=True,returned_file_hashes_verified=len(r['entries']),returned_bytes=r['return_bytes'],source_snapshot_versions=['v253','v254','v255'],actual_loaded_native_libraries_verified=True,formal_attempts=1,physical_route_passed=outcome['full_route_gate_passed'],video=dict(path=str(video),sha256=sha(video),bytes=video.stat().st_size,stream=probe,full_decode_passed=True))
(HERE/'results/local_quality.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof),flush=True)

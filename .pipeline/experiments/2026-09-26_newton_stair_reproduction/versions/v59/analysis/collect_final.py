"""Allowlist compact physical evidence and one requested review video separately."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[2];ROOT=BASE.parents[2];VERSION=HERE.parent
assert str(ROOT)=='/home/sun/vla_exec/vla'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(4*1024**2),b''):h.update(block)
 return h.hexdigest()
files=[HERE/'verification.json']
for run,version,attempt in [('v58_realtime_trial02','v58',2),('v59_realtime_trial01','v59',1)]:
 for suffix in ['_metrics.json','_summary.json','_motion.json','_handover.json','_tail_evidence.json','_frequency.csv','_latency.csv','_progress.csv','_stages.csv','_motion.csv','_handover.csv']:
  files.append(HERE/(run+suffix))
 files.extend(BASE/'versions'/version/f'trials/attempt{attempt:02d}'/name for name in ['preflight.json','request.json','result.json','remote_artifact_manifest.json'])
render=BASE/'runs/v59_review_trial01'
for name in ['full_decode_verification.json','video_verification.json','video_encoding.json','display_measurements.json','host_path_port.json','result.json','request.json','appearance.json']:
 files.append(render/name)
files.extend(sorted((render/'frame_samples').glob('*.png')))
records={str(p.relative_to(ROOT)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(files)}
assert sum(x['bytes'] for x in records.values())<5*1024**2
manifest=HERE/'final_return_manifest.json';manifest.write_text(json.dumps(records,indent=2)+'\n')
(HERE/'final_return_files.txt').write_text('\n'.join([*records,str(manifest.relative_to(ROOT))])+'\n')
video=render/'newton_stair_recorded.mp4';info=json.loads((render/'full_decode_verification.json').read_text());assert sha(video)==info['sha256'] and info['full_decode_passed']
video_record=dict(version='v59',source_run='v59_realtime_trial01',render_run='v59_review_trial01',host='gpu5070ti',remote_path=str(video),local_path='output/2026-09-27_lite3_versions/v59_realtime_trial01_review.mp4',sha256=sha(video),bytes=video.stat().st_size,full_decode_passed=True,stream=info['ffprobe']['streams'][0],display_measurements=info['display_measurements'],physics_reexecuted=False,raw_frame_manifest_remote=str(render/'frames.jsonl'),raw_frame_manifest_sha256=info['frame_manifest_sha256'],regeneration='On gpu5070ti, from the experiment root: XDG_DATA_HOME='+str(BASE/'runtime/render_env')+' /home/sun/vla_exec/envs/newton_worker/bin/python scripts/run_managed.py --run-id NEW_UNIQUE_REVIEW_ID --deadline 900 -- /home/sun/vla_exec/envs/newton_worker/bin/python versions/v59/render_review.py --source-run v59_realtime_trial01')
(VERSION/'REVIEW_VIDEO.json').write_text(json.dumps(video_record,indent=2)+'\n')
print(json.dumps({'compact_files':len(records),'compact_bytes':sum(x['bytes'] for x in records.values()),'video_bytes':video.stat().st_size,'video_sha256':sha(video)}))

"""Bind a closed physical capture and local-authoritative display sources."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
H=Path(__file__).resolve().parent;B=H.parents[1];T=Path('/data/sun/vla_mppi_20261009')
def sha(p):
 d=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(4*1024**2),b''):d.update(c)
 return d.hexdigest()
def main():
 assert H.is_relative_to(T/'repo')
 tag='v142_candidate_attempt01';source=T/'trials'/tag/'runs'/tag
 outcome=T/'results/recording_v142'/tag/'outcome.json';proof=json.loads((source/'initial_state.json').read_text());assert proof['passed'] and proof['physics_time_s']==0.0 and proof['physics_steps']==0;assert json.loads((source/'video_states.json').read_text())[0]==proof['frame'];m=json.loads(outcome.read_text())['metrics'];assert m['terminal']['backend_terminal_status']=='FINISHED' and not m['fallen'] and m['state_copyback_verified']
 root=T/'video_v143';root.mkdir(exist_ok=False);(root/'runs').mkdir();(root/'cache').mkdir()
 subprocess.run([sys.executable,str(H/'test_overlay.py')],check=True)
 subprocess.run([sys.executable,str(H/'test_timeline.py')],check=True)
 inputs=[source/'initial_state.json',source/'video_states.json',source/'factory_video_states.json',source/'startup_pacing.json',source/'raw_capture.zip',source/'clock_samples.jsonl',source/'backend_states.jsonl',source/'episode_request.json',source/'inputs/stair_scenario.json',outcome,T/'results/recording_v142'/tag/'metrics.json',T/'results/recording_v142'/tag/'latency.csv']
 identity=json.loads((H/'source_identity.json').read_text())
 for n,e in identity['files'].items():assert sha(H/n)==e,n
 contract={'physical_source_root':str(source),'physical_source_run':tag,'analysis_metrics':str(T/'results/recording_v142'/tag/'metrics.json'),'latency_csv':str(T/'results/recording_v142'/tag/'latency.csv'),
  'parent_manifests':{v:sha(B/'versions'/v/'manifest.json') for v in ['v120','v139','v141','v142']},'input_files':{str(p):sha(p) for p in inputs},'display_source_identity_sha256':sha(H/'source_identity.json'),'source_outcome_sha256':sha(outcome),'claim':'Display-only original startup by recorded sim timestamps, then navigation by original wall timestamps, no physics steps. A new recording of unchanged v139 navigation starting at actual native 0.0 s; separate from the six-run acceptance denominator.'}
 (root/'display_contract.json').write_text(json.dumps(contract,indent=2)+'\n');print(json.dumps({'prepared':True,'root':str(root),'source':tag,'inputs':len(inputs),'contract_sha256':sha(root/'display_contract.json')}))
if __name__=='__main__':main()

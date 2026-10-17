"""Reuse the qualified v220 causal display for the actual v231/v230 capture."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,zipfile
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1]
TASK=Path('/data/sun/vla_mppi_20261009/trials/v231_linux_full_attempt01')
SOURCE=TASK/'runs/v231_linux_full_attempt01';ROOT=TASK/'video_v231';OUT=ROOT/'runs/full01'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 resultdir=HERE/'results';metricdir=resultdir/'diagnostic_metrics';outcome=json.loads((resultdir/'outcome.json').read_text());metrics=json.loads((metricdir/'metrics.json').read_text())
 route=json.loads((resultdir/'full_route_verification.json').read_text())
 assert outcome['full_route_gate_passed']==route['passed']
 for p in (ROOT,ROOT/'runs',ROOT/'cache'):p.mkdir(exist_ok=False) if p==ROOT else p.mkdir()
 OUT.mkdir()
 # Restore only actual archived text inputs required by the old path-bound display contract.
 restored=[];archive_manifest=json.loads((SOURCE/'raw_capture_manifest.json').read_text())
 for name in ('clock_samples.jsonl','backend_states.jsonl'):
  p=SOURCE/name
  if not p.exists():
   with zipfile.ZipFile(SOURCE/'raw_capture.zip') as z:data=z.read(name)
   old=archive_manifest['members'][name];assert len(data)==old['bytes'] and hashlib.sha256(data).hexdigest()==old['sha256']
   p.write_bytes(data);restored.append(name)
 (ROOT/'restored_text_inputs.json').write_text(json.dumps(restored,indent=2)+'\n')
 inputs=[resultdir/n for n in ('outcome.json','full_route_verification.json')]+[metricdir/n for n in ('metrics.json','latency.csv')]
 inputs += [SOURCE/n for n in ('video_states.json','factory_video_states.json','initial_state.json','episode_request.json','result.json','inputs/stair_scenario.json','clock_samples.jsonl','backend_states.jsonl','raw_capture.zip')]
 inputs += [BASE/'versions/v231/execution_request.json']
 contract={'physical_source_root':str(SOURCE),'physical_source_run':SOURCE.name,'physical_parent':'v231','native_source':'v230','locomotion':'v216','display_parent':'v220',
 'source_outcome':str(resultdir/'outcome.json'),'route_verification':str(resultdir/'full_route_verification.json'),'analysis_metrics':str(metricdir/'metrics.json'),'latency_csv':str(metricdir/'latency.csv'),
 'parent_manifests':{v:sha(BASE/'versions'/v/'manifest.json') for v in ('v219','v216','v230','v231')},
 'input_files':{str(p):sha(p) for p in inputs},'display_source_identity_sha256':sha(HERE/'source_identity.json'),'source_outcome_sha256':sha(resultdir/'outcome.json'),
 'claim':'Recorded-state display only; all pauses retained, zero new physics. Physical gate='+str(route['passed'])+'; status='+str(outcome['terminal_status'])}
 (ROOT/'display_contract.json').write_text(json.dumps(contract,indent=2)+'\n')
 code=(BASE/'versions/v220/render_capture.py').read_text()
 code=code.replace("data['source_files'].items()","data.get('source_files',data.get('files')).items()")
 code=code.replace("'physical_source_version': 'v219'","'physical_source_version': 'v231'").replace("'native_source_version': 'Nav2 Foxy linux/amd64 SCAN v206; v208 locomotion; v196 direct Twist recorder'","'native_source_version': 'v230 navigation; v216 locomotion; v198 recorder'")
 # The final caption follows the recorded outcome, including a bounded unfinished run.
 caption='arrived (nav2_arrived)' if outcome['terminal_status']=='FINISHED' else ('physical fall (simulation stopped)' if outcome.get('fallen') else ('failed (nav2_failed)' if outcome['terminal_status']=='FAILED' else 'original recording limit; mission not finished'))
 failure=outcome.get('process_failure',{})
 if failure.get('present'):caption='navigation failed: controller SIGABRT (~46.7s); recording continued'
 # Wrap the existing adapter after loading, preserving its complete causal renderer.
 ns={'__file__':str(HERE/'render_run.py'),'__name__':'reused_causal_renderer'};exec(compile(code,str(HERE/'executed_render_adapter.py'),'exec'),ns)
 original=ns['adapt_renderer']
 def adapt(text,source,contract):
  text=original(text,source,contract)
  text=text.replace('version_label = (" | " + episode_request["integration_version"]) if episode_request.get("integration_version") else ""', 'version_label = " | v230 navigation / v231 physics"')
  condition='t >= '+repr(failure['display_marker_physics_s']) if failure.get('present') else 'i == len(rows)-1'
  return text.replace('            caption = (','            if '+condition+': status = '+repr(caption)+'\n            caption = (')
 ns['adapt_renderer']=adapt
 (OUT/'executed_render_adapter.py').write_text(code)
 env=dict(os.environ,NEWTON_RUN_DIR=str(OUT),V220_RENDER_ROOT=str(ROOT),V220_DISPLAY_CONTRACT=str(ROOT/'display_contract.json'),
 WARP_CACHE_PATH=str(ROOT/'cache'),PYOPENGL_PLATFORM='egl',PYGLET_HEADLESS='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
 os.environ.update(env);sys.path.insert(0,str(BASE/'versions/v220'));sys.argv=[str(HERE/'render_run.py')]
 ns['main']()
 # Reuse the original frame-by-frame display validator, changing identity and terminal label only.
 checker=(BASE/'versions/v220/verify_video.py').read_text().replace("TASK = Path('/data/sun/vla_mppi_20261009/trials/v219_linux_full_attempt01')",'TASK = Path('+repr(str(TASK))+')').replace('video_v220','video_v231')
 checker=checker.replace("assert outcome['terminal_status'] in ('FINISHED','FAILED') or outcome.get('fallen') is True","assert outcome['terminal_status'] in ('FINISHED','FAILED','BOUNDED_END','PHYSICAL_FALL')")
 checker=checker.replace("assert (metrics.get('terminal') or {}).get('backend_terminal_status') == outcome['terminal_status']","assert (metrics.get('terminal') or {}).get('backend_terminal_status') == outcome.get('recorded_backend_terminal_status')")
 checker=checker.replace("assert result['integration_version'] == 'v219'","assert result['integration_version'] == 'v231'")
 checker=checker.replace("    assert frames[-1]['navigation_status'] == expected_status","    expected_status = "+repr(caption)+"\n    assert frames[-1]['navigation_status'] == expected_status")
 checker=checker.replace("'physical_source_version': 'v219'","'physical_source_version': 'v231'").replace("'display_version': 'v220'","'display_version': 'v231_audit'")
 checker=checker.replace('Original-start v219_linux_full_attempt01','Original-start v231_linux_full_attempt01').replace('original-start v219_linux_full_attempt01','original-start v231_linux_full_attempt01')
 (OUT/'executed_video_checker.py').write_text(checker)
 scope={'__file__':str(OUT/'executed_video_checker.py'),'__name__':'video_checker'};exec(compile(checker,str(OUT/'executed_video_checker.py'),'exec'),scope);scope['main']()
 delivered=HERE/'delivered';delivered.mkdir(exist_ok=True);shutil.copyfile(OUT/'newton_stair_recorded.mp4',delivered/'v230_full_attempt01.mp4')
if __name__=='__main__':main()

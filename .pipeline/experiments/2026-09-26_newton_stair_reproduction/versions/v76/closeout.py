"""Archive the closed corner recording, then render and retain its real video."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1];ROOT=BASE.parents[2]
PYTHON=BASE.parent/'2026-09-26_newton_macos_policy/runtime/.venv/bin/python'
PLOT_PYTHON=Path('/Users/sun/.openviking-venv/bin/python')
REMOTE='/home/sun/vla_artifacts/2026-10-04_corner_start'


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda:stream.read(1024*1024),b''):h.update(data)
    return h.hexdigest()


def archive(root,evidence,case):
    assert json.loads((root/'retention_result.json').read_text())['status']=='completed'
    process=json.loads((root/'process.json').read_text());assert 'exit_code' in process
    files={str(p.relative_to(root)):{'bytes':p.stat().st_size,'sha256':sha(p)}
        for p in root.rglob('*') if p.is_file()}
    assert not any(p.is_symlink() for p in root.rglob('*'))
    destination=REMOTE+'/'+case
    listing=evidence/(case+'_transfer.txt');listing.write_text(''.join(x+'\n' for x in sorted(files)))
    manifest={'local_temporary_root':str(root),'remote_root':destination,'files':files,
        'bytes':sum(v['bytes'] for v in files.values()),'gpu_job_started':False}
    receipt=evidence/(case+'_storage.json');receipt.write_text(json.dumps(manifest,indent=2)+'\n')
    subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','gpu5070ti',
        'mkdir -p '+destination],check=True,timeout=25)
    subprocess.run(['rsync','-a','--files-from='+str(listing),'-e','ssh -o BatchMode=yes -o ConnectTimeout=10',
        str(root)+'/', 'gpu5070ti:'+destination+'/'],check=True,timeout=240)
    subprocess.run(['scp','-q',str(receipt),'gpu5070ti:'+destination+'/storage_manifest.json'],check=True,timeout=25)
    code='''from pathlib import Path
import json,hashlib,sys,time
m=json.loads(Path(sys.argv[1]).read_text());count=0
for name,row in m['files'].items():
 p=Path(m['remote_root'])/name
 assert p.stat().st_size==row['bytes'],str(p)
 h=hashlib.sha256()
 with p.open('rb') as f:
  for data in iter(lambda:f.read(1024*1024),b''):h.update(data)
 assert h.hexdigest()==row['sha256'],str(p)
 count+=1
print(json.dumps({'passed':True,'files':count,'bytes':m['bytes'],'verified_epoch_s':time.time(),'gpu_job_started':False}))
'''
    checked=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','gpu5070ti',
        'python3 - '+destination+'/storage_manifest.json'],input=code,capture_output=True,text=True,check=True,timeout=60)
    verification=json.loads(checked.stdout);assert verification['files']==len(files)
    (evidence/(case+'_remote_verification.json')).write_text(json.dumps(verification,indent=2)+'\n')
    return manifest


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-root',type=Path,required=True)
    p.add_argument('--evidence',type=Path,required=True);args=p.parse_args()
    root=args.run_root.resolve();evidence=args.evidence.resolve();evidence.mkdir(exist_ok=True)
    # Save the unique physical evidence before display work, including failures.
    stored=archive(root,evidence,root.name)
    if not (root/'result.json').exists():
        raise ValueError('Incomplete physical capture archived; do not synthesize a final result')
    analysis=evidence/'analysis'
    env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',MPLCONFIGDIR=str(root.parent.parent/'plot_cache'))
    subprocess.run([str(PLOT_PYTHON),str(BASE/'audits/2026-10-04_mac_newton/analyze.py'),
        '--run-root',str(root),'--output',str(analysis)],env=env,check=True,timeout=90)
    metrics=analysis/'metrics.json';provenance=analysis/'provenance.json'
    inputs=[root/n for n in ('video_states.json','episode_request.json','result.json','raw_capture.zip',
        'raw_capture_manifest.json','inputs/stair_scenario.json')]+[metrics,provenance]
    contract={'version':'v76','kind':'display_only','physical_source_version':'v76','native_source_version':'v63',
        'physical_source_run':root.name,'physical_source_root':str(root),'analysis_metrics':str(metrics),
        'parent_manifests':{v:sha(BASE/'versions'/v/'manifest.json') for v in ('v51','v61','v76')},
        'input_files':{str(x):sha(x) for x in inputs},'physics_reexecuted':False,'display_fps':30,
        'claim':'Fresh corner-local current-planner episode; no preceding-route replay or historical warm-state restoration.'}
    contract_path=evidence/'display_contract.json';contract_path.write_text(json.dumps(contract,indent=2)+'\n')
    render_root=Path(tempfile.mkdtemp(prefix='vla_newton_v76_render_',dir='/private/tmp'))
    render_run=root.name+'_review'
    env.update(V76_RENDER_ROOT=str(render_root),V76_DISPLAY_CONTRACT=str(contract_path))
    subprocess.run([str(PYTHON),str(HERE/'run_review.py'),'--run-id',render_run,'--deadline','900',
        '--retention','archive','--',str(PYTHON),str(HERE/'render_capture.py')],env=env,check=True,timeout=940)
    rendered=render_root/'runs'/render_run
    video_result=json.loads((rendered/'result.json').read_text())
    assert video_result['render_only_no_physics_steps']
    assert json.loads((rendered/'video_verification.json').read_text())['status']=='passed'
    output=ROOT/'output/2026-09-27_lite3_versions'/(root.name+'_review.mp4')
    assert not output.exists();shutil.copyfile(rendered/'newton_stair_recorded.mp4',output)
    assert sha(output)==video_result['video_sha256']
    review=evidence/'review';review.mkdir()
    for name in ('result.json','process.json','request.json','video_verification.json','frames.json',
                 'host_port_verification.json','display_measurements.json'):
        if (rendered/name).exists():shutil.copyfile(rendered/name,review/name)
    shutil.copytree(rendered/'frame_samples',review/'frame_samples')
    archive(rendered,evidence,render_run)
    result={'passed':True,'physical_record_archived':True,'video_archived':True,'local_video':str(output),
        'sha256':sha(output),'bytes':output.stat().st_size,'source_run':root.name,
        'render_only_no_physics_steps':True,'raw_remote_root':stored['remote_root'],
        'visual_review_pending':True,'physics_goal_acceptance':False}
    (evidence/'video_closeout.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()

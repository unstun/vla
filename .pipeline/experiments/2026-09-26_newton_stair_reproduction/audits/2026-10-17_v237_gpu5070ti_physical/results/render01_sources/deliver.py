"""Return compact truthful result/video evidence, excluding raw and build data."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

HERE=Path(__file__).resolve().parent
PREFIX=Path('/data/sun/vla_mppi_20261009')
RAW=PREFIX/'trials/v237_linux_full_attempt01/runs/v237_linux_full_attempt01'
RENDER=RAW.parents[1]/'video_v237/runs/full01'
OUT=HERE/'results'

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(4*2**20),b''):h.update(block)
    return h.hexdigest()

def main():
    outcome=json.loads((OUT/'outcome.json').read_text())
    ledger=json.loads((PREFIX/'evidence/v237_physical_launch_once.json').read_text())
    assert ledger['authorized_attempts']==1
    retention=json.loads((OUT/'capture_snapshot.json').read_text())
    assert retention['passed'] and sha(Path(retention['archive']))==retention['archive_sha256']
    displayed=json.loads((RENDER/'result.json').read_text())
    assert displayed['render_only_no_physics_steps'] and displayed['integration_version']=='v237'
    for n in ('video_verification.json','display_contract.json'):
        shutil.copyfile(RENDER/n,OUT/n)
    verify=json.loads((OUT/'video_verification.json').read_text());assert verify['full_decode_passed']
    for n in ('full_physics_comparison','stairs_physics_45_55'):
        proof=json.loads((OUT/(n+'_verification.json')).read_text())
        assert proof['passed'] and proof['full_decode_passed']
        assert sha(HERE/'delivered'/(n+'.mp4'))==proof['video_sha256']
    logdir=OUT/'preparation_logs';logdir.mkdir(exist_ok=True)
    for p in (PREFIX/'evidence').glob('v237_*'):
        if p.is_file() and p.suffix in ('.log','.json'):shutil.copyfile(p,logdir/p.name)
    shutil.copyfile(RAW/'run.log',logdir/'physical_run.log')
    receipts=OUT/'execution_receipts'
    manifest=json.loads((RAW/'raw_capture_manifest.json').read_text()) if (RAW/'raw_capture_manifest.json').exists() else None
    stateproof=dict(passed=True,physics_attempts=1,full_route_passed=outcome['full_route_gate_passed'],
        original_result_present=(RAW/'result.json').exists(),render_physics_steps=0,
        archive=retention['archive'],archive_sha256=retention['archive_sha256'])
    (OUT/'delivery_status.json').write_text(json.dumps(stateproof,indent=2)+'\n')
    review=OUT/'visual_review';review.mkdir(exist_ok=True)
    video=next(p for p in (HERE/'delivered').glob('v237_*attempt01.mp4'))
    frames=json.loads((RENDER/'frames.json').read_text())
    for n,path,t in [('initial.png',video,0),('tail.png',video,(len(frames)-1)/30),('stairs_48s.png',HERE/'delivered/stairs_physics_45_55.mp4',3)]:
        subprocess.run(['ffmpeg','-v','error','-ss',str(t),'-i',str(path),'-frames:v','1',str(review/n)],check=True)
    files=[p for root in (OUT,HERE/'delivered') for p in root.rglob('*') if p.is_file() and p.name not in ('return_manifest.json','postprocess_steps.json')]
    assert not any(p.suffix in ('.zip','.npz','.o','.a','.so','.pyc') or 'CMakeFiles' in p.parts for p in files)
    total=sum(p.stat().st_size for p in files);assert total<150*2**20
    report=dict(passed=True,files={str(p.relative_to(HERE)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(files)},
        physics_attempts=1,full_route_passed=outcome['full_route_gate_passed'],total_bytes=total)
    (OUT/'return_manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(files=len(files),bytes=total,full_route_passed=report['full_route_passed'])),flush=True)

if __name__=='__main__':main()

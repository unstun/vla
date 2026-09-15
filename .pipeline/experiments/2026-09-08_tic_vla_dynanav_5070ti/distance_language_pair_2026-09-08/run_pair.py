"""Detached sequential execution of the predeclared metric-language pair."""
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


def main():
    plan = json.loads((ROOT/'pair_plan.json').read_text())
    state_path = ROOT/'pair_execution.json'
    if state_path.exists():
        raise RuntimeError('This pair was already dispatched; inspect its state before retrying')
    state = {'started_unix':time.time(),'done':False,'cases':[]}
    save(state_path,state)
    # Check all pinned model assets before either case.
    assets=json.loads((ROOT.parent/'manifests/official_assets.json').read_text())
    paths=[(ROOT.parent/'models/InternVL3-1B'/e['path'],e['sha256']) for e in assets['base_model']['files']]
    paths.append((ROOT.parent/'checkpoints/TIC-VLA-model.ckpt',assets['checkpoint']['sha256']))
    checks=[]
    for path, expected in paths:
        digest=hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda:stream.read(8*1024*1024),b''):
                digest.update(block)
        if digest.hexdigest()!=expected:
            raise RuntimeError(f'Model asset mismatch: {path}')
        checks.append({'path':str(path),'sha256':expected})
    save(ROOT/'asset_integrity.json',{'passed':True,'checks':checks})
    for case in plan['cases']:
        entry={**case,'started_unix':time.time()}
        state['cases'].append(entry);save(state_path,state)
        subprocess.run([sys.executable,str(ROOT/'scripts/batch_worker.py'),case['run_id'],'top_down'],
                       check=True,timeout=830)
        run=ROOT/'runs'/case['run_id']
        delivery=json.loads((ROOT/'runs'/f"{case['run_id']}.delivery.json").read_text())
        if not delivery.get('success'):
            raise RuntimeError(f'Packaging failed: {delivery}')
        meta=json.loads((run/'meta.json').read_text())
        analysis=json.loads((run/'analysis.json').read_text())
        episode=analysis['episode']
        valid=meta['exit_code']==0 and not meta['timed_out'] and not episode.get('error') and episode.get('duration_frames')==1020
        entry.update(finished_unix=time.time(),runtime_complete=valid,model_calls=analysis['model_calls'])
        save(state_path,state)
        if not valid:
            raise RuntimeError(f'Incomplete episode: {case["run_id"]}')
    state.update(done=True,finished_unix=time.time())
    save(state_path,state)
    print(json.dumps(state,ensure_ascii=False),flush=True)


if __name__=='__main__':
    main()

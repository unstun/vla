"""Acquire pinned public weights with resumable curl and upstream LFS checks."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import quote

root = Path(sys.argv[1]).resolve()
repo = 'InternRobotics/InternVLA-N1-DualVLN'
revision = 'a698a9e898b4001621a319e1bc89f02ec715cc86'
tree = json.loads((root/'setup/upstream_model_tree.json').read_text())
jobs = [(repo, revision, item, root/'models/InternVLA-N1-DualVLN'/item['path'])
        for item in tree if item['type'] == 'file']
encoder = json.loads((root/'setup/encoder_source.json').read_text())
jobs.append((encoder['repo'], encoder['revision'], encoder['file'],
             root/'models'/encoder['file']['path']))

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(8*1024*1024), b''): h.update(b)
    return h.hexdigest()

def acquire(job):
    model_repo, model_revision, item, target = job
    target.parent.mkdir(parents=True, exist_ok=True)
    expected = item.get('lfs', {}).get('oid')
    part = target.with_name(target.name+'.part')
    started = time.time()
    if not target.exists():
        url = f'https://huggingface.co/{model_repo}/resolve/{model_revision}/{quote(item["path"])}'
        print(json.dumps({'event':'download_start','file':str(target),'bytes':item['size']}), flush=True)
        for attempt in range(4):
            result = subprocess.run(['curl','--fail','--location','--silent','--show-error',
                '--connect-timeout','20','--max-time','900','--speed-time','45',
                '--speed-limit','1024','--continue-at','-','--output',str(part),url],
                capture_output=True, text=True, timeout=930)
            if result.returncode == 0:
                if part.stat().st_size != item['size']:
                    raise RuntimeError(f'Size mismatch for {item["path"]}')
                sha = digest(part)
                if expected and sha != expected: raise RuntimeError(f'LFS mismatch: {target}')
                part.replace(target)
                break
            print(json.dumps({'event':'retry','file':item['path'],'attempt':attempt+1,
                              'stderr':result.stderr[-1000:]}), flush=True)
        else: raise RuntimeError(f'Download retries exhausted: {target}')
    if target.stat().st_size != item['size']: raise RuntimeError(f'Size mismatch: {target}')
    sha = digest(target)
    if expected and sha != expected: raise RuntimeError(f'LFS mismatch: {target}')
    row = {'path':str(target.relative_to(root)),'repo':model_repo,'revision':model_revision,
           'bytes':target.stat().st_size,'sha256':sha,'upstream_lfs_sha256':expected}
    print(json.dumps({'event':'verified','file':item['path'],'seconds':time.time()-started}),flush=True)
    return row

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    files = list(pool.map(acquire,jobs))
(root/'setup/original_weight_manifest.json').write_text(json.dumps({'files':files},indent=2)+'\n')
print('DOWNLOAD_AND_HASH_VERIFICATION_COMPLETE',flush=True)

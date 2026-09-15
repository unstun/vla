"""Resumable ranged public-HF download with range, length and LFS hash checks."""
import concurrent.futures
import hashlib
import json
import os
import re
from pathlib import Path
import sys
import subprocess
import threading
import time
import urllib.request

root = Path(sys.argv[1]).resolve()
repo = 'a8cheng/navila-llama3-8b-8f'
revision = 'b2294e96581454468d6b94f38201f4f965ef48b7'
target = root/'models/navila-llama3-8b-8f'
setup = root/'setup'
parts = root/'download_parts'
parts.mkdir(exist_ok=True)
tree = json.loads((setup/'upstream_model_tree.json').read_text())
lock = threading.Lock()
completed = 0
start_time = time.monotonic()
jobs = []
chunk_size = 32*1024*1024
for item in tree:
    if item['type']!='file': continue
    dest = target/item['path']
    if dest.is_file() and dest.stat().st_size==item['size']:
        continue
    for offset in range(0,item['size'],chunk_size):
        jobs.append((item,offset,min(offset+chunk_size,item['size'])-1))

def get_part(job):
    global completed
    item,first,last = job
    key = hashlib.sha256(item['path'].encode()).hexdigest()[:16]
    dest = parts/f'{key}_{first}'
    expected = last-first+1
    if not dest.is_file() or dest.stat().st_size!=expected:
        for attempt in range(5):
            try:
                url = f"https://huggingface.co/{repo}/resolve/{revision}/{item['path']}?download=true&segment={first}&attempt={time.time_ns()}"
                headers = dest.with_suffix('.headers')
                subprocess.run(['curl','-fsSL','--connect-timeout','15','--max-time','90',
                    '--speed-limit','1024','--speed-time','20','-H',f'Range: bytes={first}-{last}',
                    '-D',str(headers),'-o',str(dest.with_suffix('.partial')),url],
                    check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=100)
                header_text=headers.read_text()
                ranges=re.findall(r'(?im)^content-range:\s*([^\r\n]+)',header_text)
                if ranges:
                    assert ranges[-1]==f"bytes {first}-{last}/{item['size']}",ranges[-1]
                elif first!=0 or expected!=item['size']:
                    raise RuntimeError('Server did not honor requested range')
                count=dest.with_suffix('.partial').stat().st_size
                if count!=expected:raise RuntimeError(f'Truncated range: {count}/{expected}')
                headers.unlink()
                dest.with_suffix('.partial').replace(dest)
                break
            except Exception as exc:
                if attempt==4:raise RuntimeError(f"Download failed: {item['path']} offset {first}") from exc
                time.sleep(min(2**attempt,8))
    with lock:
        completed+=expected
        print(json.dumps({'completed_MiB':round(completed/2**20,1),
          'MiB_per_s':round(completed/2**20/(time.monotonic()-start_time),2),
          'file':item['path'],'offset':first}),flush=True)

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    list(pool.map(get_part,jobs))
manifest=[]
for item in tree:
    if item['type']!='file':continue
    dest=target/item['path'];dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.is_file() or dest.stat().st_size!=item['size']:
        key=hashlib.sha256(item['path'].encode()).hexdigest()[:16]
        with dest.with_suffix(dest.suffix+'.assembling').open('wb') as stream:
            for offset in range(0,item['size'],chunk_size):
                with (parts/f'{key}_{offset}').open('rb') as source:
                    while block:=source.read(8*1024*1024):stream.write(block)
        dest.with_suffix(dest.suffix+'.assembling').replace(dest)
    h=hashlib.sha256()
    with dest.open('rb') as stream:
        while block:=stream.read(8*1024*1024):h.update(block)
    sha=h.hexdigest();expected=item.get('lfs',{}).get('oid')
    assert dest.stat().st_size==item['size']
    assert not expected or sha==expected, f"LFS SHA-256 mismatch: {item['path']}"
    manifest.append({'path':item['path'],'size':item['size'],'sha256':sha,
                     'upstream_lfs_sha256':expected})
(setup/'original_weight_manifest.json').write_text(json.dumps(
 {'repo':repo,'revision':revision,'files':manifest},indent=2))
print('DOWNLOAD_AND_HASH_VERIFICATION_COMPLETE',flush=True)

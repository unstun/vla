"""Send small task files using bounded SSH writes on the unstable direct link."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

root=Path(__file__).resolve().parents[1]
remote='/home/sun/vla_exec/2026-09-08_navila_8b_quantized_5070ti'
paths=[]
for directory in ['scripts','fixtures']:
    paths += [p for p in (root/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [root/'setup'/name for name in ['package_manifest.json','work_source_manifest.json','compatibility.patch']]
ssh=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ServerAliveInterval=10',
     '-o','ServerAliveCountMax=3','gpu5070ti']

def call(code,payload=b''):
    for attempt in range(4):
        try:
            result=subprocess.run(ssh+[shlex.join(['python3','-c',code])],input=payload,
                                  capture_output=True,timeout=45)
            if result.returncode==0:return result.stdout
        except subprocess.TimeoutExpired:pass
    raise RuntimeError('Bounded SSH transfer failed after four attempts')

def send(path):
    data=path.read_bytes();sha=hashlib.sha256(data).hexdigest()
    name=path.relative_to(root).as_posix();dest=remote+'/'+name
    code=f"from pathlib import Path; import hashlib; p=Path({dest!r}); print(hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else '')"
    if call(code).decode().strip()==sha:return name+' unchanged'
    partial=dest+'.uploading'
    # Every part acknowledges its content digest. Partial files are task-owned.
    for offset in range(0,len(data),64*1024):
        block=data[offset:offset+64*1024]
        code=(f"from pathlib import Path; import sys,hashlib; p=Path({partial!r}); p.parent.mkdir(parents=True,exist_ok=True); "
              "b=sys.stdin.buffer.read(); f=p.open('r+b' if p.exists() else 'w+b'); "
              f"f.seek({offset}); f.write(b); f.close(); print(hashlib.sha256(b).hexdigest())")
        assert call(code,block).decode().strip()==hashlib.sha256(block).hexdigest()
    code=(f"from pathlib import Path; import hashlib; p=Path({partial!r}); "
          f"f=p.open('r+b'); f.truncate({len(data)}); f.close(); "
          f"assert hashlib.sha256(p.read_bytes()).hexdigest()=={sha!r}; p.replace({dest!r}); print('verified')")
    assert call(code).decode().strip()=='verified'
    return name+' verified'

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    for result in pool.map(send,paths):print(result,flush=True)
print('PACKAGE_SYNC_COMPLETE',flush=True)

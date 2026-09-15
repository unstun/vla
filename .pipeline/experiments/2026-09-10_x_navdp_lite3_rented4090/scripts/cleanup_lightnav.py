"""Remove explicitly selected LightNav deployment folders while proving evidence retention."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import time

ALLOWED = {'2026-09-09_lightnav0_official_demo_rented4090','2026-09-09_lightnav0_5070ti_inference'}
RUNTIME_NAMES = {'work','checkpoints','env','venv','models','tools','.venv'}

def retained(root):
    result={}
    for directory,children,files in os.walk(root,followlinks=False):
        current=Path(directory)
        if current==root:children[:]=[p for p in children if p not in RUNTIME_NAMES]
        for name in sorted(files):
            path=current/name;relative=str(path.relative_to(root))
            if path.is_symlink():result[relative]={'symlink':os.readlink(path)}
            else:
                hasher=hashlib.sha256()
                with path.open('rb') as stream:
                    for block in iter(lambda:stream.read(4*1024*1024),b''):hasher.update(block)
                digest=hasher.hexdigest()
                result[relative]={'bytes':path.stat().st_size,'sha256':digest}
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--delete',action='store_true')
    args=parser.parse_args();root=args.root.resolve()
    if root.name not in ALLOWED or not root.is_dir():raise RuntimeError('Root is not an approved LightNav experiment')
    targets=[root/n for n in sorted(RUNTIME_NAMES) if (root/n).exists()]
    inventory=[]
    for path in targets:
        if path.is_symlink():raise RuntimeError(f'Refusing to follow runtime-directory symlink: {path}')
        files=[f for f in path.rglob('*') if f.is_file() and not f.is_symlink()]
        inventory.append({'path':str(path),'files':len(files),'logical_bytes':sum(f.stat().st_size for f in files)})
    report={'hostname':socket.gethostname(),'root':str(root),'targets':inventory,'requested_delete':args.delete,
            'started_unix':time.time(),'authorization':'Dr Sun: Remove model/runtime copies; keep evidence'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
    if not args.delete:return
    # Only actual model/demo processes matter; the cleanup process uses the new experiment.
    if Path('/proc').exists():
        for entry in Path('/proc').iterdir():
            if not entry.name.isdigit() or int(entry.name)==os.getpid():continue
            try:command=(entry/'cmdline').read_bytes().replace(b'\x00',b' ').decode(errors='replace')
            except (FileNotFoundError,PermissionError,ProcessLookupError):continue
            if str(root) in command and any(term in command for term in ['lightnav.serving','vln_mujoco','lightnav-predict']):
                raise RuntimeError(f'LightNav process still active: {entry.name}')
    before=retained(root)
    evidence_file=args.output.with_name(args.output.stem+'_retained.json')
    evidence_file.write_text(json.dumps(before,indent=2)+'\n')
    for path in targets:shutil.rmtree(path)
    after=retained(root)
    if before!=after:raise RuntimeError('Evidence changed during runtime cleanup')
    report.update(completed=True,retained_files=len(after),deleted_paths=[str(p) for p in targets],
                  retained_manifest_sha256=hashlib.sha256(evidence_file.read_bytes()).hexdigest(),
                  finished_unix=time.time())
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)

if __name__=='__main__':main()

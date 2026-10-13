"""Bounded existing experiment command followed by closed-output retention."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import artifacts as a


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--deadline',type=float,default=180)
    parser.add_argument('--retention',choices=['compatible','archive'],default='compatible')
    parser.add_argument('--min-free-gib',type=float,default=4)
    parser.add_argument('--keep-frames',action='store_true',help='Explicit debug retention for legacy PNG renderers')
    parser.add_argument('command',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    command=args.command[1:] if args.command[:1]==['--'] else args.command
    if not command or not re.fullmatch(r'[A-Za-z0-9_-]+',args.run_id):raise ValueError('Expected a run ID and command')
    run=a.BASE/'runs'/args.run_id
    if run.exists():raise FileExistsError(run)
    if args.min_free_gib<0 or shutil.disk_usage(a.BASE).free<args.min_free_gib*1024**3:
        raise RuntimeError('Insufficient disk reserve; no run launched')
    active=a.AUDIT/'active';active.mkdir(parents=True,exist_ok=True)
    marker=active/args.run_id
    with marker.open('x') as f:json.dump(dict(pid=os.getpid(),command=command),f)
    supervisor=[sys.executable,str(a.BASE/'scripts/run_bounded.py'),'--run-id',args.run_id,'--deadline',str(args.deadline),'--',*command]
    completed=False
    try:
        process=subprocess.Popen(supervisor)
        code=process.wait()
        completed=True
    finally:
        # A killed/interrupted manager leaves a marker for explicit inspection.
        # It must never compact a child whose termination has not been observed.
        if completed:marker.unlink()
    retention=dict(source_version='v51',process_exit_code=code,requested_policy=args.retention,operations=[])
    if not (run/'result.json').is_file():
        retention.update(status='retained_incomplete',reason='No completion result; preserve partial evidence')
    else:
        try:
            a.closed_run(run)
            encoding=json.loads((run/'video_encoding.json').read_text()) if (run/'video_encoding.json').exists() else {}
            if (run/'frames').exists() and not args.keep_frames and not encoding.get('keep_frames'):
                retention['operations'].append(a.prune_frames(run,True))
            payloads=[p for p in run.rglob('*') if p.is_file() and (p.suffix=='.npz' or p.suffix in ('.jsonl','.log') and p.stat().st_size>=4*1024*1024)]
            if args.retention=='archive' or sys.platform!='darwin':
                if payloads:
                    receipt=a.pack_raw(run)
                    retention['operations'].append(dict(kind='pack_raw',members=len(receipt['members']),archive_bytes=receipt['archive_bytes']))
            else:
                for p in payloads:
                    if p.suffix in ('.jsonl','.log'):retention['operations'].append(a.compress_log(p))
            retention['status']='completed'
        except Exception as error:
            retention.update(status='retention_failed_originals_or_verified_archive_preserved',error=repr(error))
    a.atomic_json(run/'retention_result.json',retention)
    print(json.dumps(retention),flush=True)
    return code if code else (0 if retention['status']=='completed' else 2)


if __name__=='__main__':raise SystemExit(main())

"""Verify frozen delivery locally plus retained remote metadata, optionally restore."""
from pathlib import Path
import argparse, hashlib, json, shlex, subprocess

here=Path(__file__).resolve().parent
repo=next(p for p in here.parents if (p/'.git').is_dir())
record=json.loads((here/'retention.json').read_text())
parser=argparse.ArgumentParser();parser.add_argument('--restore',action='store_true');args=parser.parse_args()
missing={}
for version in record['counts']:
    folder=repo/'.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions'/version
    manifest=json.loads((folder/'manifest.json').read_text())
    for relative, expected in manifest['files'].items():
        path=folder/relative
        if path.is_file():
            assert hashlib.sha256(path.read_bytes()).hexdigest()==expected, str(path)
        else:
            key=str(path.relative_to(repo));entry=record['files'][key]
            assert entry['sha256']==expected
            missing[key]=entry
script="import json,hashlib,pathlib; q=json.load(__import__('sys').stdin); " + \
       "assert all(hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==h for p,h in q.items()); print(len(q))"
request={entry['remote_path']:entry['sha256'] for entry in missing.values()}
result=subprocess.run(['ssh',record['host'],'python3 -c '+shlex.quote(script)],input=json.dumps(request),text=True,capture_output=True,check=True)
assert int(result.stdout.strip())==len(missing)
if args.restore:
    for key,entry in missing.items():
        target=repo/key;target.parent.mkdir(parents=True,exist_ok=True)
        subprocess.run(['rsync','-az',record['host']+':'+entry['remote_path'],str(target)],check=True)
        assert hashlib.sha256(target.read_bytes()).hexdigest()==entry['sha256'],key
print(json.dumps({'local_frozen_bytes':'verified','remote_retained_files_verified':len(missing),'restored':args.restore}))

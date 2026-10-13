"""Restore only receipt-listed files from the verified storage archive."""
from pathlib import Path
import argparse, hashlib, json, shlex, subprocess, tarfile, tempfile

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
archive = '/home/sun/vla_artifacts/2026-10-08_nav2_sim_repair/attempt01/vla_nav2_sim_repair_v100_v114.tar.gz'
expected = 'd2613a0720606c1c999a1ab858ed4ae71c1fb22ff746e9007b17e5f1ca77c806'
remote = r'''
import sys,json,tarfile,hashlib
archive,expected=sys.argv[1:]
with open(archive,'rb') as f: assert hashlib.file_digest(f,'sha256').hexdigest()==expected
names=set(json.load(sys.stdin));prefix='vla_nav2_simrepair_5z7q27y7/'
with tarfile.open(archive,'r|gz') as source,tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as out:
 for item in source:
  if item.name.startswith(prefix) and item.name[len(prefix):] in names:
   item.name=item.name[len(prefix):]
   item.pax_headers.pop('path',None)
   out.addfile(item,source.extractfile(item) if item.isfile() else None)
  elif item.name=='member_manifest.json': out.addfile(item,source.extractfile(item))
'''
parser=argparse.ArgumentParser();parser.add_argument('--existing',type=Path)
args=parser.parse_args()
root=args.existing or Path(tempfile.mkdtemp(prefix='vla_nav2_simrepair_mppi_',dir='/private/tmp'))
bundle=root/'restored_files.tar.gz'
command=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','gpu5070ti',
         'python3 -c '+shlex.quote(remote)+' '+shlex.quote(archive)+' '+shlex.quote(expected)]
if not args.existing:
    with bundle.open('wb') as output:
        subprocess.run(command,input=(HERE/'restore_wanted.json').read_bytes(),stdout=output,check=True,timeout=300)
with tarfile.open(bundle) as stream:
    for member in stream.getmembers():
        member.name=member.name.removeprefix('vla_nav2_simrepair_5z7q27y7/')
        stream.extract(member,root,filter='data')
receipt=json.loads((BASE/'versions/v114/runtime_receipt.json').read_text())
for path,value in receipt['runtime_file_sha256'].items():
    actual=root/path.removeprefix('/task/')
    assert hashlib.sha256(actual.read_bytes()).hexdigest()==value,path
assert hashlib.sha256((root/'packages.tsv').read_bytes()).hexdigest()==receipt['package_receipt_sha256']
manifest=root/'member_manifest.json'
assert hashlib.sha256(manifest.read_bytes()).hexdigest()=='4471fef9475948aad50a121971360f31952502713d43ea2164b4e4f7c6830273'
result=dict(workspace=str(root),original_archive=archive,original_sha256=expected,
            runtime_files_verified=len(receipt['runtime_file_sha256']),
            restored_bundle_bytes=bundle.stat().st_size,storage_only=True)
(HERE/'runtime_restore.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)

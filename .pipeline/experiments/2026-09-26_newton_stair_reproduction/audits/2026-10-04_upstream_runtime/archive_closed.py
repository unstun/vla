"""Storage-only upload and byte verification of closed Mac test recordings."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib
import json
import subprocess

HERE=Path(__file__).resolve().parent
REMOTE='/home/sun/vla_artifacts/2026-10-04_upstream_runtime'
CASES={
    'v71_failed_launch':Path('/private/tmp/vla_newton_v71_jo0njn_s/runs/v71_mac_trial01_attempt01'),
    'v72_mac_trial01_attempt01':Path('/private/tmp/vla_newton_v72_197pzky4/runs/v72_mac_trial01_attempt01'),
    'v73_review_attempt01':Path('/private/tmp/vla_newton_v73_HlsjSP/runs/v72_upstream_review_v73'),
    'v73_review_attempt02':Path('/private/tmp/vla_newton_v73_0nDvSl/runs/v72_upstream_review_v73_attempt02'),
    'v73_review_attempt03':Path('/private/tmp/vla_newton_v73_8iyR3t/runs/v72_upstream_review_v73_attempt03'),
}


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda:f.read(1024*1024),b''):h.update(data)
    return h.hexdigest()


def main():
    manifest={'kind':'closed_capture_storage_only','host':'gpu5070ti','remote_root':REMOTE,
        'gpu_job_started':False,'created_utc':datetime.now(timezone.utc).isoformat(),'cases':{}}
    for case,root in CASES.items():
        assert root.is_dir() and root.parent.name=='runs' and root.parent.parent.parent==Path('/private/tmp')
        assert not any(p.is_symlink() for p in root.rglob('*'))
        files={str(p.relative_to(root)):{'sha256':sha(p),'bytes':p.stat().st_size}
            for p in root.rglob('*') if p.is_file()}
        manifest['cases'][case]={'local_temporary_root':str(root),'remote_root':REMOTE+'/'+case,
            'files':files,'bytes':sum(x['bytes'] for x in files.values()),
            'closed_process_receipt_present':(root/'process.json').is_file(),
            'preserved_launch_failure':case in ('v71_failed_launch','v73_review_attempt01','v73_review_attempt02')}
    manifest['total_bytes']=sum(x['bytes'] for x in manifest['cases'].values())
    manifest['total_files']=sum(len(x['files']) for x in manifest['cases'].values())
    path=HERE/'raw_archive_transfer.json';path.write_text(json.dumps(manifest,indent=2)+'\n')
    for case,item in manifest['cases'].items():
        subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','gpu5070ti',
            'mkdir -p '+item['remote_root']],check=True,timeout=25)
        listing=HERE/('transfer_'+case+'.txt')
        listing.write_text(''.join(name+'\n' for name in sorted(item['files'])))
        subprocess.run(['rsync','-a','--files-from='+str(listing),
            '-e','ssh -o BatchMode=yes -o ConnectTimeout=10',
            item['local_temporary_root']+'/', 'gpu5070ti:'+item['remote_root']+'/'],check=True,timeout=180)
    subprocess.run(['scp','-q',str(path),'gpu5070ti:'+REMOTE+'/raw_archive_transfer.json'],check=True,timeout=30)
    script='''from pathlib import Path
import hashlib,json,time
p=Path("/home/sun/vla_artifacts/2026-10-04_upstream_runtime/raw_archive_transfer.json")
m=json.loads(p.read_text());checked=0;size=0
for case,item in m['cases'].items():
 for name,expected in item['files'].items():
  f=Path(item['remote_root'])/name
  assert f.is_file() and f.stat().st_size==expected['bytes'],str(f)
  h=hashlib.sha256()
  with f.open('rb') as stream:
   for data in iter(lambda:stream.read(1024*1024),b''):h.update(data)
  assert h.hexdigest()==expected['sha256'],str(f)
  checked+=1;size+=f.stat().st_size
print(json.dumps({'passed':True,'files':checked,'bytes':size,'verified_epoch_s':time.time(),
 'manifest_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'gpu_job_started':False}))
'''
    checked=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','gpu5070ti','python3 -'],
        input=script,capture_output=True,text=True,check=True,timeout=60)
    result=json.loads(checked.stdout)
    assert result['files']==manifest['total_files'] and result['bytes']==manifest['total_bytes']
    assert result['manifest_sha256']==sha(path)
    (HERE/'remote_archive_verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()

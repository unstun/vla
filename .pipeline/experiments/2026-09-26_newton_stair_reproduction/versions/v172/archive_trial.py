"""Return every closed Mac trial before further long-running work."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,tarfile
HERE=Path(__file__).resolve().parent
REMOTE='/data/sun/vla_mppi_20261009/mac_archive_20261012'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--trial',type=Path,required=True);a=p.parse_args();trial=a.trial.resolve()
 assert trial.parent.parent==Path('/private/tmp') and trial.parent.name.startswith('vla_newton_v149_')
 assert re.fullmatch(r'v\d+_mac_full_attempt\d+',trial.name)
 execution=trial/'evidence/execution.json';assert execution.is_file(),'Still running or no closeout'
 files={str(f.relative_to(trial)):({'symlink':str(f.readlink())} if f.is_symlink() else {'bytes':f.stat().st_size,'sha256':sha(f)}) for f in trial.rglob('*') if f.is_file() or f.is_symlink()}
 dest=trial.parent/'closed';dest.mkdir(exist_ok=True)
 manifest=dest/(trial.name+'.manifest.json');archive=dest/(trial.name+'.tar')
 manifest.write_text(json.dumps({'trial':trial.name,'files':files},indent=2)+'\n')
 if not archive.exists():
  with tarfile.open(archive,'w') as tar:tar.add(trial,arcname=trial.name)
 digest=sha(archive)
 subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','gpu5070ti','mkdir','-p',REMOTE],check=True,timeout=20)
 subprocess.run(['rsync','-a','--partial','--timeout=60',str(archive),str(manifest),'gpu5070ti:'+REMOTE+'/'],check=True,timeout=900)
 verifier='''import pathlib,hashlib,json,sys,tarfile
root=pathlib.Path(sys.argv[1]);name=sys.argv[2];expected=sys.argv[3]
archive=root/(name+'.tar');h=hashlib.sha256()
with archive.open('rb') as f:
 for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
assert h.hexdigest()==expected
m=json.loads((root/(name+'.manifest.json')).read_text())
with tarfile.open(archive) as tar:
 for path,row in m['files'].items():
  member=tar.getmember(name+'/'+path)
  if 'symlink' in row:assert member.issym() and member.linkname==row['symlink'];continue
  assert member.size==row['bytes'];h=hashlib.sha256();f=tar.extractfile(member)
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
  assert h.hexdigest()==row['sha256'],path
print(json.dumps({'verified':True,'files':len(m['files']),'sha256':expected,'remote_archive':str(archive)}))
'''
 r=subprocess.run(['ssh','-o','BatchMode=yes','gpu5070ti','python3','-',REMOTE,trial.name,digest],input=verifier,text=True,capture_output=True,check=True,timeout=300)
 receipt=json.loads(r.stdout);receipt['local_archive']=str(archive);receipt['archive_bytes']=archive.stat().st_size
 out=HERE/'results'/trial.name;out.mkdir(parents=True,exist_ok=True)
 (out/'archive_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 (out/'archive_manifest.json').write_bytes(manifest.read_bytes())
 print(json.dumps(receipt))
if __name__=='__main__':main()

"""Copy this closed trial to the declared GPU archive and verify every tar member."""
from pathlib import Path
import json,shlex,subprocess
HERE=Path(__file__).resolve().parent
record=json.loads((HERE/'archive_local.json').read_text())
root='/data/sun/vla_mppi_20261009/mac_archive_v204_20261015'
name='v204_mac_full_attempt01.tar'
def remote(code,*args,timeout=60):
 command='python3 -c '+shlex.quote(code)+' '+' '.join(shlex.quote(a) for a in args)
 return subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','gpu5070ti',command],text=True,timeout=timeout)
remote('from pathlib import Path; import sys; p=Path(sys.argv[1]);p.mkdir(parents=True,exist_ok=True);assert not (p/sys.argv[2]).exists();assert not (p/(sys.argv[2]+".partial")).exists()',root,name)
subprocess.run(['scp','-q',record['archive'],'gpu5070ti:'+root+'/'+name+'.partial'],check=True,timeout=900)
subprocess.run(['scp','-q',str(HERE/'trial_archive_manifest.json'),'gpu5070ti:'+root+'/trial_archive_manifest.json'],check=True,timeout=60)
code='''from pathlib import Path
import hashlib,json,sys,tarfile
root=Path(sys.argv[1]);name=sys.argv[2];p=root/(name+".partial")
def digest(stream):
 h=hashlib.sha256()
 for block in iter(lambda:stream.read(1024*1024),b""):h.update(block)
 return h.hexdigest()
with p.open("rb") as stream:actual=digest(stream)
assert actual==sys.argv[3],actual
manifest=json.loads((root/"trial_archive_manifest.json").read_text());checked=0
with tarfile.open(p) as archive:
 for relative,expected in manifest["files"].items():
  member=archive.getmember(manifest["run"]+"/"+relative)
  assert member.size==expected["bytes"],relative
  assert digest(archive.extractfile(member))==expected["sha256"],relative
  checked+=1
p.rename(root/name)
print(json.dumps(dict(host="gpu5070ti",archive=str(root/name),sha256=actual,bytes=(root/name).stat().st_size,verified_files=checked,verified=True),indent=2))
'''
result=remote(code,root,name,record['sha256'],timeout=120)
(HERE/'remote_verification.json').write_text(result);print(result)

"""Compare the entire protected tree inventory without exceptions or writes."""
from pathlib import Path
import os,stat,json,hashlib
VERSION=Path('/Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v195')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024**2),b''):h.update(b)
 return h.hexdigest()
baseline=VERSION/'returned/protected_before.json'
before=json.loads(baseline.read_text());checks={}
for root_name,expected in before.items():
 root=Path(root_name);actual={}
 for p in [root,*sorted(root.rglob('*'))]:
  st=p.lstat();key=str(p.relative_to(root));entry={'mode':stat.S_IMODE(st.st_mode),'mtime_ns':st.st_mtime_ns}
  if p.is_symlink():entry.update(symlink=os.readlink(p))
  elif p.is_file():entry.update(sha256=sha(p),bytes=st.st_size)
  elif p.is_dir():entry.update(directory=True)
  else:raise ValueError(p)
  actual[key]=entry
 added=sorted(actual.keys()-expected.keys());removed=sorted(expected.keys()-actual.keys())
 changed=[k for k in expected.keys() & actual.keys() if expected[k]!=actual[k]]
 checks[root_name]={'entries':len(actual),'added':added,'removed':removed,'changed':sorted(changed),'passed':not(added or removed or changed)}
 print(root.name,len(actual),checks[root_name]['passed'],flush=True)
result={'passed':all(c['passed'] for c in checks.values()),'baseline_sha256':sha(baseline),
 'comparison':'Every regular file SHA-256/size, symlink target, directory entry, mode and mtime; additions/removals included; no exceptions',
 'paths':checks,'checker_sha256':sha(Path(__file__))}
(VERSION/'returned/protected_after.json').write_text(json.dumps(result,indent=2)+'\n')
assert result['passed'],result
print('All protected trees unchanged')

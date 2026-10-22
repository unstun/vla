from pathlib import Path
import hashlib,json,shutil
b=Path('.pipeline/experiments/2026-09-26_newton_stair_reproduction');v=b/'versions/v288';a=b/'audits/2026-10-20_v288_reentrant_work_terminal';old=b/'audits/2026-10-20_v287_local_cost_crash'
# Version-owned wrapper paths only; imported native sources retain their actual history.
for p in v.iterdir():
 if p.is_file() and p.suffix in {'.py','.txt','.sh','.md'}:
  p.write_text(p.read_text().replace('v287','v288').replace('V287','V288'))
for p in (old/'ultra9').iterdir():
 if p.is_file() and p.suffix in {'.py','.sh'}:
  s=p.read_text().replace('v287','v288').replace('V287','V288').replace('2026-10-20_v288_local_cost_crash','2026-10-20_v288_reentrant_work_terminal')
  # New execution copies reuse the completed v287 inputs, not v286 labels.
  if p.name in {'setup.py','bind.py'}:s=s.replace('vla_v286_20261020','vla_v287_20261020').replace('v286','v287')
  (a/'ultra9'/p.name).write_text(s)
for p in old.iterdir():
 if p.is_file() and p.suffix in {'.py','.cpp','.txt','.json'}:
  (a/p.name).write_text(p.read_text().replace('v287','v288').replace('2026-10-20_v288_local_cost_crash','2026-10-20_v288_reentrant_work_terminal'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inv={str(p.relative_to(v)):sha(p) for p in sorted((v/'src').rglob('*')) if p.is_file()}
(v/'source_inventory.json').write_text(json.dumps(inv,indent=2)+'\n')
print('source files',len(inv),'execution helpers',len(list((a/'ultra9').glob('*.py'))))

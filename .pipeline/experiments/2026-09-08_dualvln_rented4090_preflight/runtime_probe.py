
import json,subprocess
from pathlib import Path

def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=15)
 return {'exit':p.returncode,'stdout':p.stdout.strip(),'stderr':p.stderr.strip()}
r={'containers':run(['docker','ps','--format','{{.ID}}\t{{.Image}}\t{{.Names}}\t{{.Status}}']),
   'project_roots':{}}
for base in [Path('/home/ubuntu/sun'),Path('/home/ubuntu/docker')]:
 if base.is_dir(): r['project_roots'][str(base)]=sorted(p.name for p in base.iterdir())[:40]
r['isaac_versions']=[]
if r['containers']['exit']==0:
 for line in r['containers']['stdout'].splitlines():
  fields=line.split('\t')
  if len(fields)>=3 and 'isaac' in (fields[1]+' '+fields[2]).lower():
   cid=fields[0]
   row={'id':cid,'mounts':run(['docker','inspect','--format','{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}',cid])}
   row['version']=run(['docker','exec',cid,'bash','-lc','for p in /isaac-sim/VERSION /isaac-sim/version.txt; do if [ -f "$p" ]; then cat "$p"; fi; done'])
   r['isaac_versions'].append(row)
print(json.dumps(r,indent=2))

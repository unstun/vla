"""Adapt only private fixture field access to the new owned mapping state."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
shutil.copytree(BASE/'versions/v63/contract',args.output)
header=(BASE/'runtime/scan84_async_map_v81/src/plan_env/include/plan_env/grid_map.h').read_text()
groups={}
for kind,access in [('GridMapSupportState','mutableSupportState'),('GridMapState','mutableMapState')]:
 start=header.index('struct '+kind+' {');end=header.index('\n};',start)
 names=set(re.findall(r'\b(?:mp_|md_|reactive_\w+_|physical_floor_\w+_)\b',header[start:end]))
 groups[access]=names
proof={}
for path in args.output.rglob('*'):
 if not path.is_file() or path.suffix not in ('.cpp','.h','.inc'):continue
 before=path.read_bytes();text=before.decode()
 text=text.replace("/workspace/src/", "/task/workspace/v81/src/")
 for access,names in groups.items():
  for name in sorted(names,key=len,reverse=True):
   text=re.sub(r'(\.|->)'+name+r'\b',lambda m:m[1]+access+'().'+name,text)
 path.write_text(text)
 proof[str(path.relative_to(args.output))]={'original_sha256':hashlib.sha256(before).hexdigest(),
     'adapted_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
(args.output/'adaptation.json').write_text(json.dumps({'only_change':'Fixture private-state member access; assertions and data unchanged','files':proof},indent=2)+'\n')

"""Read-only checks on returned evidence and frozen source; no remote execution."""
from pathlib import Path
import ast,hashlib,json,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent;VERSIONS=HERE.parent.parent/'versions'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
versions={};python_files=0;json_files=0
for version in ('v249','v250','v251'):
 root=VERSIONS/version;manifest=json.loads((root/'manifest.json').read_text())
 for rel,h in manifest['source_files'].items():
  assert sha(root/rel)==h,(version,rel)
  assert sha(root/manifest['snapshot_locations'][rel])==h,(version,'snapshot',rel)
 assert sha(VERSIONS/manifest['parent']/'manifest.json')==manifest['parent_manifest_sha256']
 for name,key in (('source_inventory','source_inventory_sha256'),('installed_files','installed_inventory_sha256')):
  assert sha(root/'results'/(name+'.json'))==manifest[key],(version,key)
 if version=='v251':
  for name,key in (('evaluator_files','evaluator_inventory_sha256'),('fixture_files','fixture_inventory_sha256')):
   assert sha(root/'results'/(name+'.json'))==manifest[key]
 tests=0
 for p in (root/'results/pct_unit').glob('*.xml'):
  xml=ET.parse(p).getroot();assert int(xml.get('failures',0))==int(xml.get('errors',0))==0
  tests+=int(xml.get('tests',0))
 versions[version]=dict(manifest_sha256=sha(root/'manifest.json'),source_files=len(manifest['source_files']),pct_cases=tests)
receipt=json.loads((HERE/'results/return_receipt.json').read_text())
for rel,record in receipt['returned'].items():assert sha(HERE/rel)==record['sha256'],rel
for base,name,key in ((HERE/'research/A02','MANIFEST.json','files'),(HERE/'research/route_comparison','artifact_sha256.json',None)):
 entries=json.loads((base/name).read_text());entries=entries[key] if key else entries
 for rel,record in entries.items():assert sha(base/rel)==record['sha256'],(base,rel)
for root in [HERE]+[VERSIONS/v for v in ('v249','v250','v251')]:
 for p in root.rglob('*'):
  if p.is_file():
   assert p.suffix not in ('.o','.a','.so','.pyc','.npz','.pcd','.f32'),p
   assert 'CMakeFiles' not in p.parts and '__pycache__' not in p.parts,p
   if p.suffix=='.py':ast.parse(p.read_text(),filename=str(p));python_files+=1
   if p.suffix=='.json':json.loads(p.read_text());json_files+=1
qualification=json.loads((VERSIONS/'v251/results/acceptance_receipt.json').read_text())
assert qualification['passed'] and qualification['scored_calls']==60
assert qualification['first_gpmp_static_pass']==qualification['end_to_end_pass']==55
assert qualification['frozen_manifest_sha256']==versions['v251']['manifest_sha256']
report=dict(passed=True,versions=versions,returned_files_sha_verified=len(receipt['returned']),
 python_ast_files=python_files,json_parsed_files=json_files,no_local_build_or_raw_data=True,
 qualification_sha256=sha(VERSIONS/'v251/results/acceptance_receipt.json'),script_sha256=sha(Path(__file__)),
 physics_steps=0,claim='Local source and returned evidence verification; runtime receipts remain separately scoped')
(HERE/'results/local_quality.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)

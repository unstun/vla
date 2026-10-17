"""Bind the offline gate to actual source, headers, installed libraries and XML."""
from pathlib import Path
import hashlib,json,shlex,subprocess,xml.etree.ElementTree as ET
WORK=Path('/work');SOURCE=Path('/source')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inventory=json.loads((WORK/'source_inventory.json').read_text())
for rel,h in inventory.items():assert sha(WORK/rel)==h,rel
identity=json.loads((SOURCE/'source_identity.json').read_text())
for rel,h in identity['files'].items():assert sha(SOURCE/rel)==h,rel
for rel,h in identity['files'].items():
 if rel.startswith('src/'):assert inventory[rel]==h,rel
attempt='attempt08';evidence=WORK/'evidence'/attempt
assert 'Summary: 186 tests, 0 errors, 0 failures, 0 skipped' in (evidence/'test-result.log').read_text()
cases=0
for path in (evidence/'test_results').rglob('*.xml'):
 root=ET.parse(path).getroot();cases+=len(root.findall('.//testcase'))
 for suite in root.iter('testsuite'):
  assert not any(int(suite.attrib.get(k,0)) for k in ('errors','failures','skipped','disabled')),path
assert cases==165,cases
cache_checks={}
for path in (WORK/'build').glob('*/CMakeCache.txt'):
 relevant={}
 for line in path.read_text().splitlines():
  key,sep,value=line.partition('=')
  if sep and key.split(':')[0] in ('plan_env_DIR','bspline_opt_DIR','scan_planner_DIR','lite3_nav2_interfaces_DIR','scan_nav2_controller_DIR','lite3_nav2_plugins_DIR'):
   assert value.startswith('/work/install/'),(path,line)
   relevant[key]=value
 cache_checks[path.parent.name]=relevant
headers={}
for path in (WORK/'build').glob('*/compile_commands.json'):
 for entry in json.loads(path.read_text()):
  args=shlex.split(entry['command']);include=[];system=[]
  for i,arg in enumerate(args):
   if arg.startswith('-I') and len(arg)>2:include.append(arg[2:])
   elif arg=='-I':include.append(args[i+1])
   elif arg=='-isystem':system.append(args[i+1])
  for header in ('plan_env/grid_map.h','bspline_opt/environmental_curve_cost.h'):
   found=next((Path(p)/header for p in include+system if (Path(p)/header).is_file()),None)
   if found:
    assert str(found).startswith(('/work/src/','/work/install/')),(entry['file'],header,str(found))
    headers[entry['file']+':'+header]=str(found)
libs={}
for package,name in (('scan_nav2_controller','libscan_nav2_controller.so'),('scan_planner','libscan_native_core.so'),('bspline_opt','libbspline_opt.so'),('lite3_nav2_plugins','liblite3_nav2_plugins.so')):
 path=WORK/'install'/package/'lib'/name
 if not path.exists():continue
 output=subprocess.check_output(['ldd',str(path)],text=True)
 assert 'not found' not in output,output
 for line in output.splitlines():
  if any(token in line for token in ('libplan_env.so','libbspline_opt.so','libscan_native_core.so','libscan_nav2_controller.so')):
   assert '/work/install/' in line,line
 libs[str(path)]={'sha256':sha(path),'ldd':output}
installed={str(p.relative_to(WORK)):sha(p) for p in (WORK/'install').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
report={'passed':True,'physics_steps':0,'attempt':attempt,'unique_test_cases':cases,'colcon_records':186,
 'source_inventory':inventory,'installed_files':installed,'modified_header_resolution':headers,'package_cache_checks':cache_checks,
 'native_libraries':libs,'source_identity_sha256':sha(SOURCE/'source_identity.json'),'test_result_sha256':sha(evidence/'test-result.log')}
(WORK/'offline_gate.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ('passed','physics_steps','attempt','unique_test_cases','colcon_records')},indent=2))

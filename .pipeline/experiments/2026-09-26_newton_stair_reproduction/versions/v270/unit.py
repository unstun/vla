"""Native source geometry controls, keeping source material and support separate."""
from pathlib import Path
import ast,hashlib,json,math,os,subprocess,sys
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import numpy as np
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'source_surface_native_v270'
sys.path.insert(0,str(HERE.parent/'v268'))
from source_topology import prepare
from source_model import SurfaceModel
source=HERE.parent/'v266/validate_surface.py';function=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='box')
context=dict(np=np,math=math);exec(compile(ast.Module(body=[function],type_ignores=[]),str(source),'exec'),context);box=context['box']
floor=box([0,0,-.1],[5,5,.1]);cases=[]
for name,height in [('below_critical',.26-1e-7),('critical',.26),('above_critical',.26+1e-7)]:
    cases.append((name,np.concatenate([floor,box([1,0,height*.5],[1,2,height*.5])]),[-.2,0.,0.,math.pi/2]))
roof=np.array([[[-2,-2,2],[2,-2,2],[2,2,2]],[[-2,-2,2],[2,2,2],[-2,2,2]]],float)
wall=np.array([[[.75,-2,0],[.75,2,0],[.75,2,2]],[[.75,-2,0],[.75,2,2],[.75,-2,2]]],float)
cases.extend([('open_roof',np.concatenate([floor,roof]),[0,0,0,0]),
 ('open_roof_reverse',np.concatenate([floor,roof[:,::-1]]),[0,0,0,0]),
 ('open_wall_front',np.concatenate([floor,wall]),[.3,0,0,0]),
 ('open_wall_back',np.concatenate([floor,wall]),[1.2,0,0,0]),
 ('inverted_wall',np.concatenate([floor,box([0,0,1],[1,1,1])[:,::-1]]),[0,0,0,0]),
 ('inverted_floor',floor[:,::-1],[0,0,0,0]),
 ('low_ceiling',np.concatenate([floor,box([0,0,.55],[2,2,.1])]),[0,0,0,0]),
 ('high_ceiling',np.concatenate([floor,box([0,0,1.1],[2,2,.1])]),[0,0,0,0])])
thin=box([0,0,-.05],[5e-9,.5,.05]);thin[:,:,2]+=2e7*thin[:,:,0]
cases.append(('near_vertical_floor_normal',np.concatenate([floor,thin]),[0,0,0,0]))
tiny=np.array([[[0,0,.1],[1e-6,0,.1],[0,1e-6,.1]]],float)
cases.append(('tiny_open_upward_surface',np.concatenate([floor,tiny]),[0,0,0,0]))
cases.append(('tiny_closed_upward_cap',np.concatenate([floor,box([0,0,.05],[1e-6,1e-6,.05])]),[0,0,0,0]))
def export(tri,name):
    normalized,ids,m=prepare(tri);p=OUT/(name+'.f64');normalized.astype('<f8').tofile(p)
    solids=[r for r in m['objects_detail'] if r['certified_closed_volume']]
    lines=[f'SURFACE268C {len(tri)} {len(solids)}']
    for r in solids:lines.append(' '.join([str(r['solid_id']),*[format(v,'.17g') for b in r['bounds'] for v in b]]))
    lines.append('F');lines.extend(map(str,ids.tolist()));q=OUT/(name+'.meta');q.write_text('\n'.join(lines)+'\n')
    return '/work/'+p.name,'/work/'+q.name
results=[]
for name,tri,pose in cases:
    paths=export(tri,'unit_'+name);expected=SurfaceModel(tri).assess(*pose,check_support=False)['solid']
    (OUT/'unit_queries.txt').write_text(' '.join(format(x,'.17g') for x in pose)+'\n')
    with (OUT/('unit_'+name+'.log')).open('w') as log:
        subprocess.run([sys.executable,str(HERE/'native.py'),'query',*paths,'/work/unit_queries.txt','/work/unit_answers.txt'],stdout=log,stderr=subprocess.STDOUT,check=True)
    actual=float((OUT/'unit_answers.txt').read_text());expected=min(.15,expected)
    results.append(dict(case_id=name,pose=pose,expected_margin=expected,actual_margin=actual,passed=abs(actual-expected)<1e-8 and (actual<=0)==(expected<=0)))
receipt=dict(cases=results,failed=sum(not r['passed'] for r in results),
    source_sha256=hashlib.sha256((HERE/'source_surface.cpp').read_bytes()).hexdigest(),
    binary_sha256=hashlib.sha256((OUT/'build/surface_probe').read_bytes()).hexdigest(),planning_calls=0,physics_steps=0)
(OUT/'unit.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
assert not receipt['failed']

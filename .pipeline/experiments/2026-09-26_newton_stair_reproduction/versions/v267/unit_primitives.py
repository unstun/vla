"""Native physical controls including strict critical step contact."""
from pathlib import Path
import ast,hashlib,json,math,subprocess,sys
import numpy as np
BASE=Path('/data/sun/vla_mppi_20261009');HERE=Path(__file__).resolve().parent;OUT=BASE/'source_surface_native_v267'
source=HERE.parent/'v266/validate_surface.py'
function=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='box')
context=dict(np=np,math=math);exec(compile(ast.Module(body=[function],type_ignores=[]),str(source),'exec'),context);box=context['box']
floor=box([0,0,-.1],[5,5,.1]);cases=[]
for name,height,free in [('below_critical',.26-1e-7,True),('critical',.26,False),('above_critical',.26+1e-7,False)]:
    cases.append((name,np.concatenate([floor,box([1,0,height*.5],[1,2,height*.5])]),[-.2,0.,0.,math.pi/2],free))
for name,center,half,pose,free in [
    ('wall',[1,0,.75],[.1,3,.75],[.5,0,0,0],False),
    ('wall_clear',[1,0,.75],[.1,3,.75],[0,0,0,0],True),
    ('contained',[0,0,1],[1,1,1],[0,0,0,0],False),
    ('low_ceiling',[0,0,.55],[2,2,.1],[0,0,0,0],False),
    ('high_ceiling',[0,0,1.1],[2,2,.1],[0,0,0,0],True),
    ('finite_wall_end',[1,0,.75],[.1,.1,.75],[.5,1,0,0],True)]:
    cases.append((name,np.concatenate([floor,box(center,half)]),pose,free))
results=[]
for name,tri,pose,expected in cases:
    data=OUT/('unit_'+name+'.f64');tri.astype('<f8').tofile(data)
    (OUT/'unit_queries.txt').write_text(' '.join(format(x,'.17g') for x in pose)+'\n')
    with (OUT/('unit_'+name+'.log')).open('w') as log:
        subprocess.run([sys.executable,str(HERE/'native.py'),'query','/work/'+data.name,'/work/unit_queries.txt','/work/unit_answers.txt'],stdout=log,stderr=subprocess.STDOUT,check=True)
    margin=float((OUT/'unit_answers.txt').read_text())
    results.append(dict(case_id=name,pose=pose,expected_free=expected,margin=margin,passed=(margin>0)==expected))
tag=sys.argv[1];assert tag.isalnum()
receipt=dict(cases=results,failed=sum(not r['passed'] for r in results),
    source_sha256=hashlib.sha256((HERE/'source_surface.cpp').read_bytes()).hexdigest(),
    binary_sha256=hashlib.sha256((OUT/'build/surface_probe').read_bytes()).hexdigest(),planning_calls=0,physics_steps=0)
(OUT/('unit_'+tag+'.json')).write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
assert not receipt['failed']

"""Return compact negative controls; caches and raw geometry remain remote."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for version,names,status in [
 ('v267',['raw_point_oracle.json','raw_point06.log','raw_material_unit06.log','unit_red.json','unit_red.log','topology.json','build01.log','source_query.log','source_compare01.log','source_compare02.log','source_compare03.log'], 'Rejected source prototype; partial comparison is not a pass'),
 ('v269',['unit.json','unit01.log','source_parity.json','source_queries.txt','source_answers.txt','source_query.log','source_compare01.log','difference_diagnosis.json','candidate_recall_diagnosis.json','build01.log'], 'Preserved failed reference comparison; candidate-recall defect independently corrected in v270')]:
    root=BASE/('source_surface_native_'+version);dest=HERE.parent/version/'results';dest.mkdir(exist_ok=True)
    files={};missing=[]
    for name in names:
        p=root/name
        if not p.exists():missing.append(name);continue
        assert p.stat().st_size<4*1024*1024
        q=dest/name;shutil.copy2(p,q);files[name]=dict(sha256=sha(p),bytes=p.stat().st_size,remote_path=str(p))
    record=dict(version=version,status=status,files=files,unavailable_optional_names=missing,native_planner_integrated=False,physics_steps=0)
    (dest/'return_inventory.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(dict(version=version,files=len(files),bytes=sum(r['bytes'] for r in files.values()))))

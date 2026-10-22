from pathlib import Path
import hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'source_integrated_benchmark_v281'
COHORTS={'original52':('v257','space_coverage_v257',52),'clean50':('v262','mesh_benchmark_v262',53)}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n')
def load(p,name):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def verify_inputs():
    native=load(HERE.parent/'v280/verify_frozen.py','native272').verify();cohorts={}
    for name,(version,root,count) in COHORTS.items():
        original=HERE.parent/version;f=json.loads((original/'manifest.json').read_text());m=json.loads((HERE/(name+'.json')).read_text())
        assert sha(HERE/(name+'.json'))==sha(original/'cases_manifest.json')==f['cases_manifest_sha256']
        assert len(m['cases'])==count
        fixture_hashes={}
        for c in m['cases']:
            p=BASE/root/'cases'/c['case_id']/'fixture.json';assert sha(p)==f['fixtures'][c['case_id']]
            data=json.loads(p.read_text());assert data['physics_steps']==0 and data['max_scan_s']<=.1
            for rel,h in data['files'].items():assert sha(p.parent/rel)==h,(name,c['case_id'],rel)
            fixture_hashes[c['case_id']]=sha(p)
        cohorts[name]=dict(cases=count,cases_manifest_sha256=sha(HERE/(name+'.json')),source_manifest_sha256=sha(original/'manifest.json'),fixtures=fixture_hashes)
    clean=json.loads((HERE/'clean50.json').read_text());assert clean['positive_count']==clean['distinct_positive_tuples']==50
    material=json.loads((HERE.parent/'v276/manifest.json').read_text())
    for rel,h in material['files'].items():assert sha(HERE.parent/'v276'/rel)==h,rel
    external={str(p.relative_to(HERE.parent)):sha(p) for p in [HERE.parent/'v276/manifest.json',HERE.parent/'v276/registered_point_oracle.py',HERE.parent/'v276/source_material_association.py',HERE.parent/'v266/surface_model.py',HERE.parent/'v272/raw_source_oracle.py',HERE.parent/'v267/finite_floor_material.py',HERE.parent/'v257/run_matrix.py',HERE.parent/'v254/run_matrix.py',HERE.parent/'v242/run_matrix.py']}
    return dict(native=native,cohorts=cohorts,external_evaluator_dependencies=external,cpu_limit=2,memory_gib=6,physics_steps=0)
def verify():
    m=json.loads((HERE/'manifest.json').read_text())
    for rel,h in m['files'].items():assert sha(HERE/rel)==h,rel
    binding=verify_inputs();assert binding==json.loads((HERE/'results/input_binding.json').read_text())
    assert m['native_manifest_sha256']==binding['native']['native_manifest_sha256']
    return m

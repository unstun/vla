"""Build a compact, explicit return package; full CSVs/build trees stay remote."""
from pathlib import Path
import hashlib,json,shutil
work=Path('/data/sun/vla_mppi_20261009/callback_failure_v232')
source=Path('/data/sun/vla_mppi_20261009/source_v232')
out=work/'return_results'
out.mkdir(exist_ok=True)
def copy(path,rel):
    target=out/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
for name in ('source_inventory.json','composition.json','replay_comparison_final.json','offline_gate.json','admission_route_parity_final.json','graph_gate_final.json'):
    copy(work/name,name)
for path in work.glob('*.log'): copy(path,path.name)
for path in Path('/data/sun/vla_mppi_20261009').glob('v232_*.log'):
    copy(path,Path('diagnostic_attempts')/path.name)
for name in ('graph_probe01','graph_probe02','graph_probe03'):
    for path in (work/name).glob('*'):
        if path.is_file() and path.suffix in ('.json','.yaml','.log','.xml'):
            copy(path,Path(name)/path.name)

for attempt in sorted((work/'evidence').glob('attempt*')):
    for name in ('build.log','test.log','test-result.log'):
        if (attempt/name).exists():copy(attempt/name,Path('build')/attempt.name/name)
    for folder in ('test_results','ament_cmake_gtest'):
        for path in (attempt/folder).rglob('*'):
            if path.is_file():copy(path,Path('build')/attempt.name/path.relative_to(attempt))
for path in (work/'build').glob('*/test_results/*/*.xml'):
    copy(path,Path('test_xml')/path.relative_to(work/'build'))
for path in (work/'evidence/source_revisions').rglob('*'):
    if path.is_file():copy(path,Path('source_revisions')/path.relative_to(work/'evidence/source_revisions'))
for path in (work/'feedback_output').glob('*.csv'):copy(path,Path('feedback_output')/path.name)
for path in (work/'final_probe08').glob('*.log'):copy(path,Path('final_probe08')/path.name)
for path in (work/'final_probe08/admission_output03').glob('*_admitted.csv'):
    copy(path,Path('final_probe08/admission_output03')/path.name)
identity=json.loads((source/'source_identity.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for rel,expected in identity['files'].items():assert sha(source/rel)==expected,rel
inventory=json.loads((work/'source_inventory.json').read_text())
for rel,expected in inventory.items():assert sha(work/rel)==expected,rel
assert all(sha(source/rel)==inventory[rel] for rel in identity['files'] if rel.startswith('src/'))
(out/'sync_gate.json').write_text(json.dumps({'source_identity_sha256':sha(source/'source_identity.json'),'source_files_verified':len(inventory),'owned_source_files_verified':sum(k.startswith('src/') for k in identity['files']),'physics_steps':0},indent=2)+'\n')
(out/'execution_receipt.json').write_text(json.dumps({'host':'gpu5070ti','source':str(source),'workspace':str(work),'image':'sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4','build_attempt':'attempt08','field_probe':'final_probe08/field_probe03.log','admission_probe':'final_probe08/admission_probe03.log','raw_oracle':None,'replay':'replay_comparison_final.json','physics_steps':0},indent=2)+'\n')
print(json.dumps({'return_files':sum(p.is_file() for p in out.rglob('*')),'return_bytes':sum(p.stat().st_size for p in out.rglob('*') if p.is_file())}))

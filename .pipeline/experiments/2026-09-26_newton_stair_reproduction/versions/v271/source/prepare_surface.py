"""Create separate verified source fixtures; never overwrite linked parent data."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009')
F=BASE/'source_surface_integration_v271/native/fixtures'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def fnv(p):
    h=14695981039346656037
    for b in p.read_bytes():h=((h^b)*1099511628211)&((1<<64)-1)
    return str(h)
e=json.loads((BASE/'source_topology_v268/geometry_export.json').read_text())
files=[]
for key,name in [('normalized_triangles','source_triangles.f64'),('closed_volumes','source_volumes.txt')]:
    source=Path(e[key]['remote_path']);assert sha(source)==e[key]['sha256']
    dest=F/name
    if dest.exists():assert sha(dest)==sha(source)
    else:shutil.copy2(source,dest)
    files.append(dict(path=str(dest),sha256=sha(dest),fnv64=fnv(dest),bytes=dest.stat().st_size))
content='SURFACE271B .35 .18 .55 .35 .3 .15\n'
for row in files:content+=f'"/work/fixtures/{Path(row["path"]).name}" {row["fnv64"]}\n'
descriptor=F/'source_surface.env'
if descriptor.exists():assert descriptor.read_text()==content
else:descriptor.write_text(content)
env='source /work/fixtures/probe225.env\nexport RAW_FIELD=/work/fixtures/source_surface.env\nexport RAW_FNV='+fnv(descriptor)+'\n'
path=F/'probe271.env'
if path.exists():assert path.read_text()==env
else:path.write_text(env)
receipt=dict(source_export=e,dependencies=files,descriptor_sha256=sha(descriptor),descriptor_fnv64=fnv(descriptor),
    source_env_sha256=sha(path),legacy_solid_sha256=sha(F/'building/static_solids.env'))
(F/'source_surface_provenance.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt),flush=True)

units=json.loads((BASE/'source_surface_native_v270/unit.json').read_text())
assert units['failed']==0
(F/'source_units.tsv').write_text(''.join(' '.join([r['case_id'],*[format(x,'.17g') for x in r['pose']],format(r['expected_margin'],'.17g')])+'\n' for r in units['cases']))

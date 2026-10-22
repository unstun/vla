"""Export orientation-only geometry and certified closed-volume identities."""
from pathlib import Path
import hashlib,json
import numpy as np
from source_topology import prepare
BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'source_topology_v268';OUT.mkdir(exist_ok=True)
tp=BASE/'support_coverage_v134/triangles.f64';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(tp)=='f3910b7c8106977d1f6e3364c464a9144c7946a0585c8cdcff4346d7add342fc'
tri=np.fromfile(tp,dtype='<f8').reshape(-1,3,3);normalized,labels,receipt=prepare(tri)
geometry=OUT/'triangles_oriented.f64';data=normalized.astype('<f8').tobytes()
if geometry.exists():assert geometry.read_bytes()==data
else:geometry.write_bytes(data)
solids=[r for r in receipt['objects_detail'] if r['certified_closed_volume']]
lines=[f'SURFACE268C {len(tri)} {len(solids)}']
for r in solids:lines.append(' '.join([str(r['solid_id']),*[format(v,'.17g') for bound in r['bounds'] for v in bound]]))
lines.append('F');lines.extend(map(str,labels.tolist()));text='\n'.join(lines)+'\n'
metadata=OUT/'closed_volumes.txt'
if metadata.exists():assert metadata.read_text()==text
else:metadata.write_text(text)
result=dict(original_triangles_sha256=sha(tp),normalized_triangles=dict(remote_path=str(geometry),bytes=geometry.stat().st_size,sha256=sha(geometry)),
    closed_volumes=dict(remote_path=str(metadata),bytes=metadata.stat().st_size,sha256=sha(metadata)),
    geometry_point_sets_and_connectivity_unchanged=True,topology=receipt)
(OUT/'geometry_export.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='topology'}),flush=True)

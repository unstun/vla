from pathlib import Path
import json
B=Path('/data/sun/vla_mppi_20261009');out=B/'generic_mechanisms_v261/evaluation/mesh_witness_poses.txt'
with out.open('w') as f:
 for cid in ('E03','E02'):
  r=json.loads((B/'generic_mechanisms_v261/mesh_certificates'/(cid+'.json')).read_text())
  for i,p in enumerate(r['samples']):f.write(f'{cid}_{i} {p[0]:.17g} {p[1]:.17g} {p[2]+.3:.17g} {p[3]:.17g}\n')

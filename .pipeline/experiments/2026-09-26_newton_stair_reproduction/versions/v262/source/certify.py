"""Build benchmark connectivity evidence from original mesh, before PCT scores."""
from pathlib import Path
from collections import deque
import hashlib, json, math, os, pickle, sys, time
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import numpy as np

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1]
AUDIT = EXP / 'audits/2026-10-18_v259_equivalent_geometry_repairs'
sys.path.insert(0, str(AUDIT))
from mesh_route_certificate import MeshRouteCertificate

BASE = Path('/data/sun/vla_mppi_20261009')
OUT = BASE / 'mesh_benchmark_v262'
OUT.mkdir(exist_ok=True)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
source = BASE / 'support_coverage_v134/triangles.f64'
assert sha(source) == 'f3910b7c8106977d1f6e3364c464a9144c7946a0585c8cdcff4346d7add342fc'
mesh = MeshRouteCertificate(np.fromfile(source, dtype='<f8').reshape(-1, 3, 3))
old = json.loads((HERE.parent / 'v257/cases_manifest.json').read_text())['cases']
by_id = {c['case_id']: c for c in old}
root_case = by_id['A04']
root = np.array(root_case['start']['ground'] + [root_case['start']['yaw']])
assert mesh.mesh.pose(*root)[0]
initial = list(mesh.near(root))
assert initial
parent = {k: None for k in initial}
queue = deque(initial)
began = time.monotonic()
while queue:
    key = queue.popleft()
    for child in mesh.neighbours(key):
        if child in parent or not mesh.edge(key, child):
            continue
        parent[child] = key
        queue.append(child)
    if len(parent) > 400000:
        raise RuntimeError('Construction budget; never label exhausted proposals illegal')
    if len(parent) // 2000 != getattr(mesh, '_last_report', -1):
        mesh._last_report = len(parent) // 2000
        print('MESH_COMPONENT', len(parent), 'queued', len(queue),
              'queries', mesh.pose_queries, 'wall_s', time.monotonic() - began, flush=True)

# Cache is remote diagnostic data. Compact source hashes and the selected
# path witnesses will return locally; no pickle is an authoritative result.
with (OUT / 'mesh_component.pkl').open('wb') as f:
    pickle.dump(dict(parent=parent, cells=mesh.cells, states=mesh.states,
                     edges=mesh.edges), f, protocol=5)
poses = [dict(key=list(k), pose=mesh.pose(k).tolist(),
              edge_margin=mesh.states[k][1], solid_margin=mesh.states[k][2])
         for k in sorted(parent)]
(OUT / 'reachable_poses.json').write_text(json.dumps(poses) + '\n')
receipt = dict(original_triangles_sha256=sha(source), root=root.tolist(),
               reachable_pose_states=len(parent), queried_states=mesh.pose_queries,
               wall_s=time.monotonic()-began, route_scores_used=False,
               graph_resolution_m=mesh.res, heading_step_rad=math.pi/4,
               source_files={p.name: sha(p) for p in [Path(__file__),
                   AUDIT/'mesh_route_certificate.py', AUDIT/'mesh_geometry.py',
                   AUDIT/'mesh_floor_connectivity.py']})
(OUT / 'component_receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
print('COMPONENT_COMPLETE', json.dumps(receipt), flush=True)

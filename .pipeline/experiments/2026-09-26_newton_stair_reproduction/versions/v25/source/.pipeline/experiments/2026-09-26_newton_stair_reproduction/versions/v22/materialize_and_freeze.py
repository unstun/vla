from pathlib import Path
from datetime import datetime,timezone
import difflib,hashlib,json,shutil
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def replace(s,old,new):
 assert s.count(old)==1,old[:80]
 return s.replace(old,new)
def main():
 parent=json.loads((H.parent/'v21/manifest.json').read_text());assert not (H/'manifest.json').exists()
 for name,digest in parent['source_files'].items():assert sha(R/name)==digest,name
 data=B/'inputs/new_building_dense_surface.npy';assert not data.exists();shutil.copyfile(B/'audits/2026-09-27_dense_static_sampling/raw_surface_points.npy',data)
 assert sha(data)=='97b16b3c6e8abb9700f65309fac7967bc1fb295ed6c1a55c7e52b042f8a219ce'
 paths=[B/'runtime_sources/bridge/lite3_sim_bridge/pct_sim_clock_core.py',B/'runtime_sources/bridge/lite3_sim_bridge/pct_sim_clock_publisher.py',B/'scripts/native_graph.py',B/'setup/runtime_sources.json',B/'setup/source_identity.json'];before={p:p.read_bytes() for p in paths}
 for p,raw in before.items():q=H/'parent_source'/p.relative_to(B);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(raw)
 p=paths[0];s=p.read_text();s+='''

DENSE_SURFACE_SHA = "97b16b3c6e8abb9700f65309fac7967bc1fb295ed6c1a55c7e52b042f8a219ce"


def load_dense_surface_points(path: Path) -> np.ndarray:
    """Read the pinned same-Building offline surface evidence payload."""
    if hashlib.sha256(path.read_bytes()).hexdigest() != DENSE_SURFACE_SHA:
        raise ValueError("Dense Building surface source SHA-256 mismatch")
    points = np.load(path, allow_pickle=False)
    if points.dtype != np.dtype("<f4") or points.shape != (126659, 4) or \\
       not np.isfinite(points).all() or np.any(points[:, 3] < 0.0) or np.any(points[:, 3] > 20.0):
        raise ValueError("Invalid dense Building surface payload")
    return points.copy()
''';p.write_text(s)
 p=paths[1];s=p.read_text();s=replace(s,'load_surface_cost, surface_evidence_points)','load_surface_cost, surface_evidence_points, load_dense_surface_points)')
 old='''        surface_path = str(self.declare_parameter("surface_cost_path", "").value)
        if mode == "surface_evidence":
            if not surface_path or paired_elevations is None or coord_mode != "identity" or visual_offset != 0.03:
                raise ValueError("Surface evidence requires paired pinned Building data")
            self._points = surface_evidence_points(source, paired_elevations,
                                                   load_surface_cost(Path(surface_path), source))
        else:
            if surface_path:
                raise ValueError("Surface cost is only valid for the surface evidence topic")'''
 new='''        surface_path = str(self.declare_parameter("surface_cost_path", "").value)
        dense_path = str(self.declare_parameter("dense_surface_path", "").value)
        if mode == "surface_evidence":
            if bool(surface_path) == bool(dense_path) or paired_elevations is None or coord_mode != "identity" or visual_offset != 0.03:
                raise ValueError("Surface evidence requires exactly one paired pinned Building source")
            self._points = (load_dense_surface_points(Path(dense_path)) if dense_path else
                            surface_evidence_points(source, paired_elevations,
                                                    load_surface_cost(Path(surface_path), source)))
        else:
            if surface_path or dense_path:
                raise ValueError("Surface sources are only valid for the surface evidence topic")'''
 s=replace(s,old,new);p.write_text(s)
 p=paths[2];s=p.read_text();s=replace(s,'"-p", "ground_mode:=surface_evidence", "-p", "surface_cost_path:=" +\n                str(BASE / "inputs/new_building_uninflated_cost.npz")','"-p", "ground_mode:=surface_evidence", "-p", "dense_surface_path:=" +\n                str(BASE / "inputs/new_building_dense_surface.npy")');p.write_text(s)
 p=paths[3];r=json.loads(p.read_text())
 for q in paths[:2]:
  rows=[x for x in r['records'] if x['path']==str(q.relative_to(B))];assert len(rows)==1 and rows[0]['sha256']==hashlib.sha256(before[q]).hexdigest();rows[0].update(sha256=sha(q),bytes=q.stat().st_size,local_modification='v22 explicit hash-pinned same-Building denser surface evidence; original navigation tensor and native rules unchanged')
 p.write_text(json.dumps(r,indent=2)+'\n')
 p=paths[4];r=json.loads(p.read_text());r['inputs'].append({'path':str(data.relative_to(B)),'sha256':sha(data),'bytes':data.stat().st_size,'source':'audits/2026-09-27_dense_static_sampling/prepare.py + observe_raw.py; pinned Trimesh all-surface sampling and unchanged PCT generator','scope':'Offline static Building evidence only; original PCD points retained; no actor truth; original navigation map unchanged'});p.write_text(json.dumps(r,indent=2)+'\n')
 for name in ['building_planner.yaml','flat_planner.yaml']:shutil.copyfile(H.parent/'v21'/name,H/name)
 for name in ['receipt.json','raw_receipt.json']:shutil.copyfile(B/'audits/2026-09-27_dense_static_sampling'/name,H/name)
 (H/'changes.patch').write_text(''.join(''.join(difflib.unified_diff(raw.decode().splitlines(True),p.read_text().splitlines(True),fromfile='v21/'+str(p.relative_to(B)),tofile='v22/'+str(p.relative_to(B)))) for p,raw in before.items()))
 selected={R/name for name in parent['source_files']}|set(paths)|{data}
 selected.update(p for p in H.rglob('*') if p.is_file())
 for p in [B/'audits/2026-09-27_dense_static_sampling/prepare.py',B/'audits/2026-09-27_dense_static_sampling/observe_raw.py']:selected.add(p)
 selected.update(p for p in (R/'references/upstream/2026-09-27_trimesh_surface_sampling').rglob('*') if p.is_file())
 records={}
 for p in sorted(selected):
  name=str(p.relative_to(R));records[name]=sha(p);q=H/'source'/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
 (H/'manifest.json').write_text(json.dumps({'version':'v22','parent':'v21','status':'frozen_unvalidated','frozen_utc':datetime.now(timezone.utc).isoformat(),'change':'Publish denser same-Building static surface evidence, preserving original selected navigation support','source_files':records,'changed_files':[str(p.relative_to(R)) for p in paths+[data]],'native_build':parent['native_build'],'source_snapshot_prefix':'source/','acceptance_plan':'PLAN.md'},indent=2)+'\n');print({'version':'v22','source_files':len(records)})
if __name__=='__main__':main()

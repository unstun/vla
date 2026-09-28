from pathlib import Path
from datetime import datetime,timezone
import difflib,hashlib,json,shutil
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1];ROOT=BASE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 parent=json.loads((HERE.parent/'v18/manifest.json').read_text())
 if (HERE/'manifest.json').exists():raise FileExistsError('v19 frozen')
 for name,digest in parent['source_files'].items():
  if sha(ROOT/name)!=digest:raise ValueError('Parent source changed: '+name)
 core=BASE/'runtime_sources/bridge/lite3_sim_bridge/pct_sim_clock_core.py';publisher=core.with_name('pct_sim_clock_publisher.py');launcher=BASE/'scripts/native_graph.py';receipt=BASE/'setup/runtime_sources.json';inputs=BASE/'setup/source_identity.json'
 paths=[core,publisher,launcher,receipt,inputs];before={p:p.read_bytes() for p in paths}
 for p,raw in before.items():
  target=HERE/'parent_source'/p.relative_to(BASE);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
 candidate=BASE/'audits/2026-09-27_pct_precision/pct_core_candidate.py';core.write_bytes(candidate.read_bytes())
 s=publisher.read_text();old='                                load_pinned_map, selected_ground_points)';new='                                load_pinned_map, load_paired_elevations, selected_ground_points)';assert s.count(old)==1;s=s.replace(old,new)
 old='''        source = load_pinned_map(map_path)
        self._points = selected_ground_points(source, coord_mode, visual_offset,
                                              cost_limit=None if mode == "tracking_physical" else 20.0)'''
 new='''        source = load_pinned_map(map_path)
        elevation_path = str(self.declare_parameter("elevation_path", "").value)
        paired_elevations = None
        if elevation_path:
            if mode != "navigation_selected":
                raise ValueError("Original precision is only supported for selected navigation terrain")
            paired_elevations = load_paired_elevations(Path(elevation_path), source)
        self._points = selected_ground_points(source, coord_mode, visual_offset,
                                              cost_limit=None if mode == "tracking_physical" else 20.0,
                                              paired_elevations=paired_elevations)'''
 assert s.count(old)==1;s=s.replace(old,new);publisher.write_text(s)
 s=launcher.read_text();old='''        launch("pct_support", [py, pct_script, "--ros-args", "-p", "map_path:=" + str(map_path), "-p", "use_sim_time:=true"])''';new='''        ground_args = [py, pct_script, "--ros-args", "-p", "map_path:=" + str(map_path), "-p", "use_sim_time:=true"]
        if not flat:
            ground_args += ["-p", "elevation_path:=" + str(BASE / "inputs/new_building_original_precision.npz")]
        launch("pct_support", ground_args)''';assert s.count(old)==1;s=s.replace(old,new);launcher.write_text(s)
 data=BASE/'inputs/new_building_original_precision.npz';original=BASE/'audits/2026-09-27_pct_precision/tomogram_float32.npz';assert sha(original)=='9adbbaf3754fc1a488ada560775407d4c684d57e19a6caea7075fa907b5c0c2d';shutil.copyfile(original,data)
 r=json.loads(receipt.read_text())
 for p in [core,publisher]:
  rows=[v for v in r['records'] if v['path']==str(p.relative_to(BASE))];assert len(rows)==1 and rows[0]['sha256']==hashlib.sha256(before[p]).hexdigest();row=rows[0];row.setdefault('archived_sha256',row['sha256']);row['sha256']=sha(p);row['bytes']=p.stat().st_size;row['local_modification']='v19 preserve original heights for unchanged selected terrain; preimage in versions/v19/parent_source'
 receipt.write_text(json.dumps(r,indent=2)+'\n')
 r=json.loads(inputs.read_text());assert not any(x['path']==str(data.relative_to(BASE)) for x in r['inputs']);r['inputs'].append({'path':str(data.relative_to(BASE)),'source':'Archived original generation: machine-dog-nav/.pipeline/experiments/2026-09-08_new_building_pct/runs/preflight03/tomogram_float32.npz','sha256':sha(data),'bytes':data.stat().st_size,'pairing':'Full tensor rounds exactly to existing pinned float16 map; metadata equal; only selected terrain heights consumed'});inputs.write_text(json.dumps(r,indent=2)+'\n')
 (HERE/'changes.patch').write_text(''.join(''.join(difflib.unified_diff(before[p].decode().splitlines(True),p.read_text().splitlines(True),fromfile='v18/'+str(p.relative_to(BASE)),tofile='v19/'+str(p.relative_to(BASE)))) for p in paths))
 for name in ['building_planner.yaml','flat_planner.yaml']:shutil.copyfile(HERE.parent/'v18'/name,HERE/name)
 (HERE/'precision_input.json').write_text(json.dumps({'path':str(data.relative_to(ROOT)),'sha256':sha(data),'bytes':data.stat().st_size,'source_generator_commit':'1cf45a1c12ca785ce533293302be09d51daf0ccb','original_generator_sha256':'6de22d1dd7fb3b2295d1d570011ede8b2f16dbcf72b48b1118e5270c300a55b0','source_generation_receipt':'references/upstream/2026-09-27_pct_ground_cost_reference/historical_generation.json','regeneration':'Original CPU generator and recorded configuration with original NumPy1.21.5 stack; preserve archived bytes because newer SciPy/NumPy yields small gradient differences. Height channels replay identically.'},indent=2)+'\n')
 selected={ROOT/name for name in parent['source_files']};selected.add(data);selected.update(paths);selected.update(p for p in (HERE/'parent_source').rglob('*') if p.is_file());selected.update(p for p in HERE.iterdir() if p.is_file());records={}
 for p in sorted(selected):
  name=str(p.relative_to(ROOT));records[name]=sha(p);dest=HERE/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
 (HERE/'manifest.json').write_text(json.dumps({'version':'v19','parent':'v18','status':'frozen_unvalidated','frozen_utc':datetime.now(timezone.utc).isoformat(),'change':'Publish original float32 heights for the unchanged PCT-selected ground cells','source_files':records,'changed_files':[str(p.relative_to(ROOT)) for p in paths+[data]],'native_build':parent['native_build'],'source_snapshot_prefix':'source/','acceptance_plan':'PLAN.md'},indent=2)+'\n');print(json.dumps({'version':'v19','source_files':len(records)}))
if __name__=='__main__':main()

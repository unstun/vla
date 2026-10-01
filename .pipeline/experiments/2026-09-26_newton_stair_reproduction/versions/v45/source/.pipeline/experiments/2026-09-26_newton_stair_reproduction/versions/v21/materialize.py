"""Materialize one reviewed candidate; freeze separately after source review."""
from pathlib import Path
import difflib,hashlib,json,shutil
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parents[2]
N=B/'runtime/scan55_surface_ground_v21';P=B/'runtime/scan54_height_retry_v17'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:p.read_bytes().decode()
def replace(s,old,new):
    assert s.count(old)==1,old[:100]
    return s.replace(old,new)
def main():
    assert not N.exists() and not (H/'prepared.json').exists()
    parent=json.loads((H.parent/'v20/manifest.json').read_text())
    for name,digest in parent['source_files'].items():assert sha(R/name)==digest,name
    N.mkdir();shutil.copytree(P/'src',N/'src')
    files={};before={}
    def edit(p,s):
        before[p]=p.read_bytes();files[p]=s
        dest=H/'parent_source'/p.relative_to(B);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(before[p])
    p=N/'src/plan_env/include/plan_env/raw_return_classification.h';s=read(p)
    s=replace(s,'double band_m) {','double band_m, bool allow_risers = true) {')
    s=replace(s,'  // Ground-relative height is signed.','  if (!allow_risers) return false;\n  // Ground-relative height is signed.')
    edit(p,s)
    p=N/'src/plan_env/include/plan_env/grid_map.h';s=read(p)
    anchor='  void reactiveTomogramCallback(sensor_msgs::msg::PointCloud2::ConstSharedPtr msg);'
    s=replace(s,anchor,anchor+'''
  reactive_stair::TerrainSnapshot decodeReactiveGround(sensor_msgs::msg::PointCloud2::ConstSharedPtr msg) const;
  void reactiveSurfaceGroundCallback(sensor_msgs::msg::PointCloud2::ConstSharedPtr msg);
  bool reactiveSurfaceGroundReady() const;''')
    anchor='  reactive_stair::TerrainSnapshot reactive_ground_; // Unscored positive ground evidence.'
    s=replace(s,anchor,anchor+'''
  // Broader floor evidence never authorizes risers or changes scored support.
  reactive_stair::TerrainSnapshot reactive_surface_ground_;
  std::string reactive_surface_ground_topic_;
  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr reactive_surface_ground_sub_;''')
    edit(p,s)
    p=N/'src/plan_env/include/plan_env/scan_reactive_grid_methods.inc';s=read(p)
    start=s.index('void GridMap::reactiveTomogramCallback');parse_start=s.index('  reactive_stair::TerrainSnapshot terrain;',start);parse_end=s.index('  reactive_stair::StepScoreResult scored',parse_start)
    parse=s[parse_start:parse_end]
    parse=parse.replace('    reactive_decision_.acceptTerrain(terrain);\n    return;','    return {};')
    parse=parse.replace('      reactive_decision_.acceptTerrain(terrain);\n      return;','      return {};')
    assert 'return;' not in parse and 'reactive_decision_' not in parse
    parser='''reactive_stair::TerrainSnapshot GridMap::decodeReactiveGround(sensor_msgs::msg::PointCloud2::ConstSharedPtr msg) const {
'''+parse+'  return terrain;\n}\n\n'
    callback='''void GridMap::reactiveTomogramCallback(sensor_msgs::msg::PointCloud2::ConstSharedPtr msg) {
  reactive_ground_ = reactive_stair::TerrainSnapshot{};
  reactive_cloud_ready_ = false;
  reactive_pending_cloud_ = false;
  reactive_terrain_hits_.clear();
  auto terrain = decodeReactiveGround(msg);
  if (terrain.cells.empty()) {
    reactive_decision_.acceptTerrain(terrain);
    return;
  }
'''
    s=s[:start]+parser+callback+s[parse_end:]
    start=s.index('bool GridMap::reactiveTerrainReturn');end=s.index('\nint GridMap::reactiveOccupancy',start)
    s=s[:start]+'''void GridMap::reactiveSurfaceGroundCallback(sensor_msgs::msg::PointCloud2::ConstSharedPtr msg) {
  reactive_surface_ground_ = decodeReactiveGround(msg);
  reactive_cloud_ready_ = false;
  reactive_pending_cloud_ = false;
}

bool GridMap::reactiveSurfaceGroundReady() const {
  if (reactive_surface_ground_topic_.empty()) return true;
  const auto &surface = reactive_surface_ground_;
  const double now = node_->now().seconds();
  return !reactive_ground_.cells.empty() && !surface.cells.empty() && surface.frame == mp_.frame_id_ &&
      std::isfinite(surface.stamp_s) && surface.stamp_s > 0.0 &&
      surface.stamp_s <= now && now - surface.stamp_s <= reactive_parameters_.terrain_max_age_s;
}

bool GridMap::reactiveTerrainReturn(const Eigen::Vector3d &point) const {
  if (reactive_stair::selectedGroundReturn(reactive_ground_,
          point.x(), point.y(), point.z(), reactive_terrain_band_m_)) return true;
  return !reactive_surface_ground_topic_.empty() && reactiveSurfaceGroundReady() &&
      reactive_stair::selectedGroundReturn(reactive_surface_ground_,
          point.x(), point.y(), point.z(), reactive_terrain_band_m_, false);
}
''' + s[end:]
    s=replace(s,'int GridMap::reactiveOccupancy(const Eigen::Vector3d &point) {','int GridMap::reactiveOccupancy(const Eigen::Vector3d &point) {\n  if (!reactiveSurfaceGroundReady()) return 1;')
    edit(p,s)
    p=N/'src/plan_env/src/grid_map.cpp';s=read(p)
    anchor='  load_parameter(node_, "grid_map.reactive_cost_limit", reactive_cost_limit_, 20.0);'
    s=replace(s,anchor,anchor+'\n  load_parameter(node_, "grid_map.reactive_surface_ground_topic", reactive_surface_ground_topic_, string(""));')
    anchor='      std::bind(&GridMap::reactiveTomogramCallback, this, std::placeholders::_1));'
    s=replace(s,anchor,anchor+'''
  if (!reactive_surface_ground_topic_.empty())
    reactive_surface_ground_sub_ = node_->create_subscription<sensor_msgs::msg::PointCloud2>(
        reactive_surface_ground_topic_, rclcpp::QoS(rclcpp::KeepLast(1)).reliable().transient_local(),
        std::bind(&GridMap::reactiveSurfaceGroundCallback, this, std::placeholders::_1));''')
    anchor='void GridMap::cloudCallback(sensor_msgs::msg::PointCloud2::ConstSharedPtr img)\n{\r\n'
    s=replace(s,anchor,anchor+'  if (!reactiveSurfaceGroundReady()) return;\n')
    edit(p,s)
    data=B/'inputs/new_building_uninflated_cost.npz';origin=B/'audits/2026-09-27_pct_raw_cost/raw_cost_observation.npz';assert not data.exists();shutil.copyfile(origin,data);data_sha=sha(data)
    p=B/'runtime_sources/bridge/lite3_sim_bridge/pct_sim_clock_core.py';s=read(p)
    anchor='\ndef selected_ground_points('
    func='''
SURFACE_COST_SHA = "'''+data_sha+'''"


def load_surface_cost(path: Path, source: dict) -> np.ndarray:
    """Read pinned uninflated PCT costs; preserve original navigation tensor."""
    if hashlib.sha256(path.read_bytes()).hexdigest() != SURFACE_COST_SHA:
        raise ValueError("PCT surface-cost source SHA-256 mismatch")
    with np.load(path, allow_pickle=False) as observed:
        generated = np.asarray(observed["generated"])
        stored = np.asarray(source["data"])
        raw = np.asarray(observed["raw_cost"])
        if generated.shape != stored.shape or generated.dtype != np.float16 or \\
           not np.array_equal(generated[[0, 3, 4]], stored[[0, 3, 4]], equal_nan=True) or \\
           not np.array_equal(observed["idx_simp"], [0, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13]) or \\
           raw.dtype != np.float32 or raw.shape != stored[0].shape or \\
           not np.isfinite(raw).all() or np.any(raw < 0.0) or np.any(raw > 50.0):
            raise ValueError("Uninflated costs do not match the original PCT generation")
        return raw.copy()


def surface_evidence_points(source: dict, elevations: np.ndarray, raw_cost: np.ndarray) -> np.ndarray:
    """Use original PCT cost/dedup selection before obstacle-distance inflation."""
    if raw_cost.shape != source["data"][0].shape or raw_cost.dtype != np.float32:
        raise ValueError("Invalid original PCT surface cost")
    shadow = dict(source)
    shadow["data"] = source["data"].copy()
    shadow["data"][0] = raw_cost.astype(np.float16)
    return selected_ground_points(shadow, paired_elevations=elevations)

'''
    s=replace(s,anchor,'\n'+func+anchor);edit(p,s)
    p=B/'runtime_sources/bridge/lite3_sim_bridge/pct_sim_clock_publisher.py';s=read(p)
    s=replace(s,'load_pinned_map, load_paired_elevations, selected_ground_points)','load_pinned_map, load_paired_elevations, selected_ground_points,\n                                load_surface_cost, surface_evidence_points)')
    s=replace(s,'topics = {"navigation_selected": "/pct_tomogram", "tracking_physical": "/tracker_ground"}','topics = {"navigation_selected": "/pct_tomogram", "tracking_physical": "/tracker_ground",\n                  "surface_evidence": "/pct_ground_surface"}')
    s=replace(s,'            if mode != "navigation_selected":','            if mode not in ("navigation_selected", "surface_evidence"):')
    start=s.index('        self._points = selected_ground_points');end=s.index('        self._point_sha',start);old=s[start:end]
    s=s[:start]+'''        surface_path = str(self.declare_parameter("surface_cost_path", "").value)
        if mode == "surface_evidence":
            if not surface_path or paired_elevations is None or coord_mode != "identity" or visual_offset != 0.03:
                raise ValueError("Surface evidence requires paired pinned Building data")
            self._points = surface_evidence_points(source, paired_elevations,
                                                   load_surface_cost(Path(surface_path), source))
        else:
            if surface_path:
                raise ValueError("Surface cost is only valid for the surface evidence topic")
'''+''.join('    '+line for line in old.splitlines(True))+s[end:]
    edit(p,s)
    p=B/'scripts/native_graph.py';s=read(p);anchor='        launch("pct_support", ground_args)'
    s=replace(s,anchor,anchor+'''
        if not flat:
            launch("pct_surface_ground", ground_args + ["-r", "__node:=pct_surface_ground_publisher",
                "-p", "ground_mode:=surface_evidence", "-p", "surface_cost_path:=" +
                str(BASE / "inputs/new_building_uninflated_cost.npz")])''');edit(p,s)
    for p,s in files.items():p.write_bytes(s.encode())
    from repair_review import apply
    apply()
    p=B/'setup/runtime_sources.json';r=json.loads(p.read_text());before[p]=p.read_bytes()
    for q in files:
        if 'runtime_sources' not in q.parts:continue
        rows=[x for x in r['records'] if x['path']==str(q.relative_to(B))];assert len(rows)==1
        row=rows[0];assert row['sha256']==hashlib.sha256(before[q]).hexdigest();row.setdefault('archived_sha256',row['sha256']);row.update(sha256=sha(q),bytes=q.stat().st_size,local_modification='v21 separate broader surface evidence from original selected-tread riser inference')
    p.write_text(json.dumps(r,indent=2)+'\n')
    p=B/'setup/source_identity.json';r=json.loads(p.read_text());before[p]=p.read_bytes();r['inputs'].append({'path':str(data.relative_to(B)),'sha256':data_sha,'bytes':data.stat().st_size,'source':'Unchanged pinned PCT CPU generator 1cf45a1c12ca785ce533293302be09d51daf0ccb, observed pre-inflation cost; audits/2026-09-27_pct_raw_cost/reproduce.py','claim':'Original inflated cost/ground/ceiling exactly reproduce archived map; only raw cost consumed for separate floor evidence'});p.write_text(json.dumps(r,indent=2)+'\n')
    for p,raw in before.items():
        dest=H/'parent_source'/p.relative_to(B)
        if not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
    (H/'changes.patch').write_text(''.join(''.join(difflib.unified_diff(raw.decode().splitlines(True),read(p).splitlines(True),fromfile='parent/'+str(p.relative_to(B)),tofile='v21/'+str(p.relative_to(B)))) for p,raw in before.items()))
    native={str(p.relative_to(N)):sha(p) for p in sorted((N/'src').rglob('*')) if p.is_file()};(N/'source_sha256.json').write_text(json.dumps(native,indent=2)+'\n')
    identity=B/'repairs/2026-09-26_generic_occupancy/candidate55_surface_ground_v21_identity.json';identity.write_text(json.dumps({'source_sha256':native,'integration_version':'v21','claim':'Unvalidated candidate: separate additional floor matching from selected-tread riser inference; unchanged query support. Runtime acceptance pending tests and user low-protrusion semantics.'},indent=2)+'\n')
    for name in ['building_planner.yaml','flat_planner.yaml']:shutil.copyfile(H.parent/'v20'/name,H/name)
    p=H/'building_planner.yaml';s=p.read_text();s=replace(s,'  ros__parameters:\n','  ros__parameters:\n    grid_map.reactive_surface_ground_topic: /pct_ground_surface\n');p.write_text(s)
    (H/'prepared.json').write_text(json.dumps({'native_build':str(N.relative_to(R)),'changed_files':[str(p.relative_to(R)) for p in before]+[str(data.relative_to(R)),str(identity.relative_to(R))],'raw_data_sha256':data_sha,'parent':'v20','status':'unfrozen_candidate'},indent=2)+'\n');print('v21 source prepared; not frozen or accepted')
if __name__=='__main__':main()

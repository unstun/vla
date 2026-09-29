from pathlib import Path
import hashlib,json,sys
root=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(exist_ok=True)
p=root/'src/bspline_opt/src/bspline_optimizer.cpp';source=p.read_text();header=root/'src/bspline_opt/include/bspline_opt/bspline_optimizer.h';h=header.read_text()
control=h[h.index('  class ControlPoints'):h.index('  class BsplineOptimizer')];(out/'native_control_points.inc').write_text(control)
start=source.index('    /*** Assign data to each segment ***/');end=source.index('  int BsplineOptimizer::earlyExit',start)
assign='std::vector<std::vector<Eigen::Vector3d>> BsplineOptimizer::assignTest() {\n auto &segment_ids=segments_; auto &final_segment_ids=final_segments_; auto &a_star_paths=paths_; bool occ;\n'+source[start:end]
start=source.index('  bool BsplineOptimizer::check_collision_and_rebound');end=source.index('  bool BsplineOptimizer::BsplineOptimizeTrajRebound',start)
(out/'native_blocks.inc').write_text(assign+source[start:end])
helper=root/'src/bspline_opt/include/bspline_opt/rebound_constraint_utils.h'
if helper.exists():(out/helper.name).write_bytes(helper.read_bytes())
(out/'source_identity.json').write_text(json.dumps({str(q):hashlib.sha256(q.read_bytes()).hexdigest() for q in [p,header,helper]},indent=2)+'\n')

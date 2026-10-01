"""Freeze one bounded retry using the existing native optimization modes."""
from datetime import datetime, timezone
from pathlib import Path
import difflib,hashlib,json,shutil
HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
ROOT=BASE.parents[2]
PARENT=BASE/'runtime/scan52_riser_ground_v15'
TARGET=BASE/'runtime/scan53_height_retry_v16'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def replace(p,old,new):
    before=p.read_text()
    if before.count(old)!=1:raise ValueError(f'Changed anchor {p}')
    after=before.replace(old,new);p.write_text(after)
    return ''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='v15/'+str(p.relative_to(TARGET)),tofile='v16/'+str(p.relative_to(TARGET))))
def main():
    parent=json.loads((HERE.parent/'v15/manifest.json').read_text())
    if TARGET.exists() or (HERE/'manifest.json').exists():raise FileExistsError('v16 is frozen')
    for name,digest in parent['source_files'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Parent changed: '+name)
    for manifest in ['source_sha256.json','install_sha256.json']:
        for name,digest in json.loads((PARENT/manifest).read_text()).items():
            if sha(PARENT/name)!=digest:raise ValueError('Native parent changed: '+name)
    TARGET.mkdir();shutil.copytree(PARENT/'src',TARGET/'src')
    changes=[]
    p=TARGET/'src/bspline_opt/include/bspline_opt/bspline_optimizer.h'
    anchor='  public:\n'
    before=p.read_text();assert before.count(anchor)>=1
    after=before.replace(anchor,anchor+'    bool optimizesHeight() const { return optimize_height_; }\n    void setOptimizeHeight(bool enabled) { optimize_height_ = enabled; }\n',1)
    p.write_text(after);changes.append(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='v15/'+str(p.relative_to(TARGET)),tofile='v16/'+str(p.relative_to(TARGET)))))
    p=TARGET/'src/plan_manage/include/plan_manage/planner_manager.h'
    changes.append(replace(p,'  private:\n','''  private:
    bool reboundReplanAttempt(Eigen::Vector3d start_pt, Eigen::Vector3d start_vel,
        Eigen::Vector3d start_acc, Eigen::Vector3d local_target_pt,
        Eigen::Vector3d local_target_vel, bool flag_polyInit, bool flag_randomPolyTraj,
        bool &optimization_attempted);
'''))
    p=TARGET/'src/plan_manage/src/planner_manager.cpp'
    anchor='''  bool SCANPlannerManager::reboundReplan(Eigen::Vector3d start_pt, Eigen::Vector3d start_vel,
                                        Eigen::Vector3d start_acc, Eigen::Vector3d local_target_pt,
                                        Eigen::Vector3d local_target_vel, bool flag_polyInit, bool flag_randomPolyTraj)
  {
'''
    replacement='''  bool SCANPlannerManager::reboundReplan(Eigen::Vector3d start_pt, Eigen::Vector3d start_vel,
                                        Eigen::Vector3d start_acc, Eigen::Vector3d local_target_pt,
                                        Eigen::Vector3d local_target_vel, bool flag_polyInit, bool flag_randomPolyTraj)
  {
    bool attempted = false;
    const int failures_before = continuous_failures_count_;
    if (reboundReplanAttempt(start_pt, start_vel, start_acc, local_target_pt,
                            local_target_vel, flag_polyInit, flag_randomPolyTraj, attempted)) return true;
    if (!attempted || !bspline_optimizer_rebound_->optimizesHeight()) return false;
    // Keep the configured three-axis behavior first. SCAN's existing fixed-Z
    // mode can retain a feasible stair seed when smoothing lowers its height.
    struct RestoreHeightMode {
      BsplineOptimizer &optimizer;
      bool enabled;
      ~RestoreHeightMode() { optimizer.setOptimizeHeight(enabled); }
    } restore{*bspline_optimizer_rebound_, bspline_optimizer_rebound_->optimizesHeight()};
    bspline_optimizer_rebound_->setOptimizeHeight(false);
    continuous_failures_count_ = failures_before;
    RCLCPP_INFO(node_->get_logger(), "fixed_height_recovery_attempt; full planning gates retained");
    const bool accepted = reboundReplanAttempt(start_pt, start_vel, start_acc, local_target_pt,
        local_target_vel, flag_polyInit, flag_randomPolyTraj, attempted);
    RCLCPP_INFO(node_->get_logger(), "fixed_height_recovery_result accepted=%d", accepted);
    return accepted;
  }

  bool SCANPlannerManager::reboundReplanAttempt(Eigen::Vector3d start_pt, Eigen::Vector3d start_vel,
                                        Eigen::Vector3d start_acc, Eigen::Vector3d local_target_pt,
                                        Eigen::Vector3d local_target_vel, bool flag_polyInit, bool flag_randomPolyTraj,
                                        bool &optimization_attempted)
  {
    optimization_attempted = false;
'''
    changes.append(replace(p,anchor,replacement))
    changes.append(replace(p,'    bool flag_step_1_success = bspline_optimizer_rebound_->BsplineOptimizeTrajRebound(ctrl_pts, ts);','    optimization_attempted = true;\n    bool flag_step_1_success = bspline_optimizer_rebound_->BsplineOptimizeTrajRebound(ctrl_pts, ts);'))
    native={str(p.relative_to(TARGET)):sha(p) for p in sorted((TARGET/'src').rglob('*')) if p.is_file()}
    (TARGET/'source_sha256.json').write_text(json.dumps(native,indent=2)+'\n')
    (HERE/'changes.patch').write_text(''.join(changes))
    for name in ['building_planner.yaml','flat_planner.yaml']:shutil.copyfile(HERE.parent/'v15'/name,HERE/name)
    selected={ROOT/name for name in parent['source_files']};selected.update(p for p in (TARGET/'src').rglob('*') if p.is_file());selected.add(TARGET/'source_sha256.json');selected.update(p for p in HERE.iterdir() if p.is_file())
    records={}
    for p in sorted(selected):
        name=str(p.relative_to(ROOT));records[name]=sha(p);dest=HERE/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    (HERE/'manifest.json').write_text(json.dumps({'version':'v16','parent':'v15','status':'frozen_unvalidated','frozen_utc':datetime.now(timezone.utc).isoformat(),'change':'Retry optimization-stage failures once using existing fixed-height mode and all complete planning gates','source_files':records,'changed_files':[str((TARGET/f).relative_to(ROOT)) for f in ['src/bspline_opt/include/bspline_opt/bspline_optimizer.h','src/plan_manage/include/plan_manage/planner_manager.h','src/plan_manage/src/planner_manager.cpp']],'native_build':str(TARGET.relative_to(ROOT)),'source_snapshot_prefix':'source/','acceptance_plan':'PLAN.md'},indent=2)+'\n')
    for folder in ['build','install']:shutil.copytree(PARENT/folder,TARGET/folder)
    print(json.dumps({'version':'v16','source_files':len(records)}))
if __name__=='__main__':main()

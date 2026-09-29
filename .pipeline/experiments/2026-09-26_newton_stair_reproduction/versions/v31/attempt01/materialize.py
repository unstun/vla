"""Preserve v30 and let SCAN refresh pose and scan inputs before each collision-deciding step.

v30_historical_full01 stopped and held on stale inputs. From saved inputs,
audits/2026-09-28_v30_stop_classes/RESULT.md shows the most likely cause:
- SCAN serves its planning and safety timers and the pose and scan
  subscriptions on one single-threaded executor, timers first, while /clock
  runs on its own thread;
- messages that arrive during a long planning callback wait, so the body pose
  passes the 0.1 s heading gate and the processed scan the 0.25 s StaleInput
  gate before a decision uses them.
Dr Sun chose option 1 on 2026-09-28: keep the inputs fresh while planning.

v31 keeps the single-threaded executor and every gate. GridMap gains
refreshSensorInputs(site): it takes the pending sensor_pose, cloud and
body_pose messages directly from their subscriptions and applies them through
the unchanged callbacks in stamp order. It is called at the start of the
planning and safety timers, before the route walk, at the start of each replan
attempt, at the start of each rebound round and before the final full-curve
check. The map therefore never changes inside a step.
"""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
OLD = BASE / "runtime/scan62_support_evidence_v30"
NEW = BASE / "runtime/scan63_input_refresh_v31"
HEADER = "src/plan_env/include/plan_env/grid_map.h"
GRID = "src/plan_env/src/grid_map.cpp"
FSM = "src/plan_manage/src/scan_replan_fsm.cpp"
MANAGER = "src/plan_manage/src/planner_manager.cpp"
OPTIMIZER = "src/bspline_opt/src/bspline_optimizer.cpp"
AUDIT = BASE / "audits/2026-09-28_v30_stop_classes"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()

HEADER_EDITS = [
    ("""  void logInitialSplineCollision(const Eigen::Vector3d &pos, double yaw);
""", """  void logInitialSplineCollision(const Eigen::Vector3d &pos, double yaw);
  // v31: take the pose and scan messages that arrived during a long callback
  // and apply them, in stamp order, through the unchanged callbacks. Call only
  // on the executor's thread, between collision-deciding steps.
  void refreshSensorInputs(const char *site);
"""),
]

GRID_EDITS = [
    ("""void GridMap::cloudCallback(sensor_msgs::msg::PointCloud2::ConstSharedPtr img)
{
""", """void GridMap::refreshSensorInputs(const char *site)
{
  // v31: SCAN serves its planning and safety timers and these subscriptions on
  // one single-threaded executor, timers first, while the simulation clock runs
  // on its own thread. Pose and scan messages that arrive during a long callback
  // therefore wait, and their age can pass the 0.1 s pose and 0.25 s scan limits
  // before a decision uses them. Take the pending messages here, on the same
  // thread, and apply them through the unchanged callbacks in stamp order (ties
  // in subscription creation order), so each collision-deciding step starts
  // from the newest received inputs. The limits and callbacks are unchanged.
  struct PendingInput
  {
    double stamp_s;
    int subscription;  // 0 sensor_pose, 1 cloud, 2 body_pose (creation order)
    nav_msgs::msg::Odometry::ConstSharedPtr pose;
    sensor_msgs::msg::PointCloud2::ConstSharedPtr cloud;
  };
  std::vector<PendingInput> pending;
  rclcpp::MessageInfo info;
  const auto take_poses = [&](const rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr &subscription,
                              int order) {
    if (!subscription) return;
    for (;;)
    {
      auto message = std::make_shared<nav_msgs::msg::Odometry>();
      if (!subscription->take(*message, info)) break;
      pending.push_back({rclcpp::Time(message->header.stamp).seconds(), order, message, nullptr});
    }
  };
  take_poses(lidar_pose_sub_, 0);
  if (cloud_sub_)
  {
    for (;;)
    {
      auto message = std::make_shared<sensor_msgs::msg::PointCloud2>();
      if (!cloud_sub_->take(*message, info)) break;
      pending.push_back({rclcpp::Time(message->header.stamp).seconds(), 1, nullptr, message});
    }
  }
  take_poses(sliding_map_frame_sub_, 2);
  if (pending.empty()) return;
  std::stable_sort(pending.begin(), pending.end(), [](const PendingInput &a, const PendingInput &b) {
    return a.stamp_s != b.stamp_s ? a.stamp_s < b.stamp_s : a.subscription < b.subscription;
  });
  const double now = node_->now().seconds();
  const double cloud_age = now - reactive_cloud_stamp_s_;
  const double body_age = now - reactive_body_stamp_s_;
  int applied[3] = {0, 0, 0};
  for (const PendingInput &input : pending)
  {
    ++applied[input.subscription];
    if (input.subscription == 0)
      sensorPoseCallback(input.pose);
    else if (input.subscription == 1)
      cloudCallback(input.cloud);
    else
      slidingMapFrameCallback(input.pose);
  }
  if ((applied[1] > 0 && cloud_age > 0.15) || (applied[2] > 0 && body_age > 0.05))
    RCLCPP_INFO(node_->get_logger(),
                "input_refresh site=%s sensor_poses=%d clouds=%d body_poses=%d cloud_age=%.4f->%.4f "
                "body_age=%.4f->%.4f cloud_ready=%d",
                site, applied[0], applied[1], applied[2], cloud_age, now - reactive_cloud_stamp_s_,
                body_age, now - reactive_body_stamp_s_, static_cast<int>(reactive_cloud_ready_));
}

void GridMap::cloudCallback(sensor_msgs::msg::PointCloud2::ConstSharedPtr img)
{
"""),
]

FSM_EDITS = [
    ("""  void SCANReplanFSM::execFSMCallback()
  {
    updateLocalTrajTimeFreeze();
""", """  void SCANReplanFSM::execFSMCallback()
  {
    // v31: start each planning-timer callback from the newest received inputs.
    planner_manager_->grid_map_->refreshSensorInputs("exec");
    updateLocalTrajTimeFreeze();
"""),
    ("""  void SCANReplanFSM::checkCollisionCallback()
  {
    updateLocalTrajTimeFreeze();
""", """  void SCANReplanFSM::checkCollisionCallback()
  {
    // v31: check the executing curve against the newest received inputs.
    planner_manager_->grid_map_->refreshSensorInputs("safety");
    updateLocalTrajTimeFreeze();
"""),
    ("""    for (int i = sample_num; i >= 0; --i)
    {
      const double t = duration * i / sample_num;
      const double prev_t = duration * std::max(0, i - 1) / sample_num;
""", """    // v31: the goal-neighbourhood search above can run for its 0.2 s wall-time
    // budget; walk the route with the newest received inputs.
    map->refreshSensorInputs("route_walk");
    for (int i = sample_num; i >= 0; --i)
    {
      const double t = duration * i / sample_num;
      const double prev_t = duration * std::max(0, i - 1) / sample_num;
"""),
]

MANAGER_EDITS = [
    ("""    optimization_attempted = false;

    static int count = 0;
""", """    optimization_attempted = false;
    // v31: each replan attempt starts from the newest received inputs.
    grid_map_->refreshSensorInputs("replan_start");

    static int count = 0;
"""),
    ("""    const auto collision_started = std::chrono::steady_clock::now();
    const auto collision = reactive_stair::checkFullCubicTrajectory(
""", """    // v31: judge the final curve against the newest received inputs.
    grid_map_->refreshSensorInputs("final_check");
    const auto collision_started = std::chrono::steady_clock::now();
    const auto collision = reactive_stair::checkFullCubicTrajectory(
"""),
]

OPTIMIZER_EDITS = [
    ("""    constexpr int MAX_RESART_NUMS_SET = 3;
    do
    {
      /* ---------- prepare ---------- */
""", """    constexpr int MAX_RESART_NUMS_SET = 3;
    do
    {
      /* ---------- prepare ---------- */
      // v31: each rebound round starts from the newest received inputs.
      grid_map_->refreshSensorInputs("rebound_round");
"""),
]

EDITS = ((HEADER, HEADER_EDITS), (GRID, GRID_EDITS), (FSM, FSM_EDITS), (MANAGER, MANAGER_EDITS),
         (OPTIMIZER, OPTIMIZER_EDITS))

parent = json.loads((HERE.parent / "v30/manifest.json").read_text())
assert not NEW.exists() and not (HERE / "prepared.json").exists()
for name, digest in parent["source_files"].items():
    assert sha(ROOT / name) == digest, name
native = json.loads((OLD / "source_sha256.json").read_text())
for name, digest in native.items():
    assert sha(OLD / name) == digest, name
diagnosis = {str(p.relative_to(ROOT)): sha(p) for p in [AUDIT / "RESULT.md", AUDIT / "timeline.json",
                                                         AUDIT / "scan_age_bounds.json", AUDIT / "summary.json"]}

shutil.copytree(OLD / "src", NEW / "src")
changes, preimages = [], {}
for relative, edits in EDITS:
    path = NEW / relative
    before = path.read_text()
    after = before
    for old, new in edits:
        assert after.count(old) == 1, (relative, old[:60])
        after = after.replace(old, new)
    path.write_text(after)
    preimages[relative] = before
    changes.append("".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                                fromfile="v30/" + relative, tofile="v31/" + relative)))
for relative, before in preimages.items():
    preimage = HERE / "parent_source" / relative
    preimage.parent.mkdir(parents=True, exist_ok=True)
    preimage.write_text(before)
(HERE / "changes.patch").write_text("".join(changes))

manifest = {str(p.relative_to(NEW)): sha(p) for p in sorted((NEW / "src").rglob("*")) if p.is_file()}
assert set(manifest) == set(native)
assert {name for name in manifest if manifest[name] != native[name]} == {relative for relative, _ in EDITS}
(NEW / "source_sha256.json").write_text(json.dumps(manifest, indent=2) + "\n")
identity = BASE / "repairs/2026-09-26_generic_occupancy/candidate63_input_refresh_v31_identity.json"
identity.write_text(json.dumps({
    "source_sha256": manifest, "integration_version": "v31",
    "parent": {"native_build": str(OLD.relative_to(ROOT)),
               **{relative: native[relative] for relative, _ in EDITS}},
    "diagnosis": diagnosis,
    "claim": "Unvalidated: GridMap::refreshSensorInputs takes pending sensor_pose, cloud and body_pose messages "
             "from their subscriptions and applies them in stamp order through the unchanged callbacks, at the "
             "start of the planning and safety timers, before the route walk, at the start of each replan attempt "
             "and rebound round, and before the final full-curve check. Single-threaded executor, input-age gates, "
             "QoS and all planner gates unchanged"},
    indent=2) + "\n")
for name in ("building_planner.yaml", "flat_planner.yaml"):
    shutil.copyfile(HERE.parent / "v30" / name, HERE / name)
(HERE / "prepared.json").write_text(json.dumps({
    "parent": "v30", "status": "unfrozen_candidate", "native_build": str(NEW.relative_to(ROOT)),
    "changed_files": [str((NEW / relative).relative_to(ROOT)) for relative, _ in EDITS] +
                     [str(identity.relative_to(ROOT))],
    "native_parent": str(OLD.relative_to(ROOT))}, indent=2) + "\n")
print(json.dumps({"v31": "native candidate prepared; acceptance pending",
                  "changed": [relative for relative, _ in EDITS]}))

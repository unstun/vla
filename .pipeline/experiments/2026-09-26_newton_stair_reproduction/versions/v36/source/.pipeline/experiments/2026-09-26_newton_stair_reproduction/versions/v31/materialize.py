"""Preserve v30 and let SCAN refresh pose and scan inputs before each collision-deciding step.

v30_historical_full01 stopped and held on stale inputs. From saved inputs,
audits/2026-09-28_v30_stop_classes/RESULT.md shows the most likely cause:
- SCAN serves its planning and safety timers and the pose and scan
  subscriptions on one single-threaded executor, timers first, while /clock
  runs on its own thread;
- messages that arrive during a long planning callback wait, so the body pose
  passes the 0.1 s heading gate and the processed scan the 0.25 s StaleInput
  gate before a decision uses them.
Dr Sun chose option 1 on 2026-09-28 (keep the inputs fresh while planning) and,
after the first independent review, kept this narrower means: take and apply
pending messages at safe points on the single-threaded executor, with bounded
planning left to a later version.

v31 keeps the single-threaded executor and every gate. GridMap gains
refreshSensorInputs(site): it takes the pending cloud, sensor_pose and
body_pose messages directly from their subscriptions and applies them through
the unchanged callbacks in stamp order. The FSM applies its own pending
body_pose messages (odom_pos_, odom_vel_) the same way at its two timers. The
refresh runs at the start of the planning and safety timers, at the start of
the global-target check, at the start of each replan attempt and rebound
round, and before the final full-curve check, so the map never changes inside
a step.

This is the second materialization (candidate scan64). The first (scan63,
kept in attempt01/) rewrote three CRLF files in text mode; this one edits
bytes, keeps every line ending and asserts that removing the inserted lines
gives back the v30 bytes exactly.
"""
from pathlib import Path
import difflib
import hashlib
import json
import re
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
OLD = BASE / "runtime/scan62_support_evidence_v30"
NEW = BASE / "runtime/scan64_input_refresh_v31"
HEADER = "src/plan_env/include/plan_env/grid_map.h"
GRID = "src/plan_env/src/grid_map.cpp"
FSM = "src/plan_manage/src/scan_replan_fsm.cpp"
MANAGER = "src/plan_manage/src/planner_manager.cpp"
OPTIMIZER = "src/bspline_opt/src/bspline_optimizer.cpp"
AUDIT = BASE / "audits/2026-09-28_v30_stop_classes"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()

# Each edit inserts lines between two adjacent anchors (either may be empty).
# Anchors match whatever line endings the file has there; the inserted lines take
# the ending of the anchor line they follow (or precede, when `before` is empty).
HEADER_EDITS = [
    ("""  void logInitialSplineCollision(const Eigen::Vector3d &pos, double yaw);
""", """  // v31: take the pose and scan messages that arrived during a long callback
  // and apply them, in stamp order, through the unchanged callbacks. Call only
  // on the executor's thread, between collision-deciding steps. fsm_odometry is
  // the number of FSM body_pose messages the caller applied just before (-1 if
  // the caller applies none); it is only logged.
  void refreshSensorInputs(const char *site, int fsm_odometry = -1);
""", """  double collisionSegmentYaw(const Eigen::Vector3d &from, const Eigen::Vector3d &to) const;
"""),
]

GRID_EDITS = [
    ("", """void GridMap::refreshSensorInputs(const char *site, int fsm_odometry)
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
  // Stamps are read as plain numbers here, so no stamp can throw. A failed take
  // is logged and ends that subscription's drain, as the executor's
  // take_and_do_error_handling logs and skips it.
  const auto stamp_s = [](const builtin_interfaces::msg::Time &stamp) {
    return static_cast<double>(stamp.sec) + 1e-9 * static_cast<double>(stamp.nanosec);
  };
  const auto take = [&](auto &subscription, auto message, int order, const char *topic) {
    try
    {
      if (!subscription->take(*message, info)) return false;
    }
    catch (const rclcpp::exceptions::RCLError &error)
    {
      RCLCPP_ERROR(node_->get_logger(), "input_refresh site=%s take from %s failed: %s", site, topic, error.what());
      return false;
    }
    if constexpr (std::is_same_v<decltype(message), std::shared_ptr<sensor_msgs::msg::PointCloud2>>)
      pending.push_back({stamp_s(message->header.stamp), order, nullptr, message});
    else
      pending.push_back({stamp_s(message->header.stamp), order, message, nullptr});
    return true;
  };
  // Reverse publication order: the bridge publishes each scan's sensor pose
  // before its cloud, so a pair that arrives during this drain cannot leave its
  // cloud taken without its pose (a delivery that reorders the two topics would
  // mispair them on the executor path as well).
  while (cloud_sub_ && take(cloud_sub_, std::make_shared<sensor_msgs::msg::PointCloud2>(), 1, "cloud")) {}
  while (lidar_pose_sub_ && take(lidar_pose_sub_, std::make_shared<nav_msgs::msg::Odometry>(), 0, "sensor_pose")) {}
  while (sliding_map_frame_sub_ &&
         take(sliding_map_frame_sub_, std::make_shared<nav_msgs::msg::Odometry>(), 2, "body_pose")) {}
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
  const double cloud_age_after = now - reactive_cloud_stamp_s_;
  const double body_age_after = now - reactive_body_stamp_s_;
  const std::string where(site);
  // Log every call at the sites inside a timer callback, which show how much the
  // inputs aged within a step; at the two timers, log a stale input applied or
  // any input stamped ahead of the clock (a freshness test reads it as stale).
  if ((where != "exec" && where != "safety") || (applied[1] > 0 && cloud_age > 0.15) ||
      (applied[2] > 0 && body_age > 0.05) || cloud_age_after < 0.0 || body_age_after < 0.0)
    RCLCPP_INFO(node_->get_logger(),
                "input_refresh site=%s sensor_poses=%d clouds=%d body_poses=%d fsm_odom=%d "
                "cloud_age=%.4f->%.4f body_age=%.4f->%.4f cloud_ready=%d",
                site, applied[0], applied[1], applied[2], fsm_odometry, cloud_age, cloud_age_after,
                body_age, body_age_after, static_cast<int>(reactive_cloud_ready_));
}

""", """void GridMap::cloudCallback(sensor_msgs::msg::PointCloud2::ConstSharedPtr img)
{
"""),
]

FSM_EDITS = [
    ("""    return node->get_parameter(name).get_value<T>();
  }
""", """
  // v31: take the FSM's pending body_pose messages and apply them through the
  // unchanged odometryCallback, so odom_pos_ and odom_vel_ are as fresh as the
  // map's body pose when a timer callback starts. A failed take is logged and
  // skipped, as on the executor path.
  template <typename Callback>
  int takePendingOdometry(const rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr &subscription,
                          const rclcpp::Logger &logger, Callback &&callback)
  {
    int applied = 0;
    rclcpp::MessageInfo info;
    while (subscription)
    {
      auto message = std::make_shared<nav_msgs::msg::Odometry>();
      try
      {
        if (!subscription->take(*message, info)) break;
      }
      catch (const rclcpp::exceptions::RCLError &error)
      {
        RCLCPP_ERROR(logger, "input_refresh take from body_pose (fsm) failed: %s", error.what());
        break;
      }
      callback(message);
      ++applied;
    }
    return applied;
  }
""", """} // namespace
"""),
    ("""  void SCANReplanFSM::execFSMCallback()
  {
""", """    // v31: start each planning-timer callback from the newest received inputs,
    // the FSM's own body_pose included.
    const int fsm_odometry = takePendingOdometry(
        odom_sub_, node_->get_logger(), [this](nav_msgs::msg::Odometry::ConstSharedPtr msg) { odometryCallback(msg); });
    planner_manager_->grid_map_->refreshSensorInputs("exec", fsm_odometry);
""", """    updateLocalTrajTimeFreeze();
"""),
    ("""  void SCANReplanFSM::checkCollisionCallback()
  {
""", """    // v31: check the executing curve against the newest received inputs, the
    // FSM's own body_pose included.
    const int fsm_odometry = takePendingOdometry(
        odom_sub_, node_->get_logger(), [this](nav_msgs::msg::Odometry::ConstSharedPtr msg) { odometryCallback(msg); });
    planner_manager_->grid_map_->refreshSensorInputs("safety", fsm_odometry);
""", """    updateLocalTrajTimeFreeze();
"""),
    ("""  bool SCANReplanFSM::adjustGlobalTargetIfOccupied()
  {
    auto map = planner_manager_->grid_map_;
""", """    // v31: check the target, search its neighbourhood and walk the route with the
    // newest received inputs; a route message reaches here without a timer.
    if (map) map->refreshSensorInputs("target_check");
""", """    auto &global_data = planner_manager_->global_data_;
"""),
]

MANAGER_EDITS = [
    ("""    optimization_attempted = false;
""", """    // v31: each replan attempt starts from the newest received inputs.
    grid_map_->refreshSensorInputs("replan_start");
""", """
    static int count = 0;
"""),
    ("", """    // v31: judge the final curve against the newest received inputs.
    grid_map_->refreshSensorInputs("final_check");
""", """    const auto collision_started = std::chrono::steady_clock::now();
    const auto collision = reactive_stair::checkFullCubicTrajectory(
"""),
]

OPTIMIZER_EDITS = [
    ("""    constexpr int MAX_RESART_NUMS_SET = 3;
    do
    {
      /* ---------- prepare ---------- */
""", """      // v31: each rebound round starts from the newest received inputs.
      grid_map_->refreshSensorInputs("rebound_round");
""", ""),
]

EDITS = ((HEADER, HEADER_EDITS), (GRID, GRID_EDITS), (FSM, FSM_EDITS), (MANAGER, MANAGER_EDITS),
         (OPTIMIZER, OPTIMIZER_EDITS))


def anchor_pattern(text):
    """A byte-exact pattern for text whose line endings may be LF or CRLF in the file."""
    return r"\r?\n".join(re.escape(part) for part in text.split("\n"))


def apply_edits(before, edits):
    """Insert every edit into `before` (bytes as surrogate-escaped str); return the text and insertions."""
    after, inserted = before, []
    for anchor_before, lines, anchor_after in edits:
        matches = list(re.finditer(anchor_pattern(anchor_before + anchor_after), after))
        assert len(matches) == 1, (anchor_before[:60], anchor_after[:60], len(matches))
        match = matches[0]
        split = match.start() + len(re.match(anchor_pattern(anchor_before), after[match.start():]).group(0))
        # The line ending of the anchor line the insertion follows, else of the one it precedes.
        if anchor_before:
            eol = "\r\n" if after[:split].endswith("\r\n") else "\n"
        else:
            first = re.match(r"[^\n]*\n", after[split:]).group(0)
            eol = "\r\n" if first.endswith("\r\n") else "\n"
        assert lines.endswith("\n")
        text = lines.replace("\n", eol)
        after = after[:split] + text + after[split:]
        inserted.append((split, text))
    return after, inserted


def without(after, inserted):
    """Remove the insertions again (latest first); must give back the parent bytes."""
    offsets, text = [], after
    for split, piece in inserted:
        # Later insertions shift earlier offsets only if they are before them.
        offsets = [(s + len(piece) if s >= split else s, p) for s, p in offsets] + [(split, piece)]
    for split, piece in sorted(offsets, reverse=True):
        assert text[split:split + len(piece)] == piece
        text = text[:split] + text[split + len(piece):]
    return text


parent = json.loads((HERE.parent / "v30/manifest.json").read_text())
assert not NEW.exists() and not (HERE / "prepared.json").exists()
for name, digest in parent["source_files"].items():
    assert sha(ROOT / name) == digest, name
native = json.loads((OLD / "source_sha256.json").read_text())
for name, digest in native.items():
    assert sha(OLD / name) == digest, name
diagnosis = {str(p.relative_to(ROOT)): sha(p) for p in
             [AUDIT / "RESULT.md", AUDIT / "timeline.json", AUDIT / "scan_age_bounds.json", AUDIT / "summary.json"] +
             sorted(AUDIT.glob("*/result.json")) + sorted(AUDIT.glob("*/result_fresh_pose.json"))}

shutil.copytree(OLD / "src", NEW / "src")
changes, preimages, line_endings = [], {}, {}
for relative, edits in EDITS:
    path = NEW / relative
    raw = path.read_bytes()
    before = raw.decode("utf-8", "surrogateescape")
    after, inserted = apply_edits(before, edits)
    assert without(after, inserted) == before, relative
    new_raw = after.encode("utf-8", "surrogateescape")
    added_cr = sum(piece.count("\r") for _, piece in inserted)
    assert new_raw.count(b"\r") == raw.count(b"\r") + added_cr, relative
    path.write_bytes(new_raw)
    preimages[relative] = raw
    line_endings[relative] = {"parent_crlf_lines": raw.count(b"\r\n"), "parent_lines": raw.count(b"\n"),
                              "inserted": ["CRLF" if piece.endswith("\r\n") else "LF" for _, piece in inserted]}
    changes.append("".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                                fromfile="v30/" + relative, tofile="v31/" + relative)))
for relative, raw in preimages.items():
    preimage = HERE / "parent_source" / relative
    preimage.parent.mkdir(parents=True, exist_ok=True)
    preimage.write_bytes(raw)
    assert sha(preimage) == native[relative], relative
(HERE / "changes.patch").write_bytes("".join(changes).encode("utf-8", "surrogateescape"))

manifest = {str(p.relative_to(NEW)): sha(p) for p in sorted((NEW / "src").rglob("*")) if p.is_file()}
assert set(manifest) == set(native)
assert {name for name in manifest if manifest[name] != native[name]} == {relative for relative, _ in EDITS}
(NEW / "source_sha256.json").write_text(json.dumps(manifest, indent=2) + "\n")
identity = BASE / "repairs/2026-09-26_generic_occupancy/candidate64_input_refresh_v31_identity.json"
identity.write_text(json.dumps({
    "source_sha256": manifest, "integration_version": "v31",
    "parent": {"native_build": str(OLD.relative_to(ROOT)),
               **{relative: native[relative] for relative, _ in EDITS}},
    "line_endings": line_endings,
    "diagnosis": diagnosis,
    "supersedes": {"native_build": ".pipeline/experiments/2026-09-26_newton_stair_reproduction/runtime/"
                                   "scan63_input_refresh_v31",
                   "record": ".pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v31/attempt01/"},
    "claim": "Unvalidated: GridMap::refreshSensorInputs takes pending cloud, sensor_pose and body_pose messages "
             "from their subscriptions and applies them in stamp order through the unchanged callbacks; the FSM "
             "applies its own pending body_pose messages at its two timers. Sites: the start of the planning and "
             "safety timers, of the global-target check, of each replan attempt and rebound round, and the final "
             "full-curve check. Single-threaded executor, input-age gates, QoS and all planner gates unchanged"},
    indent=2) + "\n")
for name in ("building_planner.yaml", "flat_planner.yaml"):
    assert (HERE / name).read_bytes() == (HERE.parent / "v30" / name).read_bytes(), name
(HERE / "prepared.json").write_text(json.dumps({
    "parent": "v30", "status": "unfrozen_candidate", "native_build": str(NEW.relative_to(ROOT)),
    "changed_files": [str((NEW / relative).relative_to(ROOT)) for relative, _ in EDITS] +
                     [str(identity.relative_to(ROOT))],
    "native_parent": str(OLD.relative_to(ROOT)),
    "superseded_candidate": "runtime/scan63_input_refresh_v31 (attempt01/)"}, indent=2) + "\n")
print(json.dumps({"v31": "native candidate scan64 prepared; acceptance pending", "line_endings": line_endings}))

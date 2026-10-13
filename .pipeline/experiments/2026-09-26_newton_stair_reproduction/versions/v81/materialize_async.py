"""Apply the declared single-writer mapping refactor to the exact v80 source."""
from pathlib import Path
import re
import shutil
import argparse

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
PARENT = BASE / 'runtime/scan83_map_loops_v80'
parser = argparse.ArgumentParser()
parser.add_argument('--destination', type=Path, default=BASE / 'runtime/scan84_async_map_v81')
DEST = parser.parse_args().destination
assert not DEST.exists()
shutil.copytree(PARENT / 'src', DEST / 'src')
env = DEST / 'src/plan_env'
header = env / 'include/plan_env/grid_map.h'
source = header.read_text()
names = ['mp_', 'md_', 'reactive_known_trunk_enabled_']
declarations = []
lines = source.splitlines(True)
for line in lines:
    if ('reactive_' in line or 'physical_floor_' in line) and ';' in line and '(' not in line.split('//')[0]:
        if any(token in line for token in ('Subscription', 'Publisher', 'diagnostic_force', 'body_stamp', 'body_quaternion')):
            continue
        if any(token in line for token in ('reactive_parameters_', 'reactive_decision_', 'reactive_terrain_',
            'reactive_ground_', 'reactive_navigation_ground_', 'reactive_surface_ground_', 'reactive_physical_floor_',
            'physical_floor_', 'reactive_step_result_', 'reactive_nonterrain_', 'reactive_cloud_',
            'reactive_pending_cloud_', 'reactive_tomogram_', 'reactive_cost_limit_', 'reactive_known_trunk_enabled_')):
            names += re.findall(r'\b(?:reactive_\w+_|physical_floor_\w+_)\b', line.split('//')[0])
names = sorted(set(names), key=len, reverse=True)
for line in lines:
    if any(re.search(r'\b' + name + r'\b', line.split('//')[0]) for name in names) and (
        line.lstrip().startswith(('MappingParameters ', 'MappingData ', 'bool ', 'double ', 'std::string ',
            'reactive_stair::', 'std::unordered_set<'))):
        declarations.append(line)
        source = source.replace(line, '', 1)
assert any('MappingParameters mp_' in line for line in declarations)
assert any('reactive_decision_' in line for line in declarations)
source = source.replace('GridMap() {}\n  ~GridMap() {}',
    'GridMap() : owned_state_(std::make_unique<GridMapState>()) {}\n  ~GridMap();')
source = source.replace('#include <unordered_set>', '#include <unordered_set>\n#include <atomic>\n#include <condition_variable>\n#include <deque>\n#include <map>\n#include <mutex>\n#include <thread>')

mutations = {'initMap', 'updateMapBoundaryFromIndex', 'rebuildInflationOffsets', 'resetAllMapData',
    'updateInflationLayer', 'updateInflation', 'applyOccupancyUpdate', 'resetCellByAddress',
    'resetCellByAddressForSliding', 'updateSlidingMap', 'resetBuffer', 'setCacheOccupancy',
    'projectDepthImage', 'raycastProcess', 'updateOccupancyCallback', 'depthPoseCallback',
    'sensorPoseCallback', 'slidingMapFrameCallback', 'cloudCallback', 'rescorePhysicalFloorChange',
    'reactivePhysicalFloorCallback', 'supportGround', 'reactiveTomogramCallback', 'reactiveSurfaceGroundCallback'}
pattern = re.compile(r'\b(' + '|'.join(map(re.escape, names)) + r')\b')
def refactor(text):
    text = pattern.sub(lambda match: 'mapState().' + match[0], text)
    matches = list(re.finditer(r'GridMap::(\w+)\s*\(', text))
    for match in reversed(matches):
        if match[1] not in mutations:
            continue
        start = text.index('{', match.end())
        depth, end = 1, start + 1
        while depth:
            depth += (text[end] == '{') - (text[end] == '}')
            end += 1
        text = text[:start] + text[start:end].replace('mapState().', 'mutableMapState().') + text[end:]
    return text

source = refactor(source)
state = 'struct GridMapState {\n' + ''.join(declarations) + '};\n\n'
source = source.replace('class GridMap {', state + 'class GridMap {')
source = source.replace('private:\n', '''private:
  const GridMapState &mapState() const { return read_state_ ? *read_state_ : *owned_state_; }
  GridMapState &mutableMapState() {
    if (read_state_ || async_mapping_) throw std::logic_error("Mutable access to a planner snapshot");
    return *owned_state_;
  }
  std::unique_ptr<GridMapState> owned_state_;
  std::shared_ptr<const GridMapState> read_state_;
  Eigen::Vector3d live_body_position_{Eigen::Vector3d::Zero()};
  Eigen::Vector3d queryBodyPosition() const { return async_mapping_ ? live_body_position_ : mapState().md_.sliding_map_frame_pos_; }
  struct MappingInput {
    int kind;
    int64_t stamp_ns;
    nav_msgs::msg::Odometry::ConstSharedPtr pose;
    sensor_msgs::msg::PointCloud2::ConstSharedPtr cloud;
  };
  struct MappingSnapshot {
    uint64_t revision = 0;
    std::shared_ptr<const GridMapState> state;
    double mapping_ms = 0.0, copy_ms = 0.0;
    uint64_t applied_clouds = 0;
  };
  struct AsyncMapping {
    std::mutex queue_mutex, publication_mutex;
    std::condition_variable wake;
    std::deque<MappingInput> queue;
    std::shared_ptr<const MappingSnapshot> latest;
    std::deque<std::shared_ptr<const GridMapState>> retired;
    std::thread worker;
    std::atomic<bool> stopping{false}, failed{false};
    std::string error;
  };
  std::shared_ptr<AsyncMapping> async_mapping_;
  uint64_t map_revision_ = 0;
  void enqueueMapping(MappingInput input);
  void adoptMappingSnapshotLocked();
  void adoptMappingSnapshot();
''', 1)
source = source.replace('  reactive_stair::PlanningProfile planning_profile_;', '''  class PublicationLease {
    std::shared_ptr<AsyncMapping> context_;
    std::unique_lock<std::mutex> lock_;
   public:
    explicit PublicationLease(std::shared_ptr<AsyncMapping> context)
      : context_(std::move(context)), lock_(context_->publication_mutex) {}
  };
  void startAsyncMapping();
  void stopAsyncMapping();
  bool mapperHealthy() const { return !async_mapping_ || !async_mapping_->failed.load(); }
  uint64_t mapRevision() const { return map_revision_; }
  std::unique_ptr<PublicationLease> beginPublication();
  reactive_stair::PlanningProfile planning_profile_;''')
# Forward declaration is private, matching its full definition.
source = source.replace('class GridMap {\npublic:', 'class GridMap {\n  struct AsyncMapping;\npublic:')
header.write_text(source)
for file in (env / 'src/grid_map.cpp', env / 'include/plan_env/scan_reactive_grid_methods.inc'):
    text = refactor(file.read_text())
    file.write_text(text)

cpp = env / 'src/grid_map.cpp'
text = cpp.read_text()
# Start only after every original parameter, publisher and callback is ready.
init = text.index('void GridMap::initMap')
start = text.index('{', init)
depth, end = 1, start + 1
while depth:
    depth += (text[end] == '{') - (text[end] == '}')
    end += 1
text = text[:end-1] + '''
  bool asynchronous_mapping = false;
  load_parameter(node_, "grid_map.asynchronous_mapping", asynchronous_mapping, false);
  if (asynchronous_mapping) startAsyncMapping();
''' + text[end-1:]
wraps = {'sensorPoseCallback': (0, 'pose_msg'), 'cloudCallback': (1, 'img'),
         'slidingMapFrameCallback': (2, 'pose')}
for method, (kind, argument) in wraps.items():
    start = text.index('{', text.index('void GridMap::' + method)) + 1
    special = ''
    if kind == 2:
        special = '''
    const auto &p = pose->pose.pose.position;
    live_body_position_ = Eigen::Vector3d(p.x,p.y,p.z);
    const auto &q = pose->pose.pose.orientation;
    Eigen::Quaterniond rotation(q.w,q.x,q.y,q.z);
    const double stamp = rclcpp::Time(pose->header.stamp).seconds();
    reactive_body_stamp_s_ = 0.0;
    if (std::isfinite(stamp) && stamp>0.0 && live_body_position_.allFinite() &&
        rotation.coeffs().allFinite() && rotation.norm()>1e-6) {
      reactive_body_stamp_s_=stamp; reactive_body_quaternion_=rotation.normalized();
    }
'''
    value = 'nullptr, ' + argument if kind == 1 else argument + ', nullptr'
    wrapper = '\n  if (async_mapping_) {' + special + '\n    enqueueMapping({' + str(kind) + ', rclcpp::Time(' + argument + '->header.stamp).nanoseconds(), ' + value + '});\n    return;\n  }\n'
    text = text[:start] + wrapper + text[start:]
start = text.index('{', text.index('void GridMap::updateOccupancyCallback')) + 1
text = text[:start] + '\n  if (async_mapping_) { adoptMappingSnapshot(); return; }\n' + text[start:]
start = text.index('{', text.index('void GridMap::visCallback')) + 1
text = text[:start] + '\n  adoptMappingSnapshot();\n' + text[start:]
text = text.replace('  const double cloud_age_after =', '  adoptMappingSnapshot();\n  const double cloud_age_after =')
text += '\n#include <plan_env/async_mapping_methods.inc>\n'
cpp.write_text(text)
inc = env / 'include/plan_env/scan_reactive_grid_methods.inc'
text = inc.read_text().replace('mapState().md_.sliding_map_frame_pos_', 'queryBodyPosition()')
for method, kind in [('reactiveTomogramCallback',3), ('reactiveSurfaceGroundCallback',4), ('reactivePhysicalFloorCallback',5)]:
    start = text.index('{', text.index('void GridMap::' + method)) + 1
    text = text[:start] + '\n  if (async_mapping_) { enqueueMapping({' + str(kind) + ', rclcpp::Time(msg->header.stamp).nanoseconds(), nullptr, msg}); return; }\n' + text[start:]
for method, value in [('bodyEndpointMayBeObserved','false'), ('reactiveOccupancy','1')]:
    start = text.index('{', text.index('GridMap::' + method)) + 1
    text = text[:start] + '\n  if (!mapperHealthy()) return ' + value + ';\n' + text[start:]
inc.write_text(text)
shutil.copyfile(HERE / 'async_mapping_methods.inc', env / 'include/plan_env/async_mapping_methods.inc')

manager = DEST / 'src/plan_manage/src/planner_manager.cpp'
text = manager.read_text().replace('    GridMap::RawContributorCacheScope raw_cache_scope(*grid_map_);',
    '    publication_lease_.reset();\n    GridMap::RawContributorCacheScope raw_cache_scope(*grid_map_);')
text = text.replace('    const auto collision_started =', '    auto publication_lease = grid_map_->beginPublication();\n    const auto collision_started =')
text = text.replace('    continuous_failures_count_ = 0;\n    return true;',
    '    continuous_failures_count_ = 0;\n    publication_lease_ = std::move(publication_lease);\n    return true;')
manager.write_text(text)
manager = DEST / 'src/plan_manage/include/plan_manage/planner_manager.h'
text = manager.read_text().replace('    GridMap::Ptr grid_map_;',
    '    GridMap::Ptr grid_map_;\n    std::unique_ptr<GridMap::PublicationLease> publication_lease_;')
manager.write_text(text)
fsm = DEST / 'src/plan_manage/src/scan_replan_fsm.cpp'
text = fsm.read_text().replace('      bspline_pub_->publish(bspline);',
    '      bspline_pub_->publish(bspline);\n      planner_manager_->publication_lease_.reset();')
fsm.write_text(text)
from share_support import share_support
share_support(env)
print('V81_ASYNC_MATERIALIZED', len(names), 'state members')

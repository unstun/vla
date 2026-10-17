"""Build a self-contained, source-backed Chinese navigation architecture report.

Reads the frozen v196 implementation and local evidence only. It never starts
navigation or changes experiment files. Run from any directory with Python 3.
"""
from pathlib import Path
import hashlib
import json
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
BASE = Path('.pipeline/experiments/2026-09-26_newton_stair_reproduction')
V = BASE / 'versions/v196'

SOURCES = {}


def source(key, title, path, anchor=None, count=45):
    path = Path(path)
    raw = (ROOT / path).read_bytes()
    lines = raw.decode().splitlines()
    start = next((i for i, line in enumerate(lines) if anchor in line), None) if anchor else 0
    if start is None:
        raise ValueError(f'Missing source anchor: {path}: {anchor}')
    end = min(len(lines), start + count)
    SOURCES[key] = dict(title=title, path=str(path), start=start + 1, end=end,
                        sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw),
                        excerpt='\n'.join(f'{i+1:4}  {lines[i]}' for i in range(start, end)))


source('launch', '实际启动图与条件分支', V/'native_graph.py', '    try:', 115)
source('run', 'Mac 完整路线的实际启动参数', V/'run_mac_full.py', 'def main', 85)
source('mission', '任务、目标与 PCT 服务归属', V/'src/lite3_nav2_bridge/lite3_nav2_bridge/mission_bridge.py', 'class MissionBridge', 58)
source('cache', '同任务路线缓存与终点绑定', V/'src/lite3_nav2_bridge/lite3_nav2_bridge/mission_bridge.py', '    def _retain_cached_path', 126)
source('bt', 'Nav2 行为树：1 Hz 规划、跟踪、Wait 重试', V/'src/lite3_nav2_bridge/config/navigate.xml', count=30)
source('profile', '运行时 Nav2 参数覆盖与代价地图配置', V/'src/lite3_nav2_bridge/lite3_nav2_bridge/profile.py', 'def write_profile', 80)
source('pct_plugin', 'PCT Nav2 插件实际调用服务', V/'src/lite3_nav2_plugins/src/pct_planner.cpp', '  nav_msgs::msg::Path createPlan', 38)
source('pct_core', 'PCT：tomogram、A* 与 GPMP 优化接口', BASE/'runtime_sources/pct_runtime/python/pct_planner/planner_wrapper.py', '    def plan(', 36)
source('pct_native', '可直接链接的 PCT 原生规划接口', Path('references/upstream/2026-09-16_lite3_isaac_harness_backend/source/pct_global/src/pct/pct_planner/lib/src/ele_planner/offline_ele_planner.h'), count=90)
source('pct_conversion', 'PCT 原包装层的坐标与 Z 偏移转换', BASE/'runtime_sources/pct_runtime/python/pct_planner/utils/convertion.py', count=90)
source('global_map', '固定全局地图与支撑覆盖修正身份', V/'global_map_input.json', count=30)
source('scan_config', '实际 SCAN 配置与异步地图参数', V/'building_planner.yaml', count=95)
source('mapper', '异步地图队列、淘汰与快照', V/'src/plan_env/include/plan_env/async_mapping_methods.inc', 'void GridMap::enqueueMapping', 98)
source('worker', '嵌入式 SCAN 工作线程与地形切片', V/'src/scan_nav2_controller/src/controller.cpp', 'class NativeWorker', 100)
source('setplan', '路线更新与紧急样条接收', V/'src/scan_nav2_controller/src/controller.cpp', 'void Controller::setPlan', 59)
source('control', '直接速度输出、等待与超时', V/'src/scan_nav2_controller/src/controller.cpp', 'geometry_msgs::msg::TwistStamped Controller::computeVelocityCommands', 96)
source('goalcheck', '到达判定：位置、朝向、实际速度', V/'src/scan_nav2_controller/src/controller.cpp', 'bool GoalChecker::isGoalReached', 18)
source('stop_speed', 'Nav2 停止速度门槛', V/'src/scan_nav2_controller/src/controller.cpp', 'bool stoppedVelocity', 7)
source('controller_config', '控制器频率与进展检查', V/'src/scan_nav2_controller/config/controller.yaml', count=34)
source('tracking', '轨迹跟踪、航向冻结与机体系速度', V/'src/scan_nav2_controller/include/scan_nav2_controller/tracking_node.hpp', '  void cmdCallback()', 78)
source('timers', 'SCAN FSM 与安全检查定时器', V/'src/plan_manage/src/scan_replan_fsm.cpp', '    exec_timer_', 24)
source('schedule', '局部规划调度：跳过错过的节拍', V/'src/plan_manage/src/scan_replan_fsm.cpp', '  bool SCANReplanFSM::nominalReplanDue', 56)
source('recovery', 'SCAN 内部紧急停止与恢复', V/'src/plan_manage/src/scan_replan_fsm.cpp', '    case EMERGENCY_STOP:', 55)
source('restart', '旧曲线采样与实测里程计重启', V/'src/plan_manage/src/scan_replan_fsm.cpp', '  bool SCANReplanFSM::planFromCurrentTraj', 39)
source('safety', '执行中曲线检查与安全重规划', V/'src/plan_manage/src/scan_replan_fsm.cpp', '  void SCANReplanFSM::checkCollisionCallback', 51)
source('optimizer', '热启动、图搜索与优化回退', V/'src/plan_manage/src/planner_manager.cpp', '  bool SCANPlannerManager::reboundReplan(', 65)
source('terrain', 'Nav2 TerrainLayer 的 0.25 秒时效判定', V/'src/lite3_nav2_plugins/src/terrain_layer.cpp', count=70)
source('bridge_config', '传输桥参数与指令时效', BASE/'config_archived/bridge.yaml', count=50)
source('bridge', '桥接器：指令过期与发布', BASE/'runtime_sources/bridge/lite3_sim_bridge/foxy_bridge_node.py', '    def _command_loop', 49)
source('transport', '实际 TCP 流式传输实现', BASE/'runtime_sources/bridge/lite3_sim_bridge/transport.py', 'class CommandReceiverServer', 62)
source('clock', '跨主机单调时钟映射与失效置零', BASE/'scripts/bridge_adapter.py', count=70)
source('physics', 'Newton 物理循环、仿真定位与几何传感', V/'newton_episode.py', '    elif request.get("scene") == "building_full":', 62)
source('policy', '实际沿用的 V40 物理控制与 ONNX 接口', BASE/'versions/v40/physics/lite3_newton_v40.py', 'def make_session', 45)
source('stance', 'RL 与 PD 站立模式定义', Path('.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/stance_hold.py'), 'STANCE_HOLD_FSM_MODES', 32)
source('driver', '独立终局验证：到达后 PD 保持两秒', V/'long_route_driver.py', '        deadline = time.monotonic() + scenario', 45)
source('contract', '继承的导航配置合同，版本字段仍为 v59', V/'navigation_contract.json', count=40)
source('result', 'v196 完整路线验收原始 JSON', V/'results/v196_mac_full_attempt01/full_route_verification.json', count=52)
source('report', 'v196 实测及证据边界', V/'results/v196_mac_full_attempt01/RESULTS.md', count=72)
source('display', 'v197 仅重放显示，不执行物理', BASE/'versions/v197/VISUAL_QA.md', count=55)
source('refactor_wire', 'v198：新增真实执行状态接口', BASE/'versions/v198/src/lite3_nav2_interfaces/msg/RobotExecutionState.msg', count=35)
source('refactor_bridge', 'v198：TCP 执行状态转为 ROS，保留原采样时间', BASE/'versions/v198/runtime/bridge/lite3_sim_bridge/foxy_bridge_node.py', '    def _publish_execution_state', 40)
source('refactor_completion', 'v200：连续两秒 PD 站稳与独立截止时间', BASE/'versions/v200/src/scan_nav2_controller/include/scan_nav2_controller/terminal_completion.hpp', count=110)
source('refactor_server', 'v200：终点进度豁免与唯一速度出口', BASE/'versions/v200/src/nav2_controller/src/nav2_controller.cpp', 'void ControllerServer::checkProgress', 85)
source('refactor_bt', 'v200：失败直接退出，不再 Wait 重跑', BASE/'versions/v200/src/lite3_nav2_bridge/config/navigate.xml', count=25)
source('refactor_checks', 'v200：组件构建与回归记录', BASE/'versions/v200/verification/summary.json', count=23)
source('refactor_pct_plugin', 'v201：PCT 插件直接调用原生规划器', BASE/'versions/v201/src/lite3_nav2_plugins/src/pct_planner.cpp', '  nav_msgs::msg::Path createPlan', 45)
source('refactor_pct_native', 'v201：坐标、楼层与优化器高度迁移', BASE/'versions/v201/src/lite3_nav2_plugins/src/pct_route_planner.cpp', 'Eigen::Vector3i PCTRoutePlanner::poseToIndex', 61)
source('refactor_mission', 'v201：任务入口只保留 action 适配', BASE/'versions/v201/src/lite3_nav2_bridge/lite3_nav2_bridge/mission_bridge.py', 'class MissionBridge', 40)
source('refactor_pct_checks', 'v201：固定输入与插件回归记录', BASE/'versions/v201/verification/summary.json', count=25)

source('refactor_motion', 'v202：LocalMotion 对外接口与状态归属', BASE/'versions/v202/src/scan_nav2_controller/include/scan_nav2_controller/local_motion.hpp', count=70)
source('refactor_exchange', 'v202：有界快照、取消与迟到结果隔离', BASE/'versions/v202/src/scan_nav2_controller/include/scan_nav2_controller/motion_exchange.hpp', count=80)
source('refactor_worker_direct', 'v202：SCAN 工作线程直接读取输入', BASE/'versions/v202/src/scan_nav2_controller/src/local_motion.cpp', '  void consumeInput()', 17)
source('refactor_native_io', 'v202：完成样条直接回调与原生取消', BASE/'versions/v202/src/plan_manage/src/scan_replan_fsm.cpp', '  void SCANReplanFSM::publishSpline', 30)
source('refactor_motion_checks', 'v202：LocalMotion 构建与回归记录', BASE/'versions/v202/verification/summary.json', count=27)

source('refactor_terrain_bundle', 'v203：统一地形清单与静态输入绑定', BASE/'versions/v203/src/lite3_nav2_bridge/lite3_nav2_bridge/terrain_bundle.py', 'class TerrainBundle', 77)
source('refactor_static_pub', 'v203：一个节点加载并发布三种地形', BASE/'versions/v203/src/lite3_nav2_bridge/lite3_nav2_bridge/static_terrain.py', 'class StaticTerrain', 49)
source('refactor_map_profile', 'v203：最小地图外壳与统一配置', BASE/'versions/v203/src/lite3_nav2_bridge/lite3_nav2_bridge/profile.py', '    for key in', 21)
source('refactor_map_graph', 'v203：统一静态节点、删除闲置恢复服务', BASE/'versions/v203/src/lite3_nav2_bridge/launch/navigation.launch.py', '    return [', 22)
source('refactor_map_checks', 'v203：地形、生命周期和组件回归记录', BASE/'versions/v203/verification/summary.json', count=25)

source('restore_policy', 'v204：导航层终点与旧路线策略', BASE/'versions/v204/src/lite3_nav2_plugins/include/lite3_nav2_plugins/route_policy.hpp', count=125)
source('restore_tree', 'v204：普通重试恢复，1 Hz 不变', BASE/'versions/v204/src/lite3_nav2_bridge/config/navigate.xml', count=30)
source('restore_failure', 'v204：按 FollowPath 身份区分站稳超时', BASE/'versions/v204/src/lite3_nav2_plugins/include/lite3_nav2_plugins/recovery_bt.hpp', count=80)
source('restore_session', 'v204：只传任务元数据，不调用规划服务', BASE/'versions/v204/src/lite3_nav2_bridge/lite3_nav2_bridge/mission_bridge.py', '    def _session_ready', 30)
source('restore_checks', 'v204：行为恢复检查结果', BASE/'versions/v204/RESULTS.md', count=90)

source('physical_v204', 'v204：完整物理路线通过与性能对照', BASE/'versions/v204/results/v204_mac_full_attempt01/RESULTS.md', count=90)
source('physical_v204_gate', 'v204：原完整路线验收记录', BASE/'versions/v204/results/v204_mac_full_attempt01/full_route_verification.json', count=45)



source('continuity_exchange', 'v206：普通刷新保留同目标局部结果', BASE/'versions/v206/src/scan_nav2_controller/include/scan_nav2_controller/motion_exchange.hpp', count=85)
source('continuity_tracker', 'v206：航向回差与到期样条制动', BASE/'versions/v206/src/scan_nav2_controller/include/scan_nav2_controller/tracking_node.hpp', '  void cmdCallback()', 110)
source('continuity_slew', 'v206：独立指令时钟与三轴斜率限幅', BASE/'versions/v206/src/scan_nav2_controller/include/scan_nav2_controller/command_slew.hpp', count=80)
source('continuity_plan', 'v206：修复与远端验证边界', BASE/'versions/v206/PLAN.md', count=80)


source('continuity_checks', 'v206：5070ti 构建与独立回归结果', BASE/'versions/v206/RESULTS.md', count=85)

source('physical_v206', 'v206：终点站稳超时的实际物理结果', BASE/'versions/v206/results/v206_linux_full_attempt02/RESULTS.md', count=80)
source('stance_diagnosis', 'v206：记录回放定位承重准入阻塞', BASE/'audits/2026-10-15_v206_terminal_settle/REPORT.md', count=100)
source('stance_return_v208', 'v208：身体和关节安静后平滑接管', BASE/'versions/v208/stance_hold.py', '        if self.mode == "STAND_SETTLING":', 79)
source('stance_checks_v208', 'v208：两组短时物理对照与验证边界', BASE/'versions/v208/RESULTS.md', count=125)

def node(id, name, subtitle, tag, pos, role, inputs, outputs, state, caveat, refs):
    return dict(id=id, name=name, subtitle=subtitle, tag=tag, pos=pos, role=role,
                inputs=inputs, outputs=outputs, state=state, caveat=caveat, refs=refs)


NODES = [
    node('mission','任务入口','目标、取消、任务身份','任务层',[0,0],
         '接收数值目标，绑定 request_id / goal_id，向 Nav2 发起 NavigateToPose。当前完整路线由实验 driver 提交，不由语言模型决定目标。',
         ['HTTP /goal、/cancel、/state','world 坐标目标；地图 epoch / revision'],
         ['NavigateToPose action','任务终态与 canonical_goal_pose'],
         'MissionBridge 保存 current_owner、jobs、目标缓存；HTTP 线程只入队，ROS executor 负责 action 调用。',
         'VLA 接入点属于后续集成；本轮没有语言指令到目标的闭环。',['mission','cache','driver']),
    node('bt','Nav2 任务调度','全局刷新、FollowPath、Wait','行为树',[1,0],
         '组织全局规划和路线跟踪，接收 action 成功或失败；失败时执行 Wait 并重试。Nav2 是任务编排者，局部几何求解仍由 SCAN 完成。',
         ['NavigateToPose','planner / controller / progress 的结果'],
         ['ComputePathToPose：配置 1 Hz','FollowPath；失败后 Wait 1 s，最多 6 次重试'],
         '行为树状态、action 生命周期；SimpleProgressChecker 另外检查 10 s 内是否移动 0.5 m。',
         '实际配置只启用 Wait recovery；不能把通用 Nav2 的 Spin / BackUp 自动算进此系统。',['bt','profile','controller_config']),
    node('pct','PCT 全局规划','选楼层、选通路、给参考路径','配置 1 Hz',[2,0],
         'PCT 插件调用 MissionBridge 的 PlanRoute 服务；Python 包装层在固定分层地图上调用原生 A* 与优化器，返回带高度的 world Path。',
         ['当前位置 + 任务目标','固定 tomogram / coverage 修正地图'],
         ['nav_msgs/Path → Nav2 FollowPath','/pct_planned_path：诊断发布'],
         '同任务缓存最后有效路线；首次成功绑定规范终点，后续刷新保持其完整位姿。',
         '全局 PCT 没有直接读取实时 LiDAR 或 Nav2 costmap 的障碍栅格。临时障碍主要由局部层处理。',['pct_plugin','pct_core','cache','global_map']),
    node('static','静态地图与支撑','分层地图、表面、物理地面','预先生成',[3,0],
         '同一个 Building 存在不同用途的地图产物：全局可通行代价、地面高度/表面、物理地面与支撑覆盖。它们不能互换。',
         ['固定 Building 场景资料','各产物 SHA-256 / 来源身份'],
         ['PCT 的 coverage 修正 map.pickle','/pct_tomogram、/pct_ground_surface、/pct_physical_floor'],
         '静态来源身份和不同高度语义；global_map_input.json 指定运行时固定地图。',
         '几何上“有地板”不代表机器人身体可通行；局部自由空间也不能替代落脚支撑证据。',['launch','global_map','scan_config']),
    node('map','SCAN 局部地图','点云融合、支撑、碰撞查询','异步快照',[0,1],
         '点云与传感器位姿按源时间配对；后台写地图，规划读取完成的不可变 revision。使用观察时间窗口，积压可过期或因容量而淘汰。',
         ['/quad_0/cloud + /quad_0/lidar_pose','身体姿态；静态地面/支撑证据'],
         ['局部 3D 占据与支撑查询','不可变快照 → SCAN；terrain_slice → Nav2 costmap'],
         '地图 revision、源时间、配对队列、覆盖与支撑状态。配置：0.05 m 分辨率，10×10×5 m 滑动窗口。',
         '配置 100 Hz 是地图更新节拍；不代表 100 Hz 新激光帧。观察窗口 0.5 s、容量 64，点云年龄门槛另为 0.35 s。',['mapper','scan_config','worker','terrain']),
    node('scan','SCAN 局部规划','局部目标 → 搜索/优化 → 样条','目标 30 Hz',[1,1],
         '沿 PCT 参考路径选择局部目标，尝试复用曲线或图搜索种子，优化三次 B-spline，并检查碰撞、支撑与动力学可行性。',
         ['/pct_path：控制插件转交的参考路径','地图快照、里程计、execution_frozen'],
         ['/quad_0/planning/bspline','emergency_stop 样条与诊断'],
         'SCAN FSM、参考路径前沿、局部 trajectory id / start_time、热启动绑定与失败计数。',
         '代码里的 global_data 是 SCAN 内部参考曲线，不是另一个地图级全局规划器。局部窗口结束不等于任务到达。',['restart','optimizer','safety','schedule']),
    node('control','SCAN 跟踪控制器','样条采样 → 机体系速度','配置 30 Hz',[2,1],
         'Nav2 controller 插件接收 Path，转发给嵌入式 SCAN worker；读取样条并执行前馈 + 位置/航向反馈，直接发布 Twist。',
         ['FollowPath / setPlan','三次 B-spline、身体位姿与速度'],
         ['/quad_0/cmd_vel：vx、vy、wz','/pct_path；execution_frozen 反馈'],
         'has_active_plan、waiting_for_spline、goal_braking、exec_time 与终点锁定。相同路径几何刷新不重复发布，等样条/几何变化时发布。',
         '无曲线先发零速度，默认等 5 s 后失败；紧急样条清除当前曲线。此版本是 direct Nav2 Twist，没有旧 P2B 的 measured-stop 交接协议。',['setplan','control','tracking','goalcheck']),
    node('bridge','ROS ↔ 仿真桥','指令时效、双云、时钟映射','TCP',[3,1],
         '把 ROS Twist 通过 TCP 指令通道送到 Mac；把新物理状态/双云帧发布成 ROS topic 与 /clock。另有单调时钟同步通道。',
         ['Twist；物理 BODY_STATE / SENSOR_FRAME','两端 monotonic clock 估计'],
         ['24601 指令；24600 遥测','24602 时钟同步；ROS body_pose / cloud / clock'],
         '源指令时间、序列、连接状态、时钟偏移与不确定度；过期/失同步置零。',
         '代码实际使用 socket TCP；旧记录中的 ZeroMQ 名称不能直接套用。桥配置 source command timeout 为 0.25 s。',['transport','bridge','bridge_config','clock']),
    node('sense','定位与几何 LiDAR','来自实际仿真状态','仿真输入',[0,2],
         '使用 Newton 的身体位姿与几何射线扫描，生成同一采集时刻的点云和传感器位姿；向导航回传实际运动。',
         ['物理场景、机器人位姿','原始传感器安装变换'],
         ['/quad_0/body_pose、/quad_0/lidar_pose','/quad_0/cloud、/quad_0/cloud_raw、/clock'],
         '采集时刻、扫描序号、身体状态序号；异步扫描保留采集时的状态。',
         '定位是仿真真值，不是已验证的 SLAM。最新 building_full 分支 human=None，启动参数关闭移动聚类 tracker；本轮不证明动态行人避障。',['physics','launch','run']),
    node('terrain','Nav2 地形适配','3D 局部地图 → 2D 切片','兼容层',[1,2],
         '把 SCAN 地图在当前身体高度附近投影为 OccupancyGrid，供 Nav2 的 global/local costmap 使用。',
         ['SCAN 最新已完成地图','身体 Z 与 world→base TF'],
         ['/nav2_scan/terrain_slice','TerrainLayer + InflationLayer'],
         '切片源时间、当前层高、costmap current 标志。',
         '切片 0.25 s freshness 与 SCAN 0.35 s cloud freshness 不同；代码差异已确认，对停顿的因果影响仍需单独验证。',['worker','terrain','profile']),
    node('physics','Newton 物理仿真','关节力矩 → 接触 → 新状态','配置 1000 Hz',[2,2],
         '执行机器人刚体/关节与 Building 接触，返回真实积分后的姿态、速度和传感输入。Mac 采用 CPU Newton / SolverMuJoCo 路径。',
         ['关节 PD 力矩与接触场景','冻结的机器人、地图与模型资产'],
         ['新身体/关节状态','接触与视频状态；actual applied-command 证据'],
         '一个连续物理状态与原生仿真时间；latest run 的初始状态至终点连续保存。',
         'v197 是对已保存状态的可视化重放，执行零个物理步。视频 FPS 不代表求解频率。',['physics','policy','contract','display']),
    node('policy','V12 行走 / PD 站立','机体速度 → 关节目标 / 力矩','策略 50 Hz',[3,2],
         '既有 V12 ONNX 策略把速度命令与历史观测转换为 12 个关节动作；符合站立条件后，状态机把关节控制交给 PD hold。',
         ['经时效检查的 vx、vy、wz','关节、姿态、速度与观测历史'],
         ['12 维动作与关节 PD 力矩','stance_mode、policy_owns_joints'],
         'RL → STAND_SETTLING → STAND_TRANSITION → FIXED_STAND → REJOIN；启动另有 factory PD 流程。',
         '发零速度不等于立刻停稳；Nav2 到达、实际低速度、PD 保持是三层不同证据。',['policy','stance','driver','goalcheck']),
]

EDGES = [
    ['mission','bt','任务','command','right','left',0],
    ['bt','pct','规划','command','right','left',0],
    ['static','pct','地图','data','left','right',0],
    ['pct','control','Path / FollowPath','command','bottom','top',0],
    ['map','scan','查询','data','right','left',0],
    ['scan','control','样条','command','right','left',0],
    ['control','scan','/pct_path + freeze','feedback','top','top',-45],
    ['control','bridge','速度','command','right','left',0],
    ['bridge','policy','有效速度命令','command','bottom','top',0],
    ['policy','physics','力矩','command','left','right',0],
    ['physics','sense','实际状态 → 感知','feedback','bottom','bottom',45],
    ['sense','map','点云 + 同刻位姿','data','top','bottom',0],
    ['map','terrain','身体高度切片','data','bottom','top',0],
    ['static','map','静态地面 / 支撑','data','bottom','top',24],
]

RISKS = [
 dict(id='map', title='全局通路可行 ≠ 局部身体可通过', type='已确认的职责边界',
      chain=['PCT 固定分层地图','路径进入狭窄/边缘区域','SCAN 碰撞或支撑检查拒绝','重规划、停止或恢复'],
      fact='PCT 服务使用固定 coverage 修正地图；SCAN 另用实时 3D 占据、身体包络与支撑证据。两者没有共享一份完全相同的可行域。',
      risk='只放宽某一层的障碍判断，可能让全局路线更容易生成，却把无法执行的片段交给局部层。',
      proof='冻结同一失败位姿、同一地图 revision 和同一参考路径，分别回放 PCT 与 SCAN 查询；比较楼层、身体高度和支撑分类。', refs=['global_map','pct_core','scan_config','safety']),
 dict(id='refresh', title='全局刷新会改变局部规划状态', type='已确认的跨层状态路径',
      chain=['1 Hz 全局刷新','setPlan / canonical goal','参考路径与轨迹绑定变化','局部重新初始化或等待样条'],
      fact='v196 区分同目标、相同路径几何与新路径；同几何且已有曲线时不重发 /pct_path，等待曲线时仍会重发。',
      risk='只追求“每秒有新路径”，可能反复触发局部重规划；只缓存旧路径，又可能保留已经不能执行的路线。',
      proof='覆盖相同几何、几何变化、同终点新路线、owner 变化、取消与等待恢复；同时核对 Path 发布、轨迹 id 与有效执行曲线。', refs=['bt','cache','setplan','restart']),
 dict(id='clock', title='计算变慢会同时触发多个时效门槛', type='代码事实；具体因果待验证',
      chain=['求解 / 调度延迟','地图或指令年龄增加','安全门槛拒绝 / 指令置零','无进展检查 / 恢复重试'],
      fact='SCAN cloud_age=0.35 s；TerrainLayer slice_age=0.25 s；桥指令超时=0.25 s。ROS 仿真时间、两端 monotonic 时间和曲线执行相位并存。',
      risk='提高规划频率可能增加争用；放宽一个超时可能只把失效转移到另一个门槛。切片年龄差异是否实际导致本轮停顿，尚未证明。',
      proof='同一事件记录 capture→fusion→snapshot→plan→Twist→RL 的时间、时钟域与 revision，定位第一个失效点，而非只看最后的 timeout。', refs=['scan_config','terrain','bridge_config','clock','schedule']),
 dict(id='recover', title='局部恢复与任务恢复同时存在', type='已确认的多层状态机',
      chain=['SCAN 发现执行曲线不可用','EMERGENCY_STOP / 内部重规划','控制器等样条，超时抛错','Nav2 Wait 后重试整个任务链'],
      fact='SCAN 有自己的 GEN/REPLAN/EXEC/EMERGENCY 状态；controller 有 waiting_for_spline；Nav2 有进展检查与六次 Wait 重试。',
      risk='只增加局部重试次数，可能更长时间占住上层等待；只让上层快速重试，也可能反复重置局部恢复状态。',
      proof='记录最先失败的状态、清曲线与零命令时刻、恢复来源、路径/样条身份及实际恢复位移；区分 SCAN 内部恢复与 Nav2 Wait。', refs=['recovery','control','bt','controller_config']),
 dict(id='stop', title='局部结束、任务到达、站稳不能共用一个“成功”', type='已确认的不同验收语义',
      chain=['局部样条末端 2 cm','任务终点 XY / Z / yaw','Nav2 实测低速度判定','driver 再检查 PD hold 2 s'],
      fact='运行 profile 把局部 finish_dist 设为 0.02 m；任务 XY 容差 0.25 m。Nav2 GoalChecker 看实测速度，driver 另外要求 FIXED_STAND。',
      risk='调大局部终点阈值可能提前结束脱困动作；把零命令当作停车，会掩盖 RL 的实际漂移。',
      proof='同时看实际 policy input、身体位移、Nav2 终态、stance_mode 与 policy_owns_joints；不要从一个布尔值推断全部通过。', refs=['profile','tracking','stop_speed','goalcheck','driver']),
 dict(id='version', title='目录版本、依赖版本与证据版本并不一致', type='已确认的继承关系',
      chain=['v196 局部源码','v176 二进制 underlay + 历史运行库','v40 物理实现 + 继承配置','v196 物理记录 / v197 展示'],
      fact='当前物理入口导入 v40/physics；navigation_contract.json 的 version 字段仍为 v59；v197 不执行新物理。最新源码不等于所有模块全部重写。',
      risk='只按最大版本号或旧报告判断当前架构，容易把旧 P2B gate、旧地图 FIFO 契约或视频成功算进当前行为。',
      proof='以实际 launcher、生成参数、加载库与源文件哈希组成依赖清单；每个结论绑定具体 run，而不是只绑定目录名。', refs=['physics','contract','control','report','display']),
]

SCENARIOS = [
 dict(name='正常导航',desc='参考路径持续可用，局部曲线通过检查；以下是调用关系示意，不是实时仿真。',steps=[
  ['MissionBridge','绑定任务与数值目标','mission'],['Nav2 / PCT','请求全局路径；后续按 1 Hz 刷新','pct'],['SCAN','读取快照，生成局部样条','scan'],['Controller','采样曲线，输出机体系 Twist','control'],['桥 / V12','检查时效，执行关节动作','policy'],['Newton / LiDAR','产生实际位姿、点云并反馈','sense']]),
 dict(name='局部曲线被拒绝',desc='安全检查先尝试局部重规划；接近碰撞或非法曲线可进入 EMERGENCY_STOP。',steps=[
  ['SCAN safety','检查执行中剩余曲线','scan'],['SCAN FSM','重规划；必要时 EMERGENCY_STOP','scan'],['Controller','收到 emergency 样条，清曲线并发零','control'],['SCAN recovery','满足速度条件后尝试生成新轨迹','scan'],['Controller','收到合法新曲线后继续；无曲线超时则失败','control']]),
 dict(name='等待曲线超时',desc='这是上层失败与重试路径，与 SCAN 内部恢复分开。',steps=[
  ['Controller','无曲线，输出零速度','control'],['Controller','等待超过 5 s：stop + PlannerException','control'],['Nav2','FollowPath 失败，Wait 1 s','bt'],['Nav2 / PCT','重试规划与跟踪，最多六次恢复重试','pct']]),
 dict(name='全局刷新暂时失败',desc='缓存只对当前任务/目标生效；没有历史有效路线的首次规划不能借此通过。',steps=[
  ['Nav2','触发新的 ComputePathToPose','bt'],['MissionBridge / PCT','得到声明范围内的可回退错误','pct'],['MissionBridge','校验 owner/goal，深拷贝旧 Path','mission'],['Controller','同几何时保留曲线；等待时重新发布参考路径','control']]),
 dict(name='终点与站立',desc='路径结束、Nav2 arrived 与物理 PD hold 分别判定。',steps=[
  ['Tracker','进入终点位置范围，调整最终 yaw','control'],['GoalChecker','位置 / yaw / 实测低速度通过','control'],['MissionBridge','记录 arrived；释放任务 owner','mission'],['V12 / stance','在零命令与站立条件下进入 FIXED_STAND','policy'],['Driver','确认实际停稳 + PD hold 2 s','physics']]),
]

html = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lite3 · 导航系统架构</title>
<style>
:root{--bg:#f4f6f8;--paper:#fff;--ink:#14202e;--muted:#617184;--line:#dce3eb;--blue:#235bd1;--teal:#087e82;--amber:#a45e12;--soft:#edf3ff;--red:#a84036;font-family:Inter,-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;color-scheme:light}
*{box-sizing:border-box}body{margin:0;color:var(--ink);background:var(--bg);font-size:14px;line-height:1.65}button,input,select{font:inherit}button{cursor:pointer}a{color:var(--blue)}button:focus-visible,a:focus-visible,select:focus-visible,input:focus-visible{outline:3px solid #86abff;outline-offset:3px}button{transition:background .15s,border-color .15s}header{background:#111f30;color:white;padding:26px 36px 22px}.eyebrow{font-size:11px;letter-spacing:.15em;color:#99adc5;text-transform:uppercase}h1{font-size:28px;letter-spacing:-.02em;line-height:1.3;margin:8px 0 10px;font-weight:650}header p{margin:0;color:#b9c8da;max-width:940px}header .meta{display:flex;flex-wrap:wrap;gap:16px;margin-top:16px;color:#d4dfec;font-size:12px}.meta span+span{border-left:1px solid #405166;padding-left:16px}.shell{max-width:1760px;margin:auto}.tabs{display:flex;gap:28px;padding:0 36px;background:white;border-bottom:1px solid var(--line);overflow-x:auto}.tab{background:none;border:0;border-bottom:3px solid transparent;color:var(--muted);font-weight:600;white-space:nowrap;padding:18px 0 15px}.tab[aria-selected=true]{color:var(--blue);border-bottom-color:var(--blue)}main{padding:28px 36px 44px}.lead{display:flex;justify-content:space-between;align-items:start;gap:28px;margin-bottom:22px}h2{font-size:21px;margin:0 0 6px;line-height:1.4}h3{font-size:16px;line-height:1.45;margin:0 0 10px}h4{margin:18px 0 7px;font-size:12px;letter-spacing:.04em;color:var(--muted)}p{margin:0 0 12px}.muted{color:var(--muted)}.tiny{font-size:12px}.lead p{color:var(--muted);max-width:950px;margin:0}.quiet{border:1px solid var(--line);padding:8px 12px;background:white;border-radius:6px;color:var(--ink)}.legend{display:flex;gap:18px;flex-wrap:wrap;font-size:12px;color:var(--muted);margin:15px 0}.legend i{display:inline-block;width:24px;border-top:2px solid var(--blue);vertical-align:middle;margin-right:7px}.legend .data{border-color:var(--teal)}.legend .feedback{border-color:var(--amber);border-top-style:dashed}.overview>div,.panel,.table-scroll,.risk-detail,.risk-menu{min-width:0}.overview{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:24px;align-items:start}.graph-wrap{background:white;border:1px solid var(--line);border-radius:9px;padding:18px 14px 12px}.graph-top{display:flex;justify-content:space-between;gap:16px;align-items:center;padding:0 6px;color:var(--muted);font-size:12px}.graph-top select{border:1px solid var(--line);padding:5px;background:white;border-radius:5px;color:var(--ink)}.graph{position:relative;height:625px;min-width:650px}.graph-scroll{overflow:auto;max-width:100%}.graph svg{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}.edge{fill:none;stroke:var(--blue);stroke-width:1.5}.edge.data{stroke:var(--teal)}.edge.feedback{stroke:var(--amber);stroke-dasharray:5 4}.edge.dim{opacity:.12}.edge-label{font-size:10px;fill:#55677d;paint-order:stroke;stroke:white;stroke-width:5px;stroke-linejoin:round}.edge-label.dim{opacity:.15}.node{position:absolute;width:21.3%;min-height:111px;text-align:left;background:#fff;border:1px solid #ced8e3;border-radius:7px;padding:13px 12px;color:var(--ink)}.node:hover{background:#f6f9ff;border-color:#95b0e4}.node.selected{background:#edf3ff;border-color:var(--blue);box-shadow:0 0 0 1px var(--blue)}.node-name{display:block;font-weight:650;font-size:14px;line-height:1.35}.node-sub{font-size:11px;display:block;color:var(--muted);margin-top:6px;line-height:1.5}.node-tag{display:block;font-size:10px;color:var(--blue);margin-top:8px}.node[data-id=map] .node-tag,.node[data-id=sense] .node-tag,.node[data-id=static] .node-tag{color:var(--teal)}.band-label{position:absolute;left:0;right:0;border-top:1px dashed #e7ebf1;color:#8a96a4;font-size:10px;padding-top:6px;pointer-events:none}.inspector{background:white;border:1px solid var(--line);border-radius:8px;padding:21px;min-height:630px;max-height:none}.inspector .tag{font-size:11px;color:var(--blue);margin-bottom:7px}.inspector h2{font-size:20px}.inspector ul{padding-left:18px;margin:0}.inspector p,.inspector li{font-size:13px}.note{border-left:3px solid #d69a50;background:#fff8ee;padding:11px 13px;font-size:12px;margin:18px 0;color:#725024}.source-chip{border:0;background:#f0f3f7;color:#35537e;border-radius:4px;padding:4px 7px;font-size:11px;margin:3px 4px 3px 0;text-align:left;max-width:100%;overflow-wrap:anywhere}.source-chip:hover{background:#e4ecfa}.bottom-line{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;margin-top:23px;padding:20px 0;border-top:1px solid var(--line)}.bottom-line strong{display:block;font-size:14px;margin-bottom:5px}.bottom-line p{font-size:12px;color:var(--muted);margin:0}.table-scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;background:white}th,td{padding:16px 18px;text-align:left;vertical-align:top;border-bottom:1px solid var(--line);font-size:13px}th{font-size:12px;background:#eef2f7;color:#516275;font-weight:600}td strong{display:block;margin-bottom:4px}td small{display:block;color:var(--muted);font-size:12px;margin-top:7px}code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.88em;overflow-wrap:anywhere}.split{display:grid;grid-template-columns:1fr 1fr;gap:28px;margin-top:26px}.panel{background:white;border:1px solid var(--line);border-radius:8px;padding:23px}.flow-list{list-style:none;padding:0;margin:15px 0}.flow-list li{padding:13px 0 13px 38px;position:relative;border-bottom:1px solid #edf0f4}.flow-list li::before{content:attr(data-n);position:absolute;left:0;top:15px;color:var(--blue);font-size:12px;font-weight:700}.flow-list strong{display:block;margin-bottom:4px}.flow-list span{color:var(--muted);font-size:13px}.scope-list{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-top:24px}.scope-list>div{padding:18px 0;border-top:2px solid var(--line)}.scope-list p{font-size:13px;color:var(--muted)}.scenario-bar{display:flex;gap:8px;flex-wrap:wrap;margin:18px 0}.scenario-bar button{border:1px solid var(--line);background:white;border-radius:6px;padding:8px 12px;color:var(--muted)}.scenario-bar button[aria-pressed=true]{background:var(--soft);border-color:var(--blue);color:var(--blue)}.steps{display:flex;gap:10px;align-items:stretch;flex-wrap:wrap;margin:18px 0 0;counter-reset:steps}.step{flex:1;min-width:140px;border-top:3px solid #cbd8ed;background:white;padding:16px;position:relative}.step::before{counter-increment:steps;content:counter(steps,decimal-leading-zero);font-size:11px;color:var(--blue);display:block;margin-bottom:10px}.step strong{display:block;font-size:13px;margin-bottom:7px}.step p{font-size:12px;color:var(--muted);margin:0}.state-box{padding:16px 0;border-bottom:1px solid var(--line)}.state-box:last-child{border:0}.state-box p{font-size:13px;color:var(--muted)}.risk-layout{display:grid;grid-template-columns:270px minmax(0,1fr);gap:26px}.risk-menu{display:flex;flex-direction:column;gap:6px}.risk-menu button{border:1px solid transparent;background:transparent;color:var(--ink);text-align:left;padding:13px;border-radius:6px;font-size:13px}.risk-menu button[aria-pressed=true]{background:white;border-color:#b8ccec;color:var(--blue)}.risk-menu button span{display:block;color:var(--muted);font-size:11px;margin-bottom:4px}.risk-detail{background:white;border:1px solid var(--line);border-radius:8px;padding:25px}.risk-detail .chain{display:flex;gap:8px;margin:22px 0;align-items:center;flex-wrap:wrap}.chain span{padding:9px 12px;background:#f1f5fa;font-size:12px}.chain b{color:#8494a8;font-weight:400}.risk-detail dl{display:grid;grid-template-columns:92px 1fr;gap:16px 20px;margin:0}.risk-detail dt{color:var(--muted);font-size:12px}.risk-detail dd{margin:0;font-size:14px}.rules{margin-top:26px;border-top:1px solid var(--line);padding-top:22px}.rules ol{padding-left:20px;color:var(--muted);font-size:13px}.rules li{margin:8px 0}.evidence-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:22px;margin:25px 0}.metric{border-left:2px solid #b4c6e3;padding-left:16px}.metric .value{font-size:26px;font-weight:650;line-height:1.5}.metric .label{font-size:12px;color:var(--muted)}.search{width:100%;max-width:480px;border:1px solid var(--line);background:white;padding:10px 12px;border-radius:5px;margin:12px 0}.source-list{display:grid;grid-template-columns:1fr 1fr;gap:0 24px}.source-row{padding:14px 0;border-bottom:1px solid var(--line);min-width:0}.source-row button{background:none;border:0;padding:0;color:var(--blue);text-align:left;font-weight:600}.source-row code{display:block;font-size:11px;color:var(--muted);margin-top:5px;word-break:break-all}.status{font-size:11px;color:var(--teal);background:#eaf6f2;padding:3px 6px;border-radius:4px;white-space:nowrap}.status.pending{background:#fff1df;color:#995d12}.provenance{font-size:12px;color:var(--muted);padding-top:24px;margin-top:25px;border-top:1px solid var(--line)}dialog{border:1px solid #b8c5d4;border-radius:10px;width:min(1000px,94vw);padding:0;max-height:88vh;box-shadow:0 24px 100px #0a182c33}dialog::backdrop{background:#0d1b2c80}dialog .dialog-head{padding:20px 24px;border-bottom:1px solid var(--line);display:flex;gap:16px;justify-content:space-between;align-items:start}dialog .dialog-head h3{margin-bottom:5px}dialog .dialog-body{padding:20px 24px}dialog pre{overflow:auto;font-size:12px;line-height:1.65;background:#f4f6f9;padding:18px;margin:16px 0 0;max-height:53vh}dialog .path{word-break:break-all;font-size:12px;color:var(--muted)}[hidden]{display:none!important}.mobile-hint{display:none}.subtle-title{color:var(--teal);font-size:11px;font-weight:700;letter-spacing:.07em;margin-bottom:8px}.keypoint{font-size:13px;color:var(--muted);margin:14px 0 0}.pill{color:#bcd2ed;font-size:11px;border:1px solid #3d536b;padding:3px 7px;border-radius:4px}
@media(min-width:1500px){.overview{grid-template-columns:minmax(0,1fr) 355px}.graph{height:655px}.node{min-height:119px}.node-name{font-size:16px}.node-sub{font-size:12px}.edge-label{font-size:11px}}
@media(max-width:1130px){.overview{grid-template-columns:minmax(0,1fr)}.inspector{min-height:0}.graph{min-width:720px}.source-list{grid-template-columns:1fr}.inspector ul{display:flex;flex-wrap:wrap;gap:5px 28px}.scope-list{grid-template-columns:repeat(2,1fr)}}
@media(max-width:680px){header{padding:24px 20px}.tabs{padding:0 20px;gap:22px}main{padding:24px 20px}h1{font-size:25px}.lead{display:block}.lead .quiet{margin-top:12px}.split,.bottom-line,.risk-layout{grid-template-columns:1fr}.evidence-grid{grid-template-columns:repeat(2,1fr)}.risk-menu{flex-direction:row;overflow:auto}.risk-menu button{min-width:210px}.risk-detail{padding:18px}.risk-detail dl{grid-template-columns:1fr;gap:6px}.risk-detail dd{margin-bottom:14px}.scope-list{grid-template-columns:1fr}.graph-wrap{padding:12px 8px}.mobile-hint{display:block;color:var(--muted);font-size:11px}.graph{min-width:730px}.step{min-width:calc(50% - 10px)}th,td{min-width:155px;padding:12px}.source-list{grid-template-columns:1fr}}
@media print{header{background:white;color:black}.tabs,.quiet,.graph-top select{display:none}main{padding:12px}[role=tabpanel][hidden]{display:block!important;break-before:page}.overview,.risk-layout{grid-template-columns:1fr}.inspector{min-height:0}.graph{height:620px}.panel{break-inside:avoid}header p,header .meta{color:#555}}
</style></head><body><header><div class="shell"><div class="eyebrow">Lite3 research / architecture review</div><h1>Lite3 导航系统架构</h1><p>全局规划、局部规划、状态与执行的当前实现图。每个模块都有输入输出和来源，连锁故障单独展开。</p><div class="meta"><span>实现快照 <b>v196</b> · 展示版本 v197</span><span>实验与分析 · 2026-10-14</span><span>Mac ARM64 / Foxy / Newton</span><span class="pill">代码梳理 · 非新实验</span></div></div></header>
<div class="shell"><nav class="tabs" role="tablist" aria-label="架构视图">
<button class="tab" id="tab-overview" role="tab" aria-controls="overview" aria-selected="true">01 系统总览</button>
<button class="tab" id="tab-planning" role="tab" aria-controls="planning" aria-selected="false">02 全局与局部</button>
<button class="tab" id="tab-state" role="tab" aria-controls="state" aria-selected="false">03 状态与时钟</button>
<button class="tab" id="tab-risk" role="tab" aria-controls="risk" aria-selected="false">04 连锁故障</button>
<button class="tab" id="tab-evidence" role="tab" aria-controls="evidence" aria-selected="false">05 证据与边界</button>
<button class="tab" id="tab-target" role="tab" aria-controls="target" aria-selected="false">06 目标重构</button></nav>
<main><section id="overview" role="tabpanel" aria-labelledby="tab-overview">
<div class="lead"><div><h2>当前运行的是一套分层几何导航闭环</h2><p>PCT 决定走哪条通路，SCAN 生成眼前可执行的曲线，Nav2 管任务与恢复，V12 / PD 驱动身体。视觉语言层尚未接入这条完整路线。</p></div><button class="quiet" data-open-tab="risk">查看连锁故障 →</button></div>
<div class="overview"><div><div class="graph-wrap"><div class="graph-top"><span>逻辑模块（非进程边界）· 点击查看源码</span><label>连线 <select id="edge-filter" aria-label="过滤架构连线"><option value="all">全部关系</option><option value="command">任务与执行</option><option value="data">地图与感知</option><option value="feedback">状态反馈</option></select></label></div><div class="legend"><span><i></i>任务 / 路径 / 命令</span><span><i class="data"></i>地图 / 传感输入</span><span><i class="feedback"></i>状态反馈</span></div><p class="mobile-hint">图可横向滚动；每个模块均可点击。</p><div class="graph-scroll"><div class="graph" id="graph" aria-label="导航模块架构"><svg id="edges" aria-hidden="true"></svg></div></div><p class="keypoint">位置与时间是共享依赖：body_pose / TF / clock 同时进入任务、规划和控制。为避免交叉遮挡，图中未逐条重复绘制；详见「状态与时钟」。</p></div><div class="bottom-line"><div><strong>全局地图 ≠ 局部地图</strong><p>预先生成的分层通路，与实时占据/支撑证据承担不同判断。</p></div><div><strong>局部恢复 ≠ 任务恢复</strong><p>SCAN FSM、控制器等待与 Nav2 Wait 各有状态和超时。</p></div><div><strong>零命令 ≠ 实际站稳</strong><p>指令、身体速度和关节 PD 接管需要分别检查。</p></div></div></div><aside class="inspector" id="inspector" aria-live="polite"></aside></div>
</section>
<section id="planning" role="tabpanel" aria-labelledby="tab-planning" hidden>
<div class="lead"><div><h2>两个规划器回答的是不同问题</h2><p>分清地图尺度、输出形式和失败归属，才知道一个参数修改会影响哪条链。</p></div></div>
<div class="table-scroll"><table><thead><tr><th>职责</th><th>PCT 全局规划</th><th>SCAN 局部规划</th><th>Nav2 跟踪与调度</th></tr></thead><tbody>
<tr><td>要回答的问题</td><td><strong>通过哪些楼层与通路到终点？</strong>固定分层地图上的长距离参考路径。</td><td><strong>下一段身体运动怎样可行？</strong>实时占据、支撑与动力学约束下的短曲线。</td><td><strong>何时继续、何时等待、何时判失败？</strong>任务 action、路线刷新、速度输出与恢复。</td></tr>
<tr><td>主要输入</td><td>tomogram + coverage 修正；当前位置、目标与高度。</td><td>PCT Path；局部 3D 快照；身体位姿/速度；地面与支撑。</td><td>任务目标、Path、B-spline、实际位姿/速度。</td></tr>
<tr><td>主要运算</td><td>跨层索引 → 原生 A* → GPMP / 配置选定的优化器。<small>此处描述本地包装层的调用，不宣称完整上游算法审计。</small></td><td>参考前沿 → 局部目标 → 热启动或图搜索 → 样条优化 → 完整可行性检查。</td><td>行为树刷新；前馈与位置/航向反馈；机体系变换；停止/进展判断。</td></tr>
<tr><td>输出与消费者</td><td><code>nav_msgs/Path</code> → FollowPath / setPlan。</td><td><code>Bspline</code> → SCAN 跟踪插件；紧急时带 stop 标记。</td><td><code>Twist(vx,vy,wz)</code> → TCP 桥 → V12。</td></tr>
<tr><td>调度与实测</td><td>行为树配置 1 Hz；v196 本轮记录 102 次路线发布。<small>发布次数不等于所有规划调用次数。</small></td><td>目标 30 Hz；本轮成功规划 <strong>24.63 Hz</strong>。错过节拍会跳过，不追赶补发。</td><td>控制配置 30 Hz；本轮输出 <strong>29.94 Hz</strong>。不能替代局部求解频率。</td></tr>
<tr><td>失败出口</td><td>首次路线失败拒绝；同任务特定刷新失败可用缓存。无效/非有限输出不属于缓存回退。</td><td>换种子、局部恢复、EMERGENCY_STOP；安全回调检查剩余曲线。</td><td>无曲线置零，等候超时/无进展导致 FollowPath 失败；Wait 后重试。</td></tr>
<tr><td>直接来源</td><td data-refs="pct_plugin,pct_core,cache"></td><td data-refs="optimizer,restart,safety,schedule"></td><td data-refs="bt,control,tracking,report"></td></tr>
</tbody></table></div>
<div class="split"><article class="panel"><div class="subtle-title">GLOBAL → LOCAL</div><h3>一条路线如何变成可执行的局部曲线</h3><ol class="flow-list"><li data-n="01"><strong>PCT 返回含高度的 world Path</strong><span>首次规划固定 canonical goal；后续刷新不得偷偷改变终点。</span></li><li data-n="02"><strong>Controller 判断目标与几何是否变化</strong><span>同几何且当前有曲线时只更新参考；需要时发布 /pct_path。</span></li><li data-n="03"><strong>SCAN 建立内部参考曲线与局部前沿</strong><span>这里的 global_data 是参考轨迹表示；局部窗口只有有限规划范围。</span></li><li data-n="04"><strong>局部候选经搜索、优化和几何检查</strong><span>已有曲线可作为热启动；过期、缺失或多次失败改用实测里程计起点。</span></li><li data-n="05"><strong>发布含时间原点的三次样条</strong><span>控制器按轨迹相位采样，再转换为机体系速度；原地转向可冻结执行相位。</span></li></ol><div data-refs="cache,setplan,restart,tracking"></div></article>
<article class="panel"><div class="subtle-title">MAP CONTRACTS</div><h3>不能笼统叫作“地图”的四种东西</h3><ol class="flow-list"><li data-n="A"><strong>PCT 全局分层代价</strong><span>长距离可达性；固定 map.pickle，包含支撑覆盖修正。</span></li><li data-n="B"><strong>静态地面与物理表面</strong><span>区分地面高度、真实表面存在和可通行性；保留不同来源身份。</span></li><li data-n="C"><strong>SCAN 实时 3D 局部地图</strong><span>点云、位姿与静态支撑融合；0.05 m 栅格，异步不可变快照。</span></li><li data-n="D"><strong>Nav2 身体高度的二维切片</strong><span>由 C 导出，接 TerrainLayer / InflationLayer；不回写 A 的 PCT 全局地图。</span></li></ol><div class="note">一个层面的“可行”只是该层合同成立，不能自动推出下一层也可行。</div><div data-refs="global_map,launch,scan_config,terrain,pct_plugin"></div></article></div>
</section>
<section id="state" role="tabpanel" aria-labelledby="tab-state" hidden>
<div class="lead"><div><h2>状态分布在多个拥有者中</h2><p>修改前先确定状态由谁维护、谁能失效它、谁来恢复。下面的场景是基于代码的事件示意，不是运行日志回放。</p></div></div>
<div class="scenario-bar" id="scenario-controls" aria-label="选择事件场景"></div><p class="muted" id="scenario-description" aria-live="polite"></p><div class="steps" id="scenario-steps"></div>
<div class="split"><article class="panel"><h3>四层状态，各自负责自己的终态</h3><div class="state-box"><strong>任务身份 / MissionBridge + Nav2</strong><p>request_id、goal_id、current_owner、canonical_goal_pose、action 状态；负责是否还是同一个任务。</p></div><div class="state-box"><strong>局部可行性 / SCAN FSM</strong><p>INIT → WAIT_TARGET → GEN_NEW_TRAJ ↔ EXEC_TRAJ ↔ REPLAN_TRAJ；另有 EMERGENCY_STOP 与 fail_safe 恢复。</p></div><div class="state-box"><strong>轨迹执行 / Controller + Tracker</strong><p>当前样条、exec_time、waiting_for_spline、goal_braking、execution_frozen；负责眼前是否有可执行命令。</p></div><div class="state-box"><strong>身体与关节 / V12 + stance</strong><p>RL、STAND_SETTLING、STAND_TRANSITION、FIXED_STAND、REJOIN；最终 PD hold 由实验 driver 另行验证。</p></div><div data-refs="mission,recovery,control,tracking,stance,driver"></div></article>
<article class="panel"><h3>三类时间，不能互相替代</h3><div class="state-box"><strong>ROS / 原生物理仿真时间</strong><p>位姿、点云、样条 start_time、几何新鲜度与最终站立持续时间。导航节点使用 use_sim_time；通信桥的发送与超时另用 monotonic。</p></div><div class="state-box"><strong>Mac 与 Linux monotonic 时间</strong><p>局部求解节拍、指令源时间、通信超时、实际耗时。跨主机要估计偏移与不确定度，失同步会置零。</p></div><div class="state-box"><strong>局部轨迹执行相位</strong><p>接收时对齐样条时间原点，后续增量推进；转向或终点对齐会冻结相位，并把 freeze 反馈给 SCAN。</p></div><div class="note">navigation_contract.json 保留了历史 version=v59。频率字段是配置意图；实际调度与时钟语义以当前代码、生成参数和运行记录为准。</div><div data-refs="contract,schedule,clock,tracking,profile"></div></article></div>
<article class="panel" style="margin-top:26px"><h3>实际运行边界：模块不等于进程</h3><div class="table-scroll"><table><thead><tr><th>位置 / 进程</th><th>共同运行的内容</th><th>隔离与耦合</th></tr></thead><tbody><tr><td>Mac 主机 · Newton worker</td><td>CPU 物理、V12 ONNX、RL/PD 切换、几何 LiDAR；传感扫描与写盘有各自线程。</td><td>物理状态由这一侧维护，通过 TCP 回传 ROS；applied-state 与终局请求使用共享目录。</td></tr><tr><td>ARM64 Linux 容器 · MissionBridge</td><td>HTTP 任务入口、ROS action client、PlanRoute 服务与原生 PCT 包装层。</td><td>HTTP 线程与三线程 ROS executor 分开；PCT 调用有独立锁，不应当成独立外部 PCT daemon。</td></tr><tr><td>ARM64 Linux 容器 · controller_server</td><td>SCAN Controller / GoalChecker 插件、Tracker，以及嵌入式 NativeWorker。</td><td>NativeWorker 独立 executor；本轮 LiDAR + sim-time 条件下用两线程，其中原生规划/数据回调串行，/clock 可单独推进。</td></tr><tr><td>controller_server 内 · 异步 mapper</td><td>后台写地图，发布不可变 snapshot；前台规划查询已完成的 revision。</td><td>减少写图与求解直接互锁，但两者仍共享同一进程资源、时间门槛和快照发布协议。</td></tr><tr><td>容器内其他节点</td><td>planner_server、bt_navigator、recoveries_server、ROS 仿真桥、地面发布、TF 与观察器。</td><td>由 native_graph 启动；planner_server 的 PCT 插件通过服务调用 MissionBridge；当前 recovery 仅 Wait。</td></tr></tbody></table></div><div data-refs="launch,run,mission,worker,mapper,physics"></div></article>
<div class="table-scroll" style="margin-top:26px"><table><thead><tr><th>门槛 / 调度</th><th>当前值</th><th>作用对象</th><th>归属与证据</th></tr></thead><tbody>
<tr><td>局部地图点云年龄</td><td>≤ 0.35 s</td><td>SCAN 观察证据</td><td data-refs="scan_config"></td></tr><tr><td>Nav2 地形切片年龄</td><td>≤ 0.25 s</td><td>TerrainLayer current / 栅格更新</td><td data-refs="terrain"></td></tr><tr><td>源速度命令超时</td><td>0.25 s</td><td>ROS bridge 发往仿真的速度</td><td data-refs="bridge_config,bridge"></td></tr><tr><td>无样条等待</td><td>5 s</td><td>Controller 的等待状态</td><td data-refs="control,controller_config"></td></tr><tr><td>任务进展检查</td><td>0.5 m / 10 s</td><td>Nav2 SimpleProgressChecker</td><td data-refs="controller_config"></td></tr><tr><td>局部窗口 / 任务终点</td><td>2 cm / XY 25 cm</td><td>不同层的不同完成条件</td><td data-refs="profile,controller_config"></td></tr><tr><td>Nav2 实际停止速度</td><td>线速度范数 ≤ 0.03 m/s；角速度范数 ≤ 0.05 rad/s</td><td>GoalChecker；不等于旧 P2B 停车门槛</td><td data-refs="stop_speed,goalcheck"></td></tr><tr><td>最终物理站立</td><td>FIXED_STAND 连续 ≥ 2 s</td><td>driver 附加验证，另检查实际停稳与距离</td><td data-refs="driver"></td></tr></tbody></table></div>
</section>
<section id="risk" role="tabpanel" aria-labelledby="tab-risk" hidden><div class="lead"><div><h2>为什么局部补丁会牵动别的模块</h2><p>以下列出已确认的耦合和应验证的传播路径。它们是架构审查入口，不把每一种可能性都当作已经定位的 bug。</p></div></div><div class="risk-layout"><nav class="risk-menu" id="risk-controls" aria-label="选择耦合问题"></nav><article class="risk-detail" id="risk-detail" aria-live="polite"></article></div><div class="rules"><h3>后续修复的最小审查单位：一条跨层合同</h3><ol><li>先选定一个原始失败事件：保留输入、状态、版本、时钟、地图 revision 和加载库。</li><li>说明改动所属模块，以及它会让哪些下游状态失效；一次只改变一个可解释的行为。</li><li>回放既有成功案例、失败案例和负例；局部通过后再做完整路线重复，并保留原二进制对照。</li><li>分别报告组件通过、单次到达、重复可靠性、实际停车和性能；不把它们压成一个 PASS。</li></ol><p class="tiny muted">这是本次梳理提出的后续工作建议；本页面没有实施导航修改或发起新运行。</p></div></section>
<section id="evidence" role="tabpanel" aria-labelledby="tab-evidence" hidden><div class="lead"><div><h2>哪些有证据，哪些还不能推出</h2><p>最新证据绑定 v196_mac_full_attempt01。代码关系来自本地冻结快照，实测来自已归档结果；本次没有重跑物理或重新探测服务器。</p></div></div><div class="evidence-grid"><div class="metric"><div class="label">原始路线连续距离</div><div class="value">77.92 <small>m</small></div></div><div class="metric"><div class="label">导航实际耗时</div><div class="value">118.35 <small>s</small></div></div><div class="metric"><div class="label">成功局部规划</div><div class="value">24.63 <small>Hz</small></div></div><div class="metric"><div class="label">控制输出</div><div class="value">29.94 <small>Hz</small></div></div></div>
<div class="table-scroll"><table><thead><tr><th>结论层级</th><th>当前证据</th><th>边界</th></tr></thead><tbody><tr><td><span class="status">单次路线通过</span></td><td>原起点至原终点、无摔倒、最终 PD hold 与 held XYZ/yaw 检查通过。</td><td>只对应一个新执行的 v196 Mac trial。</td></tr><tr><td><span class="status pending">整体仍待验证</span></td><td>重复可靠性、持续 30 Hz、其他起点/地图、动态障碍、真机运动。</td><td>不能从视频或组件测试推出。</td></tr><tr><td>定位 / 感知</td><td>仿真身体真值 + 几何 LiDAR；本轮 Building 无活动人模型。</td><td>不是 SLAM、视觉定位或行人跟踪验收。</td></tr><tr><td>视觉语言层</td><td>项目有独立模型与 receive-only 历史实验。</td><td>不在此条 PCT→SCAN→V12 完整路线的运行链中。</td></tr><tr><td>v197 视频</td><td>保存状态的重放显示；不新增物理步。</td><td>不增加新的路线成功样本。</td></tr></tbody></table></div><div data-refs="result,report,physics,display" style="margin-top:12px"></div>
<div class="scope-list"><div><h3>本图覆盖</h3><p>v196 当前启动链、PCT/SCAN 接口、映射、跟踪、通信、状态、恢复与验收。</p></div><div><h3>未混入主链</h3><p>旧 P2B gateway、已搁置 MPPI、未启动的 moving-cluster tracker、未来 VLA 与 SLAM。</p></div><div><h3>待深入核验</h3><p>所有碰撞/支撑分支、完整原生 PCT 数值实现、跨平台性能与每次失败的首因。</p></div><div><h3>快照身份</h3><p>当前工作区含未提交 v196/v197。页内来源保存读取时 SHA-256；Git HEAD 不能单独代表这些源文件。</p></div></div>
<h3 style="margin-top:24px">原始来源索引 <span class="muted tiny" id="source-count"></span></h3><label class="tiny muted" for="source-search">按模块、文件名或关键词查找</label><br><input class="search" id="source-search" type="search" placeholder="例如：mission、clock、terrain、RESULTS"><div class="source-list" id="source-list"></div>
<div class="provenance" id="provenance"></div></section>
</main></div><dialog id="source-dialog" aria-labelledby="source-title"><div class="dialog-head"><div><h3 id="source-title"></h3><div class="path" id="source-path"></div></div><button class="quiet" id="close-source" aria-label="关闭源码片段">关闭 ×</button></div><div class="dialog-body"><div class="tiny muted" id="source-hash"></div><p class="tiny muted">以下为构建页面时从本地文件读取的原文片段，行号与整文件哈希一并保存。完整来源路径列于上方。</p><pre id="source-code"></pre></div></dialog>
<script type="application/json" id="report-data">__DATA__</script>
<script>
'use strict';
const D=JSON.parse(document.getElementById('report-data').textContent);
const $=id=>document.getElementById(id);
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const refs=keys=>keys.map(k=>{if(!D.sources[k])throw Error('Unknown source '+k);return `<button class="source-chip" data-source="${k}">${esc(D.sources[k].title)}</button>`;}).join('');
function openTab(id){document.querySelectorAll('[role=tab]').forEach(t=>t.setAttribute('aria-selected',String(t.getAttribute('aria-controls')===id)));document.querySelectorAll('[role=tabpanel]').forEach(p=>p.hidden=p.id!==id);if(id==='overview')requestAnimationFrame(drawEdges);location.hash=id;}
document.querySelectorAll('[role=tab]').forEach(t=>t.addEventListener('click',()=>openTab(t.getAttribute('aria-controls'))));
document.querySelectorAll('[data-open-tab]').forEach(t=>t.addEventListener('click',()=>openTab(t.dataset.openTab)));
document.querySelectorAll('[data-refs]').forEach(el=>el.innerHTML=refs(el.dataset.refs.split(',')));
const graph=$('graph');
graph.insertAdjacentHTML('beforeend','<div class="band-label" style="top:3%">任务与全局路线</div><div class="band-label" style="top:35%">局部感知、规划与控制</div><div class="band-label" style="top:67%">物理闭环与适配</div>');
D.nodes.forEach(n=>{let b=document.createElement('button');b.className='node';b.dataset.id=n.id;b.id='node-'+n.id;b.style.left=(1+n.pos[0]*25.2)+'%';b.style.top=(9+n.pos[1]*32)+'%';b.setAttribute('aria-label',n.name+'：'+n.subtitle);b.innerHTML=`<span class="node-name">${esc(n.name)}</span><span class="node-sub">${esc(n.subtitle)}</span><span class="node-tag">${esc(n.tag)}</span>`;b.addEventListener('click',()=>selectNode(n.id));graph.append(b);});
function selectNode(id){let n=D.nodes.find(n=>n.id===id);document.querySelectorAll('.node').forEach(b=>{b.classList.toggle('selected',b.dataset.id===id);b.setAttribute('aria-pressed',String(b.dataset.id===id));});$('inspector').innerHTML=`<div class="tag">${esc(n.tag)} · ${esc(n.id.toUpperCase())}</div><h2>${esc(n.name)}</h2><p>${esc(n.role)}</p><h4>输入</h4><ul>${n.inputs.map(v=>`<li>${esc(v)}</li>`).join('')}</ul><h4>输出</h4><ul>${n.outputs.map(v=>`<li>${esc(v)}</li>`).join('')}</ul><h4>状态由谁维护</h4><p>${esc(n.state)}</p><div class="note">${esc(n.caveat)}</div><h4>原始来源</h4>${refs(n.refs)}`;}
function drawEdges(){if($('overview').hidden)return;const r=graph.getBoundingClientRect(),w=r.width,h=r.height;const svg=$('edges');svg.setAttribute('viewBox',`0 0 ${w} ${h}`);let out='<defs>'+['command','data','feedback'].map((k,i)=>`<marker id="arrow-${k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="${['#235bd1','#087e82','#a45e12'][i]}"/></marker>`).join('')+'</defs>';
function pt(id,side){let b=$('node-'+id).getBoundingClientRect(),x=b.left-r.left,y=b.top-r.top;return side==='right'?[x+b.width,y+b.height/2]:side==='left'?[x,y+b.height/2]:side==='top'?[x+b.width/2,y]:[x+b.width/2,y+b.height];}
D.edges.forEach(([a,b,label,kind,from,to,offset])=>{let [x1,y1]=pt(a,from),[x2,y2]=pt(b,to),path,lx=(x1+x2)/2,ly=(y1+y2)/2-8;if(a==='static'&&b==='map'){let y=y1+offset;path=`M${x1},${y1} V${y} H${x2} V${y2}`;ly=y-7;}else if(from==='bottom'&&to==='top'&&Math.abs(x1-x2)>20){let y=(y1+y2)/2;path=`M${x1},${y1} V${y} H${x2} V${y2}`;ly=y-8;}else if(offset){let y=Math.min(y1,y2)+offset;if(offset>0)y=Math.max(y1,y2)+offset;path=`M${x1},${y1} C${x1},${y} ${x2},${y} ${x2},${y2}`;ly=y+ (offset>0?7:-5);}else if(from==='bottom'&&to==='left'){path=`M${x1},${y1} V${y2} H${x2}`;lx=x1+35;ly=(y1+y2)/2;}else{path=`M${x1},${y1} L${x2},${y2}`;if(Math.abs(x1-x2)<20){lx=x1+10;ly=(y1+y2)/2;}}
const dim=$('edge-filter').value!=='all'&&$('edge-filter').value!==kind;out+=`<path class="edge ${kind}${dim?' dim':''}" d="${path}" marker-end="url(#arrow-${kind})"/><text class="edge-label${dim?' dim':''}" x="${lx}" y="${ly}" text-anchor="${Math.abs(x1-x2)<20?'start':'middle'}">${esc(label)}</text>`;});svg.innerHTML=out;}
$('edge-filter').addEventListener('change',drawEdges);new ResizeObserver(drawEdges).observe(graph);
function showScenario(i){const s=D.scenarios[i];document.querySelectorAll('[data-scenario]').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.scenario)===i)));$('scenario-description').textContent=s.desc;$('scenario-steps').innerHTML=s.steps.map(([owner,text,n])=>`<div class="step"><strong>${esc(owner)}</strong><p>${esc(text)}</p><button class="source-chip" data-jump-node="${n}">在总览中定位 ↗</button></div>`).join('');}
$('scenario-controls').innerHTML=D.scenarios.map((s,i)=>`<button data-scenario="${i}" aria-pressed="false">${esc(s.name)}</button>`).join('');
function showRisk(i){const r=D.risks[i];document.querySelectorAll('[data-risk]').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.risk)===i)));$('risk-detail').innerHTML=`<div class="subtle-title">${esc(r.type)}</div><h2>${esc(r.title)}</h2><div class="chain">${r.chain.map(s=>`<span>${esc(s)}</span>`).join('<b>→</b>')}</div><dl><dt>当前事实</dt><dd>${esc(r.fact)}</dd><dt>传播风险<br>（需验证）</dt><dd>${esc(r.risk)}</dd><dt>怎样验证</dt><dd>${esc(r.proof)}</dd></dl><h4>对应源文件</h4>${refs(r.refs)}`;}
$('risk-controls').innerHTML=D.risks.map((r,i)=>`<button data-risk="${i}" aria-pressed="false"><span>耦合 ${String(i+1).padStart(2,'0')}</span>${esc(r.title)}</button>`).join('');
function sourceList(q=''){q=q.toLowerCase();const rows=Object.entries(D.sources).filter(([k,s])=>(k+' '+s.title+' '+s.path).toLowerCase().includes(q));$('source-count').textContent=`${rows.length} / ${Object.keys(D.sources).length} 个来源片段`;$('source-list').innerHTML=rows.length?rows.map(([k,s])=>`<div class="source-row"><button data-source="${k}">${esc(s.title)} ↗</button><code>${esc(s.path)}:${s.start}–${s.end}</code><span class="tiny muted">SHA-256 ${s.sha256.slice(0,16)}…</span></div>`).join(''):'<p class="muted">没有匹配的来源。</p>';}
$('source-search').addEventListener('input',e=>sourceList(e.target.value));
function openSource(k){const s=D.sources[k];$('source-title').textContent=s.title;$('source-path').textContent=D.root+'/'+s.path+':'+s.start+'–'+s.end;$('source-hash').textContent='SHA-256 '+s.sha256;$('source-code').textContent=s.excerpt;$('source-dialog').showModal();}
$('close-source').addEventListener('click',()=>$('source-dialog').close());$('source-dialog').addEventListener('click',e=>{if(e.target===$('source-dialog')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});
document.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;if(b.dataset.source)openSource(b.dataset.source);if(b.dataset.scenario!==undefined)showScenario(Number(b.dataset.scenario));if(b.dataset.risk!==undefined)showRisk(Number(b.dataset.risk));if(b.dataset.jumpNode){openTab('overview');selectNode(b.dataset.jumpNode);}});
document.querySelector('[role=tablist]').addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;const all=[...document.querySelectorAll('[role=tab]')];let i=all.indexOf(document.activeElement);if(i<0)return;e.preventDefault();i=e.key==='Home'?0:e.key==='End'?all.length-1:(i+(e.key==='ArrowRight'?1:-1)+all.length)%all.length;all[i].focus();all[i].click();});
$('provenance').textContent=`本地来源：${D.root} · 构建日期：${D.date} America/Los_Angeles · 读取时 Git HEAD：${D.git_head.slice(0,12)}（工作区非干净提交） · 页面可离线打开，无远端依赖。附带 source-manifest.json 记录所有引用的整文件哈希。`;
selectNode('scan');showScenario(0);showRisk(0);sourceList();const target=location.hash.slice(1);if(['overview','planning','state','risk','evidence','target'].includes(target))openTab(target);requestAnimationFrame(drawEdges);
</script></body></html>'''

target_fragment = (OUT/'refactor-target.fragment.html').read_text(encoding='utf-8')
target_css = (OUT/'refactor-target.css').read_text(encoding='utf-8')
html = html.replace('</main>', target_fragment + '\n</main>', 1).replace('</style>', target_css + '\n</style>', 1)

data = dict(date='2026-10-15', root=str(ROOT), implementation='v196', display='v197',
            git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            sources=SOURCES, nodes=NODES, edges=EDGES, risks=RISKS, scenarios=SCENARIOS)
payload = json.dumps(data,ensure_ascii=False,separators=(',', ':')).replace('</',r'<\/')
(OUT/'index.html').write_text(html.replace('__DATA__',payload),encoding='utf-8')
manifest = {k:v for k,v in data.items() if k not in ('nodes','edges','risks','scenarios')}
manifest['sources'] = {k:{a:b for a,b in v.items() if a!='excerpt'} for k,v in SOURCES.items()}
manifest['target_design'] = {'stage': 'implementation', 'implemented_steps': [1,2,3,4], 'pending_steps': [], 'deferred_steps': [5], 'global_replan_hz': 1.0, 'component_version': 'v204', 'full_route_experiments': 1, 'physical_trial': 'v204_mac_full_attempt01', 'physical_route_passed': True, 'fragment_sha256': hashlib.sha256(target_fragment.encode()).hexdigest(), 'css_sha256': hashlib.sha256(target_css.encode()).hexdigest()}
manifest['target_design'].update(latest_locomotion_candidate='v208', candidate_short_physics_passed=2,
                                 candidate_full_route_validated=False, navigation_source='v206',
                                 latest_full_route_trial='v206_linux_full_attempt02', latest_full_route_passed=False)
manifest['html_sha256'] = hashlib.sha256((OUT/'index.html').read_bytes()).hexdigest()
(OUT/'source-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'html':str(OUT/'index.html'),'bytes':(OUT/'index.html').stat().st_size,'sources':len(SOURCES)},ensure_ascii=False))

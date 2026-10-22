# v289 完整验证报告

离线门禁通过：合法 **49/50**，非法 **3/3** 拒绝，全局中位耗时 **1.430742 s**。
十条各跑一次：**6/10 到达并完成 PD 站立**，其中 **5/10 同时通过工厂起立与后续全记录的采样几何检查**。原生信号崩溃 0，节点无响应路线 0，扫描 deadline_miss 0，躯干时间戳回退错误 0。**完整验收未通过**。

## 实现范围与不变量

本地主仓在冻结 v288 上切出 v289；远端只在 `/home/ubuntu/sun/vla_v289_20261020` 构建执行。源码与执行输入在十条实跑前冻结，未修改 v288，未重跑任何正物理步数的尝试。0.35 m 双圆柱硬半径、0.18 m 偏移、0.1 s 扫描周期和 deadline、0.35 s 点云新鲜度、工厂起立及 v216 策略不变。没有路线、坐标或场景特判。

1. 保留共享递归工作锁，手动传感器刷新使用同一锁。迟到旧躯干样本在单调缓冲区内计数丢弃，保留更新状态；真正非法输入、队列溢出和新鲜度拒绝保留。锁不能阻止 Executor 在等待锁前已取出消息，因此幂等合并仍是必要机制。
2. 外层恢复原有 0.25 m XY 容差。内层只在朝向尚未对齐时，于 5 cm 步态死区外叠加不超过 0.15 m/s 的平滑向心速度，经原机体系变换和 slew 限幅；朝向达标后按原捕获条件停止切 PD。
3. 恢复原 measured-trunk 钩子，但它仅处理未膨胀 Unknown；v288 已将此空气归为 Free，因此恢复本身不增加放行效果。不能将父版全部 inside-obstacle 都归因于该钩子，更未扩大 Occupied 或支撑豁免。父版原始上下文见 [源码审查](SOURCE_REVIEW_zh.md) 和 evidence/parent_witnesses01.json。
4. 复用现有优化缓存记录初始代价、有限梯度下的最优候选与代价。负返回先恢复 best_q；只有 best_cost < initial_cost 才进入原有完整曲线碰撞及后续动力学门禁。函数评估次数不再代表下降。best_q 可能是尚未通过 Wolfe 的试探点，不能称为求解器接纳步。
5. 生命周期探针独立回调组，实际每节点请求 5 Hz，原 50 Hz 检查和 1 s 无响应门槛不变。运行链只加载一个已测试的主桥，将原物理覆盖桥已有的 ACTIVE 准入逻辑显式并回主桥，删除重复覆盖。

父版 A*、递归串行保护、常数每 span 3 点积分、ENV 边缘梯度与全局规划主体保留。新增修复与测试的确切差异见版本目录 changes.patch；本次不是替换规划框架。

源码清单 SHA-256：`5406c3d4930c29d4bb4a456c43874963c236ab9de2ef7fc9ae2c27a60b5f1d06`；物理输入清单：`87b1dc3baedb4f90664e1b24c0873b3fcec51f441af0070ea7bbba0a0e3c350e`。332 份原生源码与共 378 项声明源/辅助文件均核验，远端清单另绑定安装产物与测试输入。父版源码清单仍为 `e8935ba2b1d1ba3d8931641afda7eec0e951ef66805e49a7f6be7ab8233010af`。

## 构建、单测与输入核验

14 包完整清洁构建和最终增量构建均通过。49 份返回 XML 覆盖 364 次功能测试执行（含重复回归），另有 14 份通过的静态检查记录；相关包功能测试、环境场/工作互斥/修复/地形/连续性探针均通过。**另有 3 项继承的 Nav2 格式/XML lint 失败，原记录保留，未伪称全部静态检查通过。**
真实 BodyTimeBuffer 父版对照无法从迟到样本恢复，候选 4/4 通过；真实 ROS 生命周期服务对照覆盖默认组忙碌与真实失联。父版健康服务对照第二次缺 underlay 是装配错误，保留但不计作行为红灯；第三次才是实际物理桥的有效对照。
原始 cohort/字段字节复用，不重新抽样。50 个合法起点均通过统一静态额外安全余量检查，最小额外支撑约 0.1500 m、固体约 0.1442 m。1560 项原执行输入、实际桥模块与全部冻结清单在实跑前核验。

## 50+3 离线门禁

| 项目 | 实测 | 判定 |
|---|---:|---|
| 合法 | 49/50 | 通过 |
| 非法拒绝 | 3/3 | 通过 |
| 准入全局中位数 | 1.430742 s | 通过 |
| p95 / 最大值 | 2.023966 / 2.116776 s | 尾延迟保留 |
| 准入全局 / 已发局部几何 | 通过 / 通过 | 半径 0.35 m |
| 首次 GPMP | 47/49 | 准入分母 |

53 次原生计时全部完成后再做独立几何审计，53 条审计均正常结束，十条选定物理路线离线均通过。唯一合法未过例为 CS01。初始化单列，不计入全局调用耗时。
用户确认没有空闲窗口后，本次在现有 CARLA/ROS 后台负载下完成；保留原 2 CPU quota 和每 5 s 资源记录，不停其他任务。**没有空闲机器计时声明，也没有耗时门槛例外。**资源记录见 evidence/offline_host_load01.jsonl。

## 十条物理结果

| 路线 | 到达+PD | 后续记录几何 | 起立几何 | 仿真时长 s | 实走 m | 支撑/源固体/原始点额外 cm | 最长停顿 s |
|---|---|---|---|---:|---:|---:|---:|
| A04 | 未通过 | 通过 | 通过 | 86.80 | 28.79 | 15.00/15.00/15.00 | 36.92 |
| G05 | 未通过 | 通过 | 通过 | 89.32 | 28.36 | 7.29/15.00/15.00 | 35.82 |
| CU06 | 未通过 | 通过 | 通过 | 85.12 | 31.80 | 15.00/15.00/15.00 | 30.66 |
| D07 | 通过 | 通过 | 通过 | 118.47 | 83.30 | 15.00/0.91/1.27 | 6.06 |
| S04 | 通过 | 通过 | 通过 | 30.89 | 4.72 | 15.00/12.64/12.72 | 5.18 |
| CD12 | 通过 | 未通过 | 通过 | 123.10 | 89.83 | 2.93/-4.62/-4.42 | 6.02 |
| CM02 | 未通过 | 通过 | 通过 | 72.83 | 20.98 | 9.87/15.00/15.00 | 30.32 |
| CM07 | 通过 | 通过 | 通过 | 54.00 | 24.55 | 12.38/15.00/15.00 | 5.50 |
| CS03 | 通过 | 通过 | 通过 | 29.88 | 4.84 | 15.00/7.09/7.13 | 5.56 |
| CE03 | 通过 | 通过 | 通过 | 32.89 | 2.31 | 15.00/5.11/5.11 | 10.13 |

“后续记录几何”涵盖传感器开始后的全部样本，包括失败前缀与终端 PD；起立另审原 factory_video_states，包含零时刻趴姿。支撑间隙、源固体、原始点三者分列；ENV 软代价、WrongHeight 计数另保留，不拿 Free-only 统计掩盖拒绝样本。正余量在 +0.15 m 报告上限饱和。传感器约 10 Hz 离散采样，不等于连续时间、腿部接触或真机认证。失败前缀几何通过不算全路线安全到达。

扫描 6130 次，deadline_miss 0。保留原全局几何 10/10；每条 epoch 数见 physical_summary.json，重发同一参考与裁剪前缀不等于重新生成全局路线。

冻结 v288 的对应单次记录为 1/10 到达+PD、1/10 后续全记录几何与到达双过。本轮为 6/10、5/10。负载、实际暴露长度和执行结果均不同，这一对照是描述性结果，不是独立重复可靠性或因果性能证明。

启动包装器退出码与导航结果分开：旧保留脚本因 lsof 对其他容器挂载点发出警告而返回归档失败时，原文件仍保留。最终另做非删除 snapshot，并核验全部成员 SHA。因此不把这种退出码 2 自动计为导航失败，也不掩盖实际 FAILED 终态。

## 错误计数、输入顺序与优化耗时

暴露量：v288 总仿真记录 572.362 s、完成局部轮次 3168；v289 为 723.319 s、14999 轮。以下为包括重试的日志记录，不是独立失败概率。两个版本均从原日志按 SHA 核验后使用相同解析器重算，未改写父版证据。

| 日志项 | v288 同口径重算 | v289 |
|---|---:|---:|
| pool_exhaustion | 0 | 0 |
| endpoint_adjustment_failed | 0 | 26 |
| astar_optimization_failed | 0 | 58 |
| inside_obstacle | 13 | 48 |
| lbfgs_minus1008 | 371 | 410 |
| minus1008_raw_substring_mentions | 371 | 416 |
| no_executable_trajectory | 38 | 26 |
| regressed_body_source_stamp | 见父版原报告 | 0 |
| -1008 / 100 完成局部轮 | 11.711 | 2.734 |

真实 -1008 计数排除 `---1008` 重规划编号；raw_substring_mentions 单列保留旧式字面搜索结果。返回码恢复日志仍计数，没有将复用下降候选伪装成无求解错误。每轮可含多次优化，也包含失败后的等待轮，按规划轮归一化不等于独立求解失败率。是否真正改善必须结合暴露量与同口径父版比较，不能仅凭函数评估次数或到达率判断。

| 路线 | 忽略旧躯干计数最大值 | 负返回恢复记录 | 回退错误 | 无响应日志 | 整轮 median/p95/max ms |
|---|---:|---:|---:|---:|---:|
| A04 | 0 | 9 | 0 | 0 | 9.604/25.762/252.013 |
| G05 | 2 | 0 | 0 | 0 | 12.265/35.905/347.405 |
| CU06 | 1 | 0 | 0 | 0 | 16.113/64.358/215.380 |
| D07 | 0 | 31 | 0 | 0 | 14.054/28.702/203.713 |
| S04 | 0 | 69 | 0 | 0 | 14.166/22.998/36.005 |
| CD12 | 0 | 76 | 0 | 0 | 14.439/32.650/326.540 |
| CM02 | 0 | 16 | 0 | 0 | 2.228/21.074/324.756 |
| CM07 | 0 | 4 | 0 | 0 | 16.431/30.188/260.355 |
| CS03 | 0 | 133 | 0 | 0 | 13.246/29.511/48.246 |
| CE03 | 0 | 72 | 0 | 0 | 12.052/20.469/26.661 |

旧样本计数是记录到的 GridMap 最大值，不是 GridMap+FSM 丢弃数之和。单调 sensor.jsonl 也不能证明未记录的 DDS take/锁等待顺序。恢复代价以双精度源码比较为准；日志只打印 12 位有效数字，微小真实下降可能显示相等。完整曲线碰撞及动力学验证仍单独执行。

| 路线 | 最小 XY cm | 最终 XY cm | <=25cm 样本 | 进度超时日志 |
|---|---:|---:|---:|---:|
| A04 | 513.526 | 513.982 | 0 | 0 |
| G05 | 441.724 | 1024.986 | 0 | 0 |
| CU06 | 582.081 | 708.387 | 0 | 0 |
| D07 | 5.409 | 5.662 | 111 | 0 |
| S04 | 6.132 | 6.219 | 79 | 0 |
| CD12 | 14.537 | 16.123 | 85 | 0 |
| CM02 | 776.701 | 1184.106 | 0 | 0 |
| CM07 | 7.474 | 8.547 | 92 | 0 |
| CS03 | 9.119 | 10.354 | 80 | 0 |
| CE03 | 4.785 | 5.099 | 133 | 0 |

## 仍未解决的问题

迟到位姿永久锁死及原生进程/心跳异常在这十次中均为零，S04/CS03 已顺利到达。A04/G05/CU06/CM02 仍因局部搜索/种子失败而耗尽可执行轨迹，未完成任务；并非 0.35 m 几何通过就能继续走。CM02 出现 26 次端点调整失败、36 次 A* 失败和全部 48 次 inside-obstacle。A* 源码虽未回退，父版“0 端点/搜索失败”的实测结果没有在本轮保持。

L-BFGS 仍有 410 次真实 -1008，高于父版 371；每 100 完成规划轮为 2.734 对 11.711。放行判据已修正且每次恢复仍受硬检验，但不能宣称舍入错误已消除或求解失败率已收敛。

CD12 仍有实际采样包络越界。首次负余量与最差值分别列出，避免将事后的零速站立误当成事件开始。

| 路线 | 事件 | 仿真 s | 源/点额外 cm | 距目标 cm | yaw 误差 rad | 实施 vx,vy,wz | 步态 |
|---|---|---:|---:|---:|---:|---|---|
| CD12 | 首次负值 | 114.769 | -0.936/-0.705 | 19.107 | -0.084 | [0.407,0.000,-0.325] | RL |
| CD12 | 最差值 | 117.567 | -4.622/-4.422 | 16.114 | -0.085 | [0.000,0.000,0.000] | STAND_TRANSITION |

CD12 首个负值处仍有前进与转向，并非零线速度纯旋转；最差值发生在零指令 STAND_TRANSITION。仅恢复原终点容差并在转头时归中，没有解决整个接近/切 PD 过渡的跟踪包络。上述是实际记录关联，不重建未记录的内部轨迹相位，也不把单次时序关联写成已证实的全部根因。见 physical_return/boundary_witnesses.json。

inside-obstacle 的源码位置为 bspline_optimizer.cpp 的回退控制点搜索：找不到之前的空闲控制点时输出该错误。它不直接证明当前实测机身碰撞。CM02 首次报错前已出现端点调整和 A* 失败，且点云年龄约 0.12 s；不能把全部问题归咎于后台负载或旧自轮廓钩子。

## 失败定位与原始日志行号

以下引用原 nav2.log 一基行号；日志 SHA 和远端保留位置见 failure_terminal_bill.json 的 sources。首末上下文保存在 mechanism_witnesses.json；不以候选查询的碰撞警告代替真机身几何越界证据。

### A04：FAILED，到达+PD 未通过

- `A-star failed`：3 次，首个原日志 L18497：`[controller_server-3] [ERROR] [1792563635.298309191] [bspline_opt]: A-star failed; aborting optimization`
- `reactive_stair_seed_search_failed`：2095 次，首个原日志 L34441：`[controller_server-3] [WARN] [1792563650.795706946] [quad_0.scan_planner_node]: reactive_stair_seed_search_failed status=2`
- `Native SCAN has no executable trajectory`：7 次，首个原日志 L39471：`[controller_server-3] [ERROR] [1792563655.582627909] [controller_server]: Native SCAN has no executable trajectory before timeout`

### G05：FAILED，到达+PD 未通过

- `reactive_stair_seed_search_failed`：2039 次，首个原日志 L37276：`[controller_server-3] [WARN] [1792563805.344171520] [quad_0.scan_planner_node]: reactive_stair_seed_search_failed status=2`
- `Native SCAN has no executable trajectory`：7 次，首个原日志 L44898：`[controller_server-3] [ERROR] [1792563814.556085973] [controller_server]: Native SCAN has no executable trajectory before timeout`

### CU06：FAILED，到达+PD 未通过

- `A-star failed`：1 次，首个原日志 L19499：`[controller_server-3] [ERROR] [1792563942.132267494] [bspline_opt]: A-star failed; aborting optimization`
- `reactive_stair_seed_search_failed`：971 次，首个原日志 L36858：`[controller_server-3] [WARN] [1792563959.120911095] [quad_0.scan_planner_node]: reactive_stair_seed_search_failed status=2`
- `Native SCAN has no executable trajectory`：6 次，首个原日志 L41267：`[controller_server-3] [ERROR] [1792563963.604758054] [controller_server]: Native SCAN has no executable trajectory before timeout`

### D07：FINISHED，到达+PD 通过

- `A-star failed`：2 次，首个原日志 L42569：`[controller_server-3] [ERROR] [1792564104.501824412] [bspline_opt]: A-star failed; aborting optimization`
- `reactive_stair_seed_search_failed`：3 次，首个原日志 L82248：`[controller_server-3] [WARN] [1792564142.508299966] [quad_0.scan_planner_node]: reactive_stair_seed_search_failed status=2`

### S04：FINISHED，到达+PD 通过

- `A-star failed`：1 次，首个原日志 L2272：`[controller_server-3] [ERROR] [1792564242.243986313] [bspline_opt]: A-star failed; aborting optimization`

### CD12：FINISHED，到达+PD 通过

- `A-star failed`：14 次，首个原日志 L19695：`[controller_server-3] [ERROR] [1792564344.601655751] [bspline_opt]: A-star failed; aborting optimization`

### CM02：FAILED，到达+PD 未通过

- `The robot is inside an obstacle`：48 次，首个原日志 L27786：`[controller_server-3] [ERROR] [1792564533.833794482] [bspline_opt]: The robot is inside an obstacle`
- `A-star failed`：36 次，首个原日志 L25096：`[controller_server-3] [ERROR] [1792564530.814444253] [bspline_opt]: A-star failed; aborting optimization`
- `Unable to handle the initial or end point`：26 次，首个原日志 L27692：`[controller_server-3] [ERROR] [1792564533.670143607] [path_searching]: Unable to handle the initial or end point, force return!`
- `reactive_stair_seed_search_failed`：2533 次，首个原日志 L26687：`[controller_server-3] [WARN] [1792564532.391339717] [quad_0.scan_planner_node]: reactive_stair_seed_search_failed status=2`
- `Native SCAN has no executable trajectory`：6 次，首个原日志 L29421：`[controller_server-3] [ERROR] [1792564534.357729959] [controller_server]: Native SCAN has no executable trajectory before timeout`

### CM07：FINISHED，到达+PD 通过

- `A-star failed`：1 次，首个原日志 L10670：`[controller_server-3] [ERROR] [1792564648.543598723] [bspline_opt]: A-star failed; aborting optimization`

### CS03：FINISHED，到达+PD 通过


### CE03：FINISHED，到达+PD 通过

- `reactive_stair_seed_search_failed`：1 次，首个原日志 L526：`[controller_server-3] [WARN] [1792564831.139714461] [quad_0.scan_planner_node]: reactive_stair_seed_search_failed status=2`

## 交付与可复核性

十条普通 MP4 全部已返回本地，共 76.6 MiB。逐文件 SHA-256 与远端清单相等，本地全片 ffmpeg 解码通过；20 个抽帧已目检。视频含完整原始起立、行进、停顿和终态，不补跑、不插值补成功。见 [完整视频索引](delivered/README.md)。

- `offline/`：53 次原生调用、独立几何与原门禁。
- `qualification_return01/`、`evidence/`：测试、构建、实际加载路径和执行前后身份。
- `physical_return/`：每条原始执行收据、数值审计、视频检查、失败账单与成员 SHA。
- `startup_return/`：零时刻开始的原工厂起立几何。
- `physical_summary.json`、`physical_table.csv`、`acceptance.json`：机器可读汇总和验收结论。
- 大型原始记录继续保留在 ultra9 原目录；return_inventory.json 记录位置、字节和 SHA，使用冻结脚本可仅重算分析/渲染，不得重跑物理。

后处理首次代价日志解析将末尾分号并入数值而失败；保留原脚本与 traceback，使用独立 summarize_mechanisms02.py 对同一记录重算成功。原 finalize_recordings01.json 与修复收据 finalize_recordings02.json 均返回本地；没有修改导航、重跑物理或覆盖失败证据。

本轮完成指定实现、测试、53 离线、十条单次执行与报告视频交付；验收是否达标以上述实际数据为准。未提升项目已选导航基线，也未声称单次路线结果代表统计可靠性。

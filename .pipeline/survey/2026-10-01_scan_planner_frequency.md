---
origin: ai+web
reviewed: false
date: 2026-10-01
status: surveyed
---


> ⚠ [未门控] Codex CLI 0.153.3 在当前沙箱初始化 app-server 时返回 Operation not permitted，未产生独立核查结论。主会话已核对摘要、实测字段、视频 SHA 和未实施方案边界；reviewed: false 保留。

# SCAN-Planner Paper And Source Frequency Check

Primary sources were inspected on 2026-09-30; this archive was written on
2026-10-01. Scope: Dr Sun asked for the original paper's local planning rate.
This is source inspection, not a new upstream reproduction or runtime
benchmark. The fixed local 30 Hz requirement was selected by Dr Sun for VLA.

## Paper Boundary

The inspected [SCAN-Planner paper v1](https://arxiv.org/html/2606.19555v1)
([PDF](https://arxiv.org/pdf/2606.19555), [arXiv record](https://arxiv.org/abs/2606.19555))
describes onboard real-time operation on Jetson Orin NX and uses an i9-14900K
for simulation. It does not report a fixed local trajectory replanning rate
or a measured 30 Hz trajectory update result. Hardware and the word
“real-time” are not substitute measurements of local solve frequency.

## Pinned Author Code

Repository: [wuyi2121/SCAN-Planner](https://github.com/wuyi2121/SCAN-Planner).
Inspected pin: `348e8a590a50a5a6bbab8d8c6dcfd171f009be26` (main snapshot),
root license Apache-2.0. This is a recorded pin, not a claim about current HEAD.

| Layer | Source setting/trigger | Meaning |
| --- | --- | --- |
| FSM checks | 0.01 s, 100 Hz | A scheduled state check; not 100 new trajectories per second |
| Collision safety checks | 0.05 s, 20 Hz | Safety callback timer |
| Closed-loop tracking/output | 0.01 s, 100 Hz | Velocity tracking timer, not an achieved-rate measurement |
| Nominal new local trajectory | Displacement, trajectory state and safety conditions | No fixed new-trajectory Hz reported by these settings |

Sources: [pinned FSM](https://github.com/wuyi2121/SCAN-Planner/blob/348e8a590a50a5a6bbab8d8c6dcfd171f009be26/src/planner/plan_manage/src/scan_replan_fsm.cpp),
[pinned controller](https://github.com/wuyi2121/SCAN-Planner/blob/348e8a590a50a5a6bbab8d8c6dcfd171f009be26/src/planner/plan_manage/src/closed_loop_controller.cpp).
The manager also has a branch that initializes from the preceding trajectory:
[pinned manager](https://github.com/wuyi2121/SCAN-Planner/blob/348e8a590a50a5a6bbab8d8c6dcfd171f009be26/src/planner/plan_manage/src/planner_manager.cpp).
Its acquired local identity is recorded in the experiment's
`references/2026-09-26_trajectory_diagnosis/source.json`; the manager hash
checked for the optimization audit is
`d5daf9ac96432e7b5334c4819f5d8688d046f366a48bd8f6eeac8a7ccda08863`.

## Consequences For The Local Requirement

Nav2's controller computes and publishes near-term velocity commands on its
wall-rate loop; SCAN's trajectory generation and tracking are separate
operations. [Pinned Nav2 controller](https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_controller/src/controller_server.cpp#L355).
The earlier [continuous-planning survey](2026-09-30_continuous_local_planning_upstream_survey.md)
records Nav2 defaults/examples and rolling-horizon/trajectory-state reuse.
The [time survey](2026-09-30_realtime_clock_upstream_survey.md) separates ROS
clock coherence, wall frequency, actual native/wall RTF and encoded FPS.

Our v45 complete-stack observation measured local 16.8619 Hz, raw controller
29.9648 Hz and global PCT 0.99998 Hz, with RTF 0.9400. The paper and timer
constants cannot be used to accept those results as local 30 Hz or simulation
1:1. See the [experiment archive](../experiments/2026-10-01_newton_nav2_timing_archive.md).

The [local optimization plan](../experiments/2026-09-26_newton_stair_reproduction/audits/2026-09-30_local_30hz_opportunities/PLAN.md)
proposes feasible-window reuse and valid-trajectory initialization, followed by
bounded solve/recovery and profiling. The upstream reuse branch is a design
reference, not proof that the current stair port can adopt it unchanged or
achieve 30 Hz. No v47 implementation or new qualification run exists.

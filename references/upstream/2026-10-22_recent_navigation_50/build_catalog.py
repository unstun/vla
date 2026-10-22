#!/usr/bin/env python3
"""Build the dated reference catalogue from verified local acquisition receipts."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
EXCLUDED = {
    'sjtuyinjie/Ultra-Fusion': 'README 明确说明当前仅发布可执行文件和演示，核心源码待论文接收后公开；工具脚本不作为完整算法开源计数。',
    'Robot-Nav/SA-MPPI': '根 LICENSE 为 Apache-2.0，但 README 第 13 节声明 GPLv3-or-later；源码保留，许可冲突单列，不计入本次达标数量。',
}
ORDER = ['导航与恢复', '地形与运动能力', '定位建图与三维感知', '视觉语言导航', '仿真评测与控制工具']
PRIMARY = {
    'HITSZ-NRSL/ReTAP-Planner': ['src/path_planning/include/local_planning/local_planning.h', 'src/path_planning/include/local_planning/trajectory_generator.h'],
    'lab-sun/Feetend-Planner': ['compute_body_traj.py'],
    'wty-yy/RoboGauge': ['robogauge/scripts/run.py'],
    'leggedrobotics/ocs2': ['ocs2_mpc/src/MPC_BASE.cpp', 'ocs2_mpc/include/ocs2_mpc/MPC_MRT_Interface.h'],
    'ros-controls/ros2_controllers': ['joint_trajectory_controller/src/joint_trajectory_controller.cpp'],
    'ivaROS/quad_gap': ['src/planner.cpp', 'src/trajectory_controller.cpp'],
}


def write_json(name: str, value: object) -> None:
    (ROOT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def enrich(row: dict, annotations: dict) -> dict:
    row = dict(row)
    name = row['name']
    row.update(annotations[name])
    source = ROOT/row['local_source_path']
    files = json.loads((ROOT/row['source_manifest']).read_text())
    paths = [x['path'] for x in files if not x['lfs_pointer'] and not x['symlink']]
    core = [p for p in paths if Path(p).suffix in {'.py', '.cpp', '.cc', '.h', '.hpp', '.rs', '.js', '.ts', '.cu'}
            and not re.search(r'(third.?party|vendor|external|SIBR_viewers|backward_ros|livox_sdk|libqhull|/tests?/)', p, re.I)]
    ranked = sorted(core, key=lambda p: (not bool(re.search(r'(main|planner|controller|train|eval|mapping|navigation|pipeline)', p, re.I)), len(p.split('/')), len(p), p))
    row['key_entrypoints'] = [p for p in PRIMARY.get(name, []) if p in paths]
    row['key_entrypoints'] += [p for p in ranked if p not in row['key_entrypoints']][:5-len(row['key_entrypoints'])]
    row['dependency_files'] = [p for p in paths if Path(p).name in {'pyproject.toml','setup.py','requirements.txt','environment.yml','environment.yaml','pixi.toml','package.xml','CMakeLists.txt','Cargo.toml','package.json'}][:16]
    readme = '\n'.join((source/p).read_text(errors='replace') for p in row['readme_files'][:2])
    # These are source excerpts, not commands executed or compatibility claims.
    row['readme_command_excerpts'] = [s.strip() for s in readme.splitlines() if re.match(r'^\s*(?:python3? |ros2 (?:launch|run)|roslaunch |pip install |uv (?:run|sync)|conda (?:create|env)|colcon build|catkin_make)', s)][:10]
    row['runtime_mentions'] = sorted(set(re.findall(r'ROS\s*2|ROS\s*1|Noetic|Humble|Jazzy|Isaac\s*Lab|IsaacLab|Isaac\s*Gym|MuJoCo|Mujoco|Habitat|CUDA|Genesis|Rust', readme, re.I)))
    row['freshness_group'] = '近半年默认分支提交' if row['recent_commit'] else '补充参考；不计入近期50个'
    row['canonical_readme'] = row['canonical_url'] + '/blob/' + row['pinned_commit'] + '/' + row['readme_files'][0] if row['readme_files'] else row['canonical_url'] + '/tree/' + row['pinned_commit']
    # Root license applies to the repository's own code; bundled dependencies and models may differ.
    row['license_scope'] = 'Root code license; preserve file-level third-party notices. Model/data rights not inferred.'
    return row


def main() -> None:
    acquisition = json.loads((ROOT/'raw_logs/acquisition.json').read_text())
    annotations = json.loads((ROOT/'annotations.json').read_text())
    baseline = json.loads((ROOT/'existing_references_before.json').read_text())
    accepted = [enrich(r, annotations) for r in acquisition if r['status']=='imported' and r['name'] not in EXCLUDED]
    accepted.sort(key=lambda r: (not r['recent_commit'], ORDER.index(r['category']), r['priority']!='优先', r['name'].lower()))
    ids = [r['name'].lower() for r in accepted]
    assert len(ids)==len(set(ids)) and not set(ids).intersection(baseline)
    recent = [r for r in accepted if r['recent_commit']]
    assert len(recent)>=50, f'Only {len(recent)} recent code repositories'
    excluded = [{'name':r['name'],'reason':EXCLUDED.get(r['name'],r.get('error')),'local_source_path':r['local_source_path']} for r in acquisition if r['status']!='imported' or r['name'] in EXCLUDED]
    total_bytes = sum(r['checked_out_bytes'] for r in accepted)
    manifest = {'topic':'Recent open-source references for Lite3 navigation','date':'2026-10-22',
                'status':'imported','reviewed':False,'source_review_completed':True,
                'review_scope':'Main-session checks of primary README, root license, source presence, freshness, canonical identity and Git integrity; no independent review or runtime reproduction.',
                'recent_commit_cutoff':'2026-04-22','required_recent_repositories':50,
                'accepted_repositories':len(accepted),'recent_repositories':len(recent),
                'supplementary_repositories':len(accepted)-len(recent),'checked_out_bytes':total_bytes,
                'baseline_unique_references':len(baseline),'repositories':accepted}
    # JSON syntax is deliberately used as a strict YAML subset, with no YAML dependency.
    write_json('repository_manifest.yaml',manifest)
    write_json('excluded_after_source_review.json',excluded)
    stats = {'date':'2026-10-22','accepted':len(accepted),'recent':len(recent),'supplementary':len(accepted)-len(recent),
             'by_category_recent':dict(Counter(r['category'] for r in recent)),
             'by_category_all':dict(Counter(r['category'] for r in accepted)),
             'created_years':dict(Counter(r['created_at'][:4] for r in accepted)),
             'duplicate_canonical_ids':0,'overlap_with_previous_references':0,
             'git_blob_mismatches':sum(r['verification']['git_blob_mismatches'] for r in accepted),
             'source_bytes':total_bytes,'source_files':sum(r['checked_out_files'] for r in accepted),
             'runtime_executions':0,'excluded':excluded}
    write_json('verification.json',stats)
    lines = ['# 新增开源参考仓库：2026-10-22','',
             f'已实际下载并核验 **{len(recent)} 个近半年有默认分支提交的新仓库**，另保留 **{len(accepted)-len(recent)} 个补充参考**，共 {len(accepted)} 个有效仓库身份。',
             '', '“近期”按 2026-04-22 至本次取得的默认分支提交判断，使用 Git commit 日期，不使用网页 updated_at 或最近 push 时间。较老项目的当前维护版本明确列出创建年份。',
             '', '本次以已有正式收藏和调研记录中的 361 个仓库身份做保守去重；同仓库分支、子模块和内嵌依赖不另计。独立仓库数量不代表原创算法数量：SRU 等衍生部署实现会标明来源关系。',
             '', '证据等级：**imported（源码已导入）**。检查了源码存在、许可证、Git 提交与本地文件一致性；没有运行上游安装、训练、仿真或真机程序。源码工作区按 sparse 模式跳过媒体、权重、数据和模型资产，子模块没有展开。',
             '', '按 Dr Sun 随后的要求，本批及既有参考源码已迁至 `/Volumes/ModelArchive/vla-references/`；项目中的 `source` 是外接盘链接，原阅读路径保持可用。见 [迁移核验与路径恢复](../storage/2026-10-22_external/README.md)。',
             '', '## 当前项目优先阅读','',
             '优先看 ros2_controllers 的停止/控制切换、Quadruped-PyMPC 的模型失配与接触控制、ReTAP 的地形轨迹、RoboGauge 的执行能力评测、MUSE 的实测速度、JEPLO 的 LiDAR 感知控制。SWAGGER 与 DDDMR 可补全路由和完整系统对照。Feetend-Planner 放在补充区，适合研究足端地形与身体轨迹。',
             '', '保留现有 v232/v233 基线与 v290 修复计划；收集参考不代表采用新架构。',
             '', '## 方向分布','', '| 方向 | 近半年提交 | 含补充参考 |','|---|---:|---:|']
    for cat in ORDER:
        lines.append(f'| {cat} | {sum(r["category"]==cat for r in recent)} | {sum(r["category"]==cat for r in accepted)} |')
    lines += ['', '## 50 个近期仓库','', '| # | 仓库与本地源码 | 创建 | 固定提交日期 | 代码许可证 | 当前用途 |','|---:|---|---|---|---|---|']
    for i,r in enumerate(recent,1):
        lines.append(f'| {i} | [{r["name"]}]({r["canonical_url"]}) · [本地]({r["local_source_path"]}) | {r["created_at"][:4]} | [{r["commit_date"][:10]}]({r["canonical_url"]}/commit/{r["pinned_commit"]}) | {r["license"]} | {r["use_for_lite3"]} |')
    lines += ['', '## 补充参考：不计入近期 50 个','', '| 仓库与本地源码 | 固定提交日期 | 用途 |','|---|---|---|']
    for r in accepted:
        if not r['recent_commit']:
            lines.append(f'| [{r["name"]}]({r["canonical_url"]}) · [本地]({r["local_source_path"]}) | {r["commit_date"][:10]} | {r["use_for_lite3"]} |')
    lines += ['', '## 源码复核后未计数','']
    for r in excluded: lines.append(f'- **{r["name"]}**：{r["reason"]} 本地记录保留。')
    lines += ['', '另有候选因许可证尚未完成核验、与当前任务关联较弱或已有引用而未入选；见 [候选表](candidates.json) 和 [GitHub 元数据](metadata.json)。NOASSERTION 或空字段表示本次没有确认可采用的许可证，不直接断言项目一定没有许可证。',
             '', '## 使用与恢复','',
             '- [固定版本、许可证哈希、入口和原始命令摘录](repository_manifest.yaml)',
             '- [校验摘要](verification.json)',
             '- [源码取得与恢复脚本](acquire.py)',
             '- [原始抓取和逐文件 SHA-256](raw_logs/)',
             '', '恢复命令（在项目根目录）：', '', '```bash',
             'python3 references/upstream/2026-10-22_recent_navigation_50/acquire.py --restore --workers 8',
             'python3 references/upstream/2026-10-22_recent_navigation_50/acquire.py --restore --verify-only --workers 8',
             '```', '',
             '恢复使用固定提交；不会运行上游代码。对同一次入库生成的逐文件清单，工作区 SHA-256 与 Git blob 校验分别记录；少数 CRLF 文件按仓库 .gitattributes 规范化后匹配原 Git 对象。根许可证不自动覆盖第三方依赖、模型权重或数据集。',
             '', '## 过程记录','',
             'Exa 两个方向各请求 15 条结果，并结合 GitHub 多组检索及逐仓库元数据核实。检索结果只是候选，最终以本地默认分支源码和许可证复核为准。',
             '', '初次校验误用了会读取遗漏 blob 大小的 git ls-tree --long，触发部分大对象按需下载并超时。已停止本次下载进程树、保留第一次记录，改为仅读取树对象后完成核验；本地 Git 缓存可能因此含工作区排除的对象。没有删除旧参考或失败记录。',
             '', '源码和原始日志沿用 references/upstream/.gitignore，不加入项目提交；清单、报告和脚本可以本地提交。当前研究分支继续遵守 docs/agents/git-workflow.md 的未发布研究保留要求。',
             '', '## 逐仓库阅读入口','']
    for r in accepted:
        source=r['local_source_path']
        lines += [f'### {r["name"]}', '', f'**{r["priority"]}** · {r["freshness_group"]} · `{r["pinned_commit"]}`', '',
                  r['use_for_lite3']+'。'+r['boundary']+'。', '',
                  '主要源码：'+ '；'.join(f'[{p}]({source}/{p})' for p in r['key_entrypoints']),
                  '', '原项目说明：'+f'[固定版 README]({r["canonical_readme"]})。'+
                  ' 运行环境提及：'+('、'.join(r['runtime_mentions']) or 'README 未提取到标准环境标签')+'。', '']
    (ROOT/'comparison.md').write_text('\n'.join(lines).rstrip()+'\n')
    print(json.dumps(stats,ensure_ascii=False))


if __name__=='__main__':
    main()

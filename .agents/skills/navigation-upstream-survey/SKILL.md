---
name: navigation-upstream-survey
description: |-
  调研、筛选并核验可用于 Lite3 VLA 与自主导航的开源仓库。触发：Dr Sun 说“找 VLA/开源导航仓库/借鉴别人代码/选基座/先跑别人项目”。
argument-hint: "[方向、候选仓库、时间窗或期望接口]"
user-invocable: true
context: inline
---

# Navigation Upstream Survey

Use this skill before selecting or importing an external navigation codebase.

## Read first

- `AGENTS.md`
- active Trellis task
- `.pipeline/literature/index.md`
- `.pipeline/terminology/terminology.md`
- `references/upstream/README.md`

## Workflow

1. Turn the request into checkable repository criteria without making them a
   permanent project scope limit.
2. Search papers, official project pages, and GitHub. A search result is only a
   lead; open the canonical repository and primary paper.
3. For each candidate record:
   - canonical URL and project page;
   - license;
   - default branch and pinned commit;
   - release and maintenance state;
   - robot, simulator, ROS, sensors, compute, and model assumptions;
   - available weights, datasets, Docker/conda files, and demo commands;
   - interface to locomotion: velocity command, geometric waypoint, pixel goal,
     language action, trajectory, or another form.
4. Rank candidates by evidence and adaptation cost. Do not rank by README
   polish or paper claims alone.
5. With Dr Sun's selection, clone into
   `references/upstream/YYYY-MM-DD_<topic>/source/<repo>`.
6. Copy `references/upstream/templates/repository_manifest.yaml` to the topic
   directory and fill it with URLs, commit pins, license, commands, and status.
7. Run the smallest original upstream smoke test that the available environment
   supports. Keep raw output under the same topic directory.
8. Report status precisely:
   - `surveyed`: repository and sources inspected;
   - `reproduced`: upstream command ran successfully;
   - `integrated`: project code uses it successfully;
   - `validated`: declared project acceptance test passed.

## Safety and source boundary

- `/Users/sun/tongbu/study/phdproject/vla` is the only VLA project source of truth.
- The local `machine-dog-nav` checkout is a read-only baseline until a clean
  commit is explicitly selected and imported.
- Upstream source directories are read-only references during survey.
- Do not paste unreviewed upstream code into project implementation paths.
- Check the license before copying code.
- Remote changes must sync back to the same local project paths before claims.
- Do not start formal training or real-robot actuation without Dr Sun's explicit
  authorization.

## Output

Write a concise comparison to
`.pipeline/survey/YYYY-MM-DD_<topic>_upstream_survey.md` with primary links,
commit pins, uncertainty, and a recommended first reproduction target.

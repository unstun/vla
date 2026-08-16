---
name: inno-code-survey
description: Survey, acquire, and map upstream code for Lite3 VLA or autonomous navigation. Use when Dr Sun asks to find a codebase, compare implementations, select a baseline, inspect how a paper maps to code, or prepare an upstream repository for reproduction.
---

# VLA Code Survey

Survey canonical upstream implementations before selecting or importing code.
Keep source inspection, import, reproduction, integration, and validation as
separate states.

## Read First

- `AGENTS.md`
- the active Trellis task and its planning artifacts
- `.pipeline/literature/index.md`
- `.pipeline/terminology/terminology.md`
- `references/upstream/README.md`
- `references/upstream/templates/repository_manifest.yaml`

## 1. Define Selection Criteria

Turn the request into checkable criteria. Include only dimensions relevant to
the task, such as:

- visual and language inputs;
- action representation and control frequency;
- supported robot, simulator, ROS/middleware, sensors, and compute;
- available weights, datasets, licenses, and original demo commands;
- compatibility with the intended navigation and locomotion boundaries;
- maintenance state and likely adaptation cost.

Do not turn the first candidate's interface into a permanent project contract.

## 2. Survey Primary Sources

Search primary papers, official project pages, release records, and canonical
repositories. Treat search snippets and third-party summaries only as leads.

For each candidate, record:

- canonical URL, project page, license, default branch, and pinned commit;
- paper, model, dataset, and dependency links;
- original installation, evaluation, and demo commands;
- expected hardware and runtime environment;
- key entry points, configuration files, model/data flow, and tests;
- claimed results versus evidence personally inspected or executed;
- unresolved assumptions and repository health.

Write the comparison to
`.pipeline/survey/YYYY-MM-DD_<topic>_upstream_survey.md` with `origin` and
`reviewed` frontmatter.

## 3. Acquire Only After Selection

After Dr Sun or the active task selects a candidate, create:

```text
references/upstream/YYYY-MM-DD_<topic>/
├── repository_manifest.yaml
├── comparison.md
├── raw_logs/
└── source/
    └── <repository>/
```

Copy and fill `references/upstream/templates/repository_manifest.yaml`, then
clone the exact candidate under `source/`. Pin the resolved commit in the
manifest. Keep `source/` and `raw_logs/` ignored while tracking the manifest and
comparison.

Do not copy upstream files into project implementation paths during survey.

## 4. Map Concepts To Code

For every component relevant to the proposed VLA path, identify:

- the public contract and data shape;
- entry points and configuration;
- model, perception, planning, and action flow;
- training and inference separation;
- checkpoint/dataset binding;
- tests and original evaluation commands;
- code and dependency seams that an import would touch.

Use file paths and symbols rather than large pasted code blocks. Note missing or
ambiguous implementation evidence explicitly.

Store detailed code mapping in the topic's `comparison.md`; keep the project
survey concise and source-backed.

## 5. Reproduction Boundary

Run an original upstream smoke only when the active task authorizes execution
and the environment supports it. Preserve the exact command and raw output in
the topic directory.

Use the strongest justified label only:

- `surveyed`: sources inspected;
- `imported`: pinned code brought into `/Users/sun/vla`;
- `reproduced`: original upstream procedure ran with recorded evidence;
- `integrated`: behavior works through this repository;
- `validated`: the declared project acceptance test passed.

Never start formal training, a long remote run, destructive data work, or
real-robot actuation without Dr Sun's explicit authorization.

## Deliverable

Return a concise candidate ranking, recommended first reproduction target,
primary-source links, pinned commits, license and environment risks, and the
next explicit human decision. If no candidate meets the criteria, say so rather
than lowering the evidence bar silently.

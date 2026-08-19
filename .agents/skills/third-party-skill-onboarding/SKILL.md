---
name: third-party-skill-onboarding
description: Use when Dr Sun asks to evaluate, install, copy, or adapt third-party skills from another repository into `/Users/sun/tongbu/study/phdproject/vla` or another project-local `.agents/skills` directory.
---

# Third-Party Skill Onboarding

Use this skill to bring external skills into a project without mixing official skills, old experiments, personal tools, and project-specific rules.

## Workflow

1. Read the target project's `AGENTS.md` and `CLAUDE.md` first.
2. Identify the source repository's official entry point. For Claude-style plugin repositories, prefer `.claude-plugin/plugin.json`.
3. Treat only skills listed by the official entry point as the recommended set.
4. Classify other source folders before discussing them:
   - `deprecated`: historical reference, default skip
   - `in-progress`: unfinished, default skip
   - `misc`: one-off tools, inspect before recommending
   - `personal`: author-specific, default skip
5. Install into the project-local directory:

```bash
python ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo owner/repo \
  --path skills/path/to/skill \
  --dest .agents/skills
```

6. If a skill already exists, stop and compare before overwriting.
7. For each installed skill, read `SKILL.md` and direct reference files. Add a project scope section only when the skill can write docs, mutate state, trigger persistent style changes, or affect research evidence.
8. Keep project-specific records in their correct harness location. For this VLA project:
   - research terminology: `.pipeline/terminology/terminology.md`
   - engineering vocabulary: `CONTEXT.md` when domain contexts exist
   - engineering decisions: `docs/adr/`
   - experiment decision logs and records: `.pipeline/experiments/`
   - upstream repository manifests: `references/upstream/`
   - long-term memory: `bigmemory/`
9. Stage only the skill directories involved in the current onboarding task.
10. Commit the onboarding change with a concise message.

## Review Rule

Do not recommend a source-folder skill just because it exists in the repository. A skill is a candidate only when it is in the official manifest, or Dr Sun explicitly asks to inspect non-manifest folders.

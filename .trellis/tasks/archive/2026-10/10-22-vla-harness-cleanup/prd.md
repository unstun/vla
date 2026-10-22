# Simplify the VLA project harness

## Request

Dr Sun authorized the proposed cleanup on 2026-10-22: keep Trellis core and
necessary project skills, leave research records and experimental data untouched,
and do not change global MCP configuration. Implementation is authorized.

## Acceptance criteria

- Keep all 12 existing Trellis skills and their installed contents.
- Keep nine project capabilities: archive, memory retrieval, status, research
  planning, literature survey, upstream code survey, paper analysis, arXiv
  conversion, and remote experiment execution.
- Remove redundant project skills, vendor discovery links, and unused custom
  agent definitions; synchronization must not restore retired vendor skills.
- Keep AGENTS.md concise and durable, without an obsolete project-state snapshot.
- Remove routine prompt/session injections; preserve Trellis context delivery
  for explicitly requested agents and Cursor's task-session bridge.
- Validate offline synchronization, repeated execution, link resolution,
  configuration syntax, and preservation of unrelated work.
- Do not edit .pipeline, bigmemory, research documents, upstream snapshots,
  implementation/experiment data, global MCP, or pre-existing Trellis changes.

## Scope

Project instruction/configuration files, skill discovery and selected skills,
harness specification, focused tests, and this maintenance task only.

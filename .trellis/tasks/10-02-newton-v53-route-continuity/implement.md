# v53 execution plan

Status: planning. First implementation target; requires frozen v52.
Read parent PRD/design/implementation package before starting. The latest final
planning summary needs subsequent explicit user approval. Inline execution/check;
no implement/check sub-agents.

After the recorded final-plan approval and this child's predecessor gates,
activate it with:
python3 .trellis/scripts/task.py start .trellis/tasks/10-02-newton-v53-route-continuity

## Ordered checklist

1. Verify frozen v52 native/manifest hash and replay fixtures.
2. Add failing actual callback/manager and sequential-reserve assertions before editing new native source.
3. Implement requested-pose exact context, transactional refresh and world-geometry hint reprojection.
4. Build, run parent-required positive/negative suites, replay and exact inactive cold geometry.
5. Review owned patch; freeze qualified v53 source/install and compact evidence.


## Validation and artifacts

Reuse actual v52 contract/remote_test and recorded corner replay entry points in
new version-owned tests. Parent implement.md lists mandatory suites, proof layers,
load preflight and hash/storage/retention checks. Preserve failed attempts.
No new physics in this child before component qualification; final two bounded
90-s idle-host Building recordings belong to integration acceptance.

Bulk inputs, generators' array outputs, compiled binaries and logs remain on
gpu5070ti. Return source/configuration, compact results and hashes; preserve
user work. Review staged owned diff before any meaningful verified commit.

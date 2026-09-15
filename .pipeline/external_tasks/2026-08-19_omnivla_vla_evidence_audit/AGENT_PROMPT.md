# External Agent Prompt: OmniVLA VLA-evidence audit

> Use this prompt only after Dr Sun explicitly approves the planning artifacts
> in `.trellis/tasks/08-19-omnivla-vla-evidence-audit/`. When Dr Sun pastes this
> prompt into a new Agent window, that paste is authorization to implement this
> child task, but it is **not** authorization for robot actuation, training,
> destructive cleanup, APK installation, or later roadmap children.

You are implementing the first child of the OmniVLA supervised Lite3 roadmap.
Your job is to produce an auditable evidence pack, not to decide whether
OmniVLA "really is a VLA."

## Active task and required reading

Active task:

`.trellis/tasks/08-19-omnivla-vla-evidence-audit`

Before editing or running anything:

1. Read `/Users/sun/tongbu/study/phdproject/vla/AGENTS.md` completely.
2. Read `.trellis/workflow.md` and the active task's `prd.md`, `design.md`, and
   `implement.md` completely.
3. Read every real entry in the task's `implement.jsonl` before implementation.
4. Confirm the task is still `planning`. Because this prompt is pasted only
   after Dr Sun approves it, run:

   ```bash
   python3 ./.trellis/scripts/task.py start 08-19-omnivla-vla-evidence-audit
   ```

5. Follow the `in_progress` Trellis workflow. If the planning artifacts differ
   materially from this prompt, stop and report the mismatch; do not silently
   choose a new scope.

## Source of Truth

The only source of truth is:

`/Users/sun/tongbu/study/phdproject/vla`

Pristine upstream source under
`third_party/2026-08-18_omnivla_5182600/OmniVLA/` is read-only. The sibling
`machine-dog` and `machine-dog-nav` repositories are read-only references.
Remote hosts are execution copies only.

## Sync Gate

You may make bounded diagnostic changes only in task-owned remote copies, but
every final source file, configuration, raw record, log, image, metric, and
manifest must be synchronized back to its intended local path. Before claiming
a panel ran, prove local/remote hash agreement and show the result in the local
working tree. A remote-only success is a failed handback.

Do not commit, archive, mark the task complete, or update long-term project
memory. Leave the local diff and artifacts for the primary window to inspect.

## Objective

Audit both pinned candidates with the same receive-only protocol:

- OmniVLA-original on `gpu40901`;
- OmniVLA-edge on the Jetson AGX Orin 64GB.

For each, trace the real image and language computation path and run the frozen
24-forward matrix specified in `design.md`: 12 language-panel attempts and 12
vision-panel attempts. Retain all attempts, including failures. Produce raw
records, numerical comparisons, overlays, code trace, claim matrix, failure
gallery, and a static human-review page with no preselected verdict.

## Allowed modification scope

- `.pipeline/experiments/2026-08-19_omnivla_vla_evidence_audit/**`
- This task's `task.json` only if execution metadata needs a factual update;
  do not materially rewrite the approved PRD/design/implementation plan.
- A narrowly required shared receive-only helper or test under
  `deploy/omnivla_lite3_receive_only/**` only when reuse is impossible without
  it. Search first, keep the diff minimal, and explain why the experiment-local
  implementation was insufficient.

## Forbidden scope

- No robot-control sender, MotionSDK call, ROS publisher, `/cmd_vel`, joint
  target, locomotion command, daemon, or autostart entry.
- No robot motion, camera reconfiguration, network changes, APK installation,
  latency benchmarking, weight training/fine-tuning, or V12 `model_149999`
  integration.
- Do not edit pristine third-party source, sibling repositories, existing prior
  experiment evidence, or protected vehicle-autonomy content on the Orin.
- Do not kill unrelated GPU, CARLA, Isaac, ROS, camera, or vehicle processes.
- Do not delete checkpoints or existing evidence to gain storage.
- Do not write a final "is/is not a VLA" conclusion. Report observations and
  unresolved interpretation for Dr Sun.

## Required execution sequence

1. Inspect the dirty working tree and preserve unrelated changes.
2. Pre-register the exact matrix, identities, hashes, expected/failure signals,
   timeouts, paths, and claim boundary using
   `.pipeline/templates/experiment_decision_log.md` before any new forward.
3. Build one shared, versioned run-record validator plus deterministic fixture,
   metrics, overlay, and review-page generation code. Do not let each consumer
   parse raw JSON independently.
4. Add targeted tests for wrong shape, NaN/Inf, identity mismatch, deterministic
   transforms, repeat-dispersion math, failure retention, and absence of an
   actuation dependency.
5. Produce code-path evidence with exact local file/line anchors for image,
   language, modality selection, model/fusion, action head, and `8 x 4`
   trajectory output in both candidates.
6. Preflight and run the OmniVLA-original batch in the task-owned path:

   `/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_vla_evidence_audit/`

   Verify source/checkpoint hashes and safe free GPU resources. Load once, run
   serially with a bounded wall timeout, stop the task process, sync back, and
   verify hashes locally.
7. Preflight and run the edge batch only under:

   `/home/nvidia/sun/vla_exec/2026-08-19_omnivla_vla_evidence_audit/`

   Verify source/edge/CLIP hashes and device state. Do not touch any directory
   outside `/home/nvidia/sun/`. Load once, run serially, clean up task processes,
   sync back, and verify hashes locally.
8. Generate:

   - immutable raw per-attempt JSON records;
   - stdout/stderr, environment, preflight/postflight, and source manifests;
   - machine-readable summary JSON and CSV;
   - trajectory overlays and a visible failure gallery;
   - `analysis/code_trace.md` and `analysis/claim_matrix.md`;
   - `review/index.html` with an `AI-prepared evidence; human decision required`
     banner and unselected human decision boxes;
   - an experiment `README.md` with exact claim boundaries.
9. Run all targeted tests and the existing receive-only suite, validate the
   Trellis task, verify every evidence manifest, and inspect the complete local
   diff.
10. Stop. Do not commit, archive, or continue to the latency/control tasks.

## Necessary command and log discipline

- Use `rg`/`rg --files` for local discovery.
- Use existing SSH configuration where available; verify the resolved target
  before remote actions. Do not put passwords into tracked files or logs.
- First remote action is read-only environment/preflight inspection.
- Local source changes must be hash-synchronized before execution.
- Every attempted forward receives a unique run ID and separate stdout/stderr
  or a structured per-attempt event record.
- Save all retained evidence beneath:

  `.pipeline/experiments/2026-08-19_omnivla_vla_evidence_audit/`

- Apply bounded process timeouts shorter than 30 minutes per remote batch. If a
  batch cannot finish safely in that bound, stop with partial evidence.

## Success signals

- The frozen 24-attempt panel is fully represented for each model, including
  failed attempts.
- Source/checkpoint/fixture identities and all local/remote hashes agree.
- Same-input repeats, prompt counterfactuals, and image counterfactuals are
  directly comparable in raw and visual form.
- The page exposes failures and does not select the human verdict.
- Static/runtime evidence confirms `actuation_enabled: false` and no control
  dependency.
- All task model/monitor processes are stopped after execution.

## Failure and immediate-stop signals

- Any source, checkpoint, CLIP, or fixture identity mismatch.
- An actuation/control import or sender appears.
- A malformed or non-finite output cannot be retained as a failure record.
- Insufficient safe compute resources or risk to unrelated workloads.
- Remote-only changes or missing sync-back artifacts.
- The report filters out failures, applies Lite3 metric calibration that was not
  measured, or upgrades the evidence label beyond the declared test.

If one model panel fails, preserve its evidence and continue to the other only
when doing so is independently safe and does not conceal the failure.

## Required handback format

Return one concise handback headed `Dr Sun,` with:

1. **Outcome:** what was actually executed for each model; no VLA verdict.
2. **Changed paths:** exact local files/directories owned by this task.
3. **Verification:** commands and verbatim pass/fail counts.
4. **Remote evidence:** resolved hosts, task-owned remote paths, run IDs,
   cleanup state, and local/remote hash proof.
5. **Counterfactual observations:** raw sensitivity versus repeat variability,
   including failures and semantic inconsistencies.
6. **Claim boundary:** strongest justified labels and everything still untested.
7. **Review entry:** absolute local path to `review/index.html`.
8. **Independent-review note:** explicitly state that the primary window and
   Dr Sun must inspect the packet before any task completion or next stage.

Also provide `git status --short` and `git diff --stat` output. Do not stage or
commit anything.

# Implementation plan: OmniVLA vision-language-action evidence audit

Do not execute this plan until Dr Sun explicitly approves the final planning
summary and the task status is changed from `planning` to `in_progress`.

## Phase 0: Preflight and immutable protocol

- [ ] Read `AGENTS.md`, this task's `prd.md`, `design.md`, and the curated
      context files.
- [ ] Inspect `git status`; preserve every pre-existing modification and
      untracked path.
- [ ] Create
      `.pipeline/experiments/2026-08-19_omnivla_vla_evidence_audit/` with the
      reviewed experiment decision-log template.
- [ ] Write the frozen matrix, image transformations, exact prompts, repeats,
      identities, expected signals, failure signals, stop rules, artifact paths,
      and claim boundary before running either model.
- [ ] Verify pristine upstream and checkpoint hashes against existing manifests.
      Stop on any mismatch.

## Phase 1: Shared local audit tools

- [ ] Search existing receive-only protocol, engine, validation, and plotting
      code before adding helpers. Reuse it where contracts match; do not copy
      validators into multiple scripts.
- [ ] Implement one versioned run-record schema and validator.
- [ ] Implement deterministic fixture generation for mirror and blur, with
      transformation parameters and hashes.
- [ ] Implement shared trajectory metrics and overlay generation.
- [ ] Add unit tests for schema rejection, non-finite values, wrong shape,
      identity mismatch, fixture determinism, repeat metrics, and failure
      preservation.
- [ ] Add a static source scan proving the new runtime has no actuation
      dependency or sender.

## Phase 2: Code-path evidence

- [ ] Trace OmniVLA-original image and language inputs from the wrapper through
      preprocessing/model/action head to the returned trajectory; cite exact
      local file/line anchors.
- [ ] Trace OmniVLA-edge image and CLIP-language inputs through its fusion/model
      and trajectory head; cite exact local file/line anchors.
- [ ] Record where modality masks/IDs select language-only behavior.
- [ ] Record what is not proven: learned causal use, semantic correctness,
      metric scale, collision safety, and locomotion compatibility.

## Phase 3: OmniVLA-original bounded remote batch

- [ ] Preflight `gpu40901`: environment, source/checkpoint hashes, free VRAM,
      existing task processes, and unrelated workloads. Do not stop unrelated
      jobs.
- [ ] Sync only task-owned wrappers/configuration to
      `/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_vla_evidence_audit/` and
      verify local/remote hashes.
- [ ] Load the pinned original model once, then run its 24 serial matrix
      forwards under a bounded wall timeout.
- [ ] Save one immutable record per attempted forward, including failures.
- [ ] Stop the task model process and verify cleanup.
- [ ] Sync all raw records, stdout/stderr, environment, pre/postflight, and
      manifests back to the local experiment path; verify SHA-256 locally.

## Phase 4: OmniVLA-edge bounded Orin batch

- [ ] Preflight the Orin without modifying protected vehicle-autonomy content;
      use only `/home/nvidia/sun/`.
- [ ] Verify the pinned edge/CLIP/source hashes and available RAM/GPU state.
- [ ] Sync only task-owned wrappers/configuration to
      `/home/nvidia/sun/vla_exec/2026-08-19_omnivla_vla_evidence_audit/`.
- [ ] Load the edge model and CLIP once, run the same 24 serial matrix forwards,
      and retain every attempt.
- [ ] Stop task processes, recheck non-interference, sync back, and verify all
      hashes locally.

## Phase 5: Analysis and review page

- [ ] Validate every raw record through the shared decoder before analysis.
- [ ] Generate machine-readable summary JSON/CSV, overlays, code trace, claim
      matrix, and a failure gallery.
- [ ] Generate `review/index.html` with no preselected final verdict.
- [ ] Ensure plots distinguish raw normalized values from any derived display
      scale and do not label upstream 0.1 m spacing as Lite3 calibration.
- [ ] Write an experiment README stating exact successful and failed panels,
      timings as observations rather than benchmarks, and the strongest
      justified evidence labels.

## Phase 6: Quality and handback

- [ ] Run all new targeted tests plus the existing
      `deploy/omnivla_lite3_receive_only` suite.
- [ ] Run task validation and evidence-manifest verification.
- [ ] Inspect `git diff` and untracked files; confirm no sibling repository,
      robot, APK, network, camera, locomotion, or unrelated Orin content changed.
- [ ] Do not commit, archive, or mark the task complete.
- [ ] Return: changed paths, commands, raw test output, remote execution IDs,
      artifact hashes, failures, untested paths, and the absolute path to
      `review/index.html` for independent review.

## Success signals

- Both model panels have pinned identities and complete attempted-run records.
- Counterfactual and repeat panels are directly comparable and failures remain
  visible.
- The review page and raw artifacts reproduce from local source and manifests.
- No actuation path exists and all remote task processes are stopped.

## Failure and stop signals

- Source/checkpoint/fixture hash mismatch.
- Control dependency or robot sender appears in the task runtime.
- Any remote-only source change or missing sync-back artifact.
- Non-finite/malformed output that the record validator fails to retain.
- Unbounded model process, insufficient safe resources, or risk to unrelated
  workloads.
- Evidence page hides or drops a failed condition.

## Rollback points

- Before remote run: remove only the task-owned local experiment directory.
- After either remote panel: preserve failure evidence, stop task processes,
  and remove only that task-owned remote copy if rollback is requested.
- Never delete existing OmniVLA checkpoints or prior experiment evidence.

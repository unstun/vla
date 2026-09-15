# Implementation plan: direct Orin TIC-VLA pretrained inference

No step begins until Dr Sun gives fresh approval after reviewing this final
plan. Formal training and real-robot actuation remain prohibited.

## Phase 0: provenance and read-only preflight

- Reconfirm the upstream commit, release URLs, license, checkpoint hash, base
  model identifier, and official run instructions.
- Recheck Orin identity, architecture, Python/PyTorch/CUDA versions, free
  storage, RAM, routes, relevant listeners/processes, and owned directory size.
- Stop if the target or ownership boundary differs from the approved design.

## Phase 1: import and isolate

- Import the pinned upstream into the local pristine path and complete the
  repository manifest.
- Create the local evidence directory and exact remote child-directory layout.
- Transfer the pristine snapshot to the remote `pristine/` directory, make a
  separate `work/` copy, and record hashes before adapting it.

## Phase 2: acquire official assets

- Download the upstream-selected InternVL3-1B base assets and official
  `TIC-VLA-model.ckpt` directly into task-owned remote paths.
- Save source URLs, resolved revisions where available, byte sizes, and
  SHA-256 hashes. Require the checkpoint hash to equal the published value.
- Do not acquire the full TIC-VLA dataset.

## Phase 3: compatibility overlay and load gates

- Audit Python 3.8 compatibility and binary dependency requirements.
- Add only numbered, documented patches to the work copy and task-local
  dependencies/caches. Copy every overlay back to the local evidence path.
- Run compile/import smoke before model execution.
- Inspect checkpoint structure and state dict on CPU, recording all missing,
  unexpected, and shape-mismatched parameters.
- Load the base model and checkpoint on CUDA. Stop on unexplained weight loss,
  incompatible binary dependencies, or unsafe memory pressure.

## Phase 4: bounded offline inference

- Copy the retained Lite3 RGB fixture into `inputs/` with its provenance and
  SHA-256. Build the explicitly synthetic repeated-frame/neutral-state input.
- Confirm statically and at runtime that the task starts no robot sender,
  listener, service, daemon, ROS command path, SDK command, or `/cmd_vel`
  publisher.
- Run one warm-up, then three serial measured forward passes.
- Save raw language responses, waypoint tensors, shape/dtype/finite checks,
  load and inference timings, peak CUDA memory, and available temperature/power
  samples for each run.

## Phase 5: postflight, sync-back, and validation

- Repeat route, process/listener, storage, and owned-path checks.
- Sync manifests, patches, dependency inventories, logs, inputs metadata, and
  raw outputs to the local evidence directory.
- Run task validation, JSON/YAML parsing, targeted tests, diff checks, and a
  final read-only review against every acceptance criterion.
- Report failed criteria explicitly. Do not promote a partial run to
  `reproduced`, `integrated`, or `validated`.

## Stop rules

Stop immediately and preserve evidence if any of these occurs:

- a robot-control sender/listener or persistent service is discovered;
- a required action would modify system Python, PyTorch, CUDA, JetPack, network
  configuration, protected data, or files outside the owned task path;
- free root storage would fall below 10 GiB;
- checkpoint identity or state-dict compatibility cannot be established;
- CUDA out-of-memory, unsafe temperature/power behavior, or an incompatible
  binary dependency cannot be resolved inside the task path;
- model outputs are non-finite or do not match the source-inspected contract.

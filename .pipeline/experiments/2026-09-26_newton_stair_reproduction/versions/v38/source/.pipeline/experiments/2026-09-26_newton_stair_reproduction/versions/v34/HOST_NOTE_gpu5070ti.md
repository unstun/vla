# v34 trial on gpu5070ti: host note

Written before the freeze and before any v34 trial physics.

## Dr Sun's decisions

- **Where, 2026-09-29, after the corridor-entry diagnosis:** v34's single trial runs on gpu5070ti, "as for v33". The
  option as offered was: "Same runner, host note, abort rule and retry rule as v33. The robot controller files kept
  for v34 are still there."
- **The private bytes, 2026-09-29:** the factory controller snapshot and its arm64 image stay on gpu5070ti for v34.
  Their removal is to be asked again after v34.

## What applies

`versions/v33/HOST_NOTE_gpu5070ti.md` applies to v34's trial unchanged. That note was reviewed with the port in
five rounds. The substitutions are v33 → v34 in run IDs and host-file paths, and scan64 → scan65 in the native
build. It covers:
- **Execution and monitoring:** the execution copy and its environment, the `docker` → podman shim, QEMU for the
  factory controller, and the pre-run snapshot, sampler, post-run record and self-checked manifest. Monitoring stays
  light.
- **The quiet-host refusals:** podman failure, a running container of this user, `qemu-aarch64` not enabled, load
  above 1.0, a GPU compute process, ports 46200–46203.
- **The abort rule:** SIGTERM to the runner's pid only, never its process group or `run_bounded`. The note gives
  the runner's handling and the residual risk N31.
- **The lock, and the infrastructure-failure rule:** a retry before physics takes the next run ID; after physics
  starts, the run is the outcome.
- **The Linux sampler's record,** and the rule on other users' command lines. These are never recorded. A root
  process there carries a tunnel token.
- **The known inaccuracies** in the run's own records, and the host's claim boundary: different numerics from the
  MacBook, a native navigation container, host-specific timing, and the container's shared clock.

## What is new for v34

- **The runner:** `hosts/2026-09-29_gpu5070ti/v34_trial_run.sh`.
  - **Derivation:** from `v33_trial_run.sh` (sha256 `2649f0e8…`) by substitution only (`make_v34_files.py`,
    `make_v34_files.json`).
  - **What changed:** 15 lines, each holding "v33" or the scan64 path.
  - **Everything else is identical:** the refusals, lock, handler, abort escalation, sampler, post-run recovery and
    manifest.
  - **The start command:**

    ```
    setsid nohup bash /home/sun/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/hosts/2026-09-29_gpu5070ti/v34_trial_run.sh v34_historical_full01 > /dev/null 2>&1 < /dev/null &
    ```

- **The pre-physics gate check:** `checks/p1_gates_v34.py`.
  - **Derivation:** from `checks/p1_gates.py` by the same substitutions.
  - **The added gate:** the launcher's reviewed-candidate check (`scripts/run_local_episode.py` lines 158–162).
- **The sync:** `PHYSICAL_RUN_PLAN.md` lists what is copied after the freeze. The check requires every file of
  v34's manifest to match on both hosts before the gates run.
- **Host files:** in `versions/v34/host/`, named for the run ID, as v33's were.

## Host use

- **During v34's run:** the host-use rule of v33's trial applies. Nobody else uses gpu5070ti, and the
  `machine-dog-nav` blackbox recorder may keep running.
- **Enforcement:** the runner's refusals enforce what they can see.
- **Before the start:** the pre-run snapshot records the host's state.

# Diagnostic run `diag_v31_clock01`: pre-registration

Written before the run, after the saved-log analysis and the replay benchmark.

## Why

- **Saved logs:** v31's fatal pause was a 347 ms control step (sim 27.716–27.736 s). Its body-pose
  publishes stopped for 288 ms between two substep publishes. The command was `active`, and there was no
  reconnect around it.
- **Planner:** SCAN logged nothing from 83.6 to 85.2 s on the Linux monotonic clock, so it was not
  planning.
- **Replay benchmark:** v31's own commands replayed through the same physics, scan and writer threads
  reproduce its states exactly. They did not reproduce any step over 127 ms, either alone or with a
  four-CPU container load.
- **What is missing:** what the Mac process is doing during a live-loop stall.

## What runs

- **Configuration:** the frozen v31 configuration with v31_historical_full01's exact flags, under
  `scripts/run_bounded.py`, run ID `diag_v31_clock01`.
- **The only substitution:** the Newton worker runs `diag_worker.py`, which executes the unchanged
  pinned `scripts/newton_episode.py` after adding observation only:
  - step and substep wall and CPU times;
  - a 150 ms faulthandler stack dump of all threads;
  - thread names.
- **Launcher (`diag_launch.py`):** it adds an external wake-up probe process and a 1 Hz host sampler
  (load average, top processes, paging counters).
- **Status:** this is a diagnostic run. It is not a v31 trial, and its navigation outcome is not a v31
  result.

## How it discriminates

For every step longer than 150 ms, the run records two numbers:
- main-thread CPU time, compared with wall time;
- the external probe's lateness at the same moment.

| Main-thread CPU in the stall | External probe | Reading |
|---|---|---|
| ≈ wall time | on time | the physics computed for that long (a pathological step) |
| ≪ wall time | on time | the main thread waited inside the process (GIL, lock or I/O); the stacks say where |
| ≪ wall time | late by a similar amount | the OS did not schedule the process (CPU or memory); host samples say what ran |

## Attempts

- **`diag_v31_clock01` is invalid, because of an instrumentation bug.** The first worker initialized
  Warp before running the pinned file. The pinned preamble then reset `kernel_cache_dir` to the
  unversioned root, and its own `wp.init()` was a no-op.
  - All 49 kernel modules compiled cold. The first LiDAR scan took 952 ms to compile, and the episode
    stopped on its own guard, "Captured scan did not finish before the next sensor period", before
    navigation.
  - The cold compile wrote 49 module directories into `runtime/warp-cache/` itself, outside the
    `1.17.0/` directory that pinned runs read. They are regenerable, and they are left in place.
- **`diag_v31_clock02`:** the corrected worker patches `lite3_newton` through an import hook and imports
  nothing from Warp. It adds the per-step `rusage_info_v6` deltas:
  - process CPU time;
  - the part of it on performance cores;
  - runnable time, which on this machine includes running time, so waiting for a CPU ≈ runnable − CPU;
  - page-ins.

  **It is invalid too, because of the instrumentation.** Kernels loaded from cache, and 285 control steps
  (sim 11.04–16.72 s) ran normally.
  - **The failure:** at the first step over 150 ms, `faulthandler.dump_traceback_later` wrote one dump.
    That dump walks thread stacks without the GIL, and here it raced with the running main thread. A native
    `sample` showed its watchdog spinning in `dump_frame`, while the main thread was blocked for good in
    `cancel_dump_traceback_later`.
  - **What the dump shows:** at 150 ms into that step, the main thread was inside MuJoCo-Warp's constraint
    solver (`solve` → `capture_while` → `_solver_iteration`).
  - **Ending the run:** the worker was stopped with SIGTERM after 776 s. The runner then tore the
    container down, so no container remained.
- **`diag_v31_clock03`:** the worker takes stacks only under the GIL. A Python watchdog thread polls every
  10 ms, and once a step passes 150 ms it records `sys._current_frames()` every 50 ms, up to 8 times per
  step. It also records its own wake-up lateness.

- **`diag_v31_clock04`** was added after `diag_v31_clock03`'s analysis, to log what that run could only
  infer. It is the same configuration and worker, with two additions:
  - every cyclic garbage collection (`gc.callbacks`), logged directly;
  - stack samples during gaps over 150 ms between steps.

  It ran 390 s of simulation and ended on `odom_stale`. Its results are in `RESULT.md` section 4.

## Stop rule

- **Limits:** the run ends by itself or at the supervisor's deadline.
- **Stall counts:** the v31 trial had 3 steps over 250 ms in 946, and v30 had 13 in 3,022. A run
  without such a stall is recorded as such, not repeated silently.

# Newton trial pipeline on gpu5070ti: port and validation

## Decision

- **Dr Sun, 2026-09-29, after v33's freeze:** "u can process on gpu 5070ti", then "u can use newton too on 5070ti".
  - Asked where v33's trial should run, he chose to port the pipeline to gpu5070ti first and validate it with a
    baseline run before v33 runs there.
  - The option he chose included two conditions: he installs ARM emulation there (sudo), and he approves copying
    the robot's private controller snapshot there.
- **Why a port is needed:** every earlier trial (v3–v32) ran on the MacBook. The pipeline has four Mac-bound parts:
  - Docker Desktop, with `host.docker.internal`;
  - Docker Desktop's image IDs;
  - an arm64 factory-controller container that runs natively on Apple Silicon;
  - pyzmq loaded from a directory that held only a Python 3.10 build.
- **What does not change:** v33's frozen sources. The worker still runs Newton physics on the CPU
  (`wp.set_device("cpu")`), so the GPU is not used. GPU physics would change the numerics and would be a separate
  version.

## Source of truth and sync gate

- **Source of truth:** the local repository at `/Users/sun/tongbu/study/phdproject/vla`. The 5070ti holds an
  execution copy at `~/vla_exec/vla`, with the same relative paths. Every run's gates check that copy before
  physics: the v33 manifest (3,061 files), the 99 records of `setup/runtime_sources.json`, the native-build
  identity and the 36 scene inputs.
- **What was copied:** the 3,061 manifest files, plus the runtime directories a run loads, 7,585 files and
  882 MB in all (`checks/sync_list.txt`):
  - the native build `runtime/scan64_input_refresh_v31`;
  - `runtime/foreground_py310`;
  - the stair experiment's inputs, references, setup, archived configuration, runtime sources, scripts and
    repairs;
  - `versions/v33`, without its `source/` snapshot, which no run reads;
  - the archived bridge run `walk_scan28_height030_right_v1`, without its returned artifacts;
  - the factory audit, including its private snapshot;
  - the Mac policy experiment's scripts, assets, policy, setup and runtime assets.

  Old run outputs, caches and the Mac virtual environment were not copied.
- **Added after the first scene build failed on a missing import:**
  - the Mac policy experiment's `references/` (the `lite3_reference` package that `lite3_newton.py` imports),
    `validation/`, `source/` and `README.md`;
  - `2026-09-16_pi_cortex_harnessvln/isaac_runner/stance_hold.py`, which `newton_stance.py` loads and pins by
    SHA-256. The local copy matches the pin. It is not in the v33 manifest, so P1 did not look for it;
  - `runtime/zmq_linux` with the added module, and `runtime/matplotlib`;
  - for P5, `runs/v31_historical_full01/telemetry.jsonl` and its `inputs/`;
  - after P6 attempt 01, the native build's 17 `.pyc` files in `__pycache__` and one more file (18 in all).

  These additions are not in `checks/sync_list.txt`. The execution copy's file list with SHA-256s, without the Warp
  kernel cache and the Python 3.12 bytecode written at run time, is `checks_out/execution_copy_manifest.txt`
  (port review round 1, N3). It was regenerated after the fixes of rounds 2 (N19), 3, 4 and 5, and is a snapshot
  at the time recorded in its first line. At run time the launcher's own gates check every pinned file, and the
  runner records the hashes of its own tools.
- **Not copied, and not needed during a run:** `scripts/replay_local.py` reads an 821 MB repairs directory, and
  `scripts/render_heading_view.py` has a hardcoded Mac path. Both are analysis tools, and videos are rendered on
  the Mac after the run is copied back.
- **Back to the repository** (corrected after port review round 1, B2; the first version said every file had been
  copied back, which was not true):
  - the port's logs from the 5070ti, in `remote_logs/`, with `SHA256SUMS_remote.txt`;
  - the check outputs, in `checks_out/`;
  - run outputs, under `runs/`.

  The arm64 image archive stays on the 5070ti (`LOCAL_ONLY_BYTES.json`).

## Environment differences, all outside the pinned files

| Part | MacBook | gpu5070ti |
|---|---|---|
| Host | macOS 26.5.2, arm64 (Apple Silicon) | Ubuntu 24.04.3, x86_64, AMD Ryzen 7 9700X (8 cores, 16 threads), 30 GB |
| SCAN/backend container | Docker Desktop; amd64 image under emulation | rootless podman 4.9.3; the same image natively |
| Factory controller container | arm64, native | arm64 under QEMU user-mode emulation (`qemu-user-static` 8.2.2, installed by Dr Sun) |
| Worker Python | 3.12.13, 105 packages (`mac_worker_environment.json`) | 3.12.13, the same 105 packages and versions (`gpu5070ti_worker_environment.json`, `requirements_linux.lock`) |
| Worker pyzmq | `runtime/zmq_macos` (cp312 macOS) | `runtime/zmq_linux` plus the cp312 Linux backend (`zmq_linux_cp312.json`) |

- **Images:**
  - **SCAN/backend (amd64):** pulled on the 5070ti by the pinned digest, as
    `docker.io/koide3/direct_visual_lidar_calibration@sha256:f7363cc3…`. Podman reports that same digest.
  - **Factory (arm64):** `lite3/ddsrouter:v3.5.2-arm64` is private, so it was saved on the Mac and loaded on the
    5070ti. The pinned `sha256:1c102582…` is an OCI index. Its arm64 manifest `sha256:cd044354…` names config
    `sha256:ea7f3ad4…`, which is podman's image ID. The seven layer diff IDs are identical.
- **The `docker` shim** (`docker` in this directory, installed as `~/vla_exec/bin/docker` and first on PATH for a
  run) forwards every call to podman. It makes three changes:
  - it replaces the two pinned image IDs with the references above;
  - it gives a `run` without its own network slirp4netns with host-loopback access, and maps
    `host.docker.internal` to that loopback (10.0.2.2), as Docker Desktop provides;
  - it adds `--userns=keep-id` when a container's `--user` is the invoking host user, so that user owns the
    bind-mounted files, as with Docker Desktop's file sharing (added after P5 attempt 01, below).

  With `VLA_SHIM_LOG` set, it also appends each incoming call and the podman call it made
  (`checks_out/shim_log_attempt02.txt`). A run's `container_command.json` keeps the Docker form (port review round
  1, N4).
- **Tested, with the outputs saved after port review round 1 (B2):** `checks_out/net_test_attempt01.txt` and
  `_attempt02.txt`, `keepid_test_attempt01.txt` and `_attempt02.txt`:
  - the main container resolves `host.docker.internal` to 10.0.2.2;
  - it reaches a server on the host's 127.0.0.1;
  - the host reaches a port the container publishes on 127.0.0.1;
  - the factory container runs as the host user and reads both private libraries;
  - its snapshot mount stays read-only.

  The first runs of these tests printed only. The earliest result, the arm64 image failing with "Exec format error"
  before emulation was installed, was seen only in the session and cannot be repeated now.

## Validation, criteria fixed before each check ran

| Check | What | Pass |
|---|---|---|
| P1 gates | the launcher's version and record gates executed from its own text on the execution copy, plus the native identity and scene inputs | all pass |
| P2 environment | worker packages against the Mac's | the same names and versions |
| P3 ROS smoke | `versions/v33/ros_smoke.py` (`trial`), byte-identical, in the pinned image through the shim, with `run_ros_smoke.sh`'s container command | all five checks pass |
| P4 factory controller | the arm64 controller under emulation, inside P5's replay | it compiles and reports ready within the unchanged 45 s; the startup finishes within the unchanged 240 s; wherever its input equals the Mac's at the same step (`versions/v32/gc_schedule_check/none/factory_full_rate.npz`), its output is bit-identical |
| P5 physics replay | `versions/v32/gc_schedule_check/bench_gc.py` (mode `none`) on `v31_historical_full01`'s commands, as v32's K3 ran it on the Mac (joint-state error 0.0 over 946 steps) | the replay completes without a fall. An error of 0.0 means bit-identical physics. A larger error does not fail the port: later 5070ti results are then labelled numerically different from the Mac, with the error reported over time (the RL policy runs in ONNX Runtime, whose kernels differ between ARM and x86) |
| P6 end-to-end | one bounded run through the real launcher on the empty floor with v33 (`--scene flat_empty_long`, `versions/v33/flat_planner.yaml`, otherwise the trial's flags), run ID `port5070_v33_flat01`, goal wall budget 600 s within a 900 s deadline, so the episode ends itself before the wrapper would kill it (a killed launcher skips its container cleanup) | no infrastructure failure (container, network, shim, emulation, copy-back); the factory startup completes and the robot walks under SCAN's commands. Navigation outcomes are reported, not judged |

- **After P1–P6:** an independent review of this port, then v33's trial on the 5070ti. A host note is written in
  `versions/v33` before that run, since `PHYSICAL_RUN_PLAN.md` said "Local simulation only".
- **Claim boundary:** a port check shows only that the pipeline runs there as recorded. It is not acceptance
  of anything, and a result on the 5070ti does not replace or reproduce a MacBook result.

## Results so far

- **P1 passed:** version gate (3,061 files), record gate (99), native identity and all 36 scene inputs. Its first
  runs printed only. Re-runs with saved output: `checks_out/p1_gates_attempt01.json` and `_attempt02.json`, which
  also cover the native build's `install_sha256.json` and the free-disk rule (port review round 1, B2).
- **P2 passed:** 105 packages, identical names and versions.
- **P3 passed:** `p3/ros_smoke_trial_attempt01.json`. The decisions equal the Mac's attempt 03 check for check;
  the harness's longest command-receipt gap was 0.021 s, against 0.027 s on the Mac.
- **Warp kernel cache** (`checks/warm_kernels.py`; its log is `checks/warm_kernels_run4.log`):
  - **Why:** the Mac runs used a populated cache; a first compile on a fresh host would otherwise run inside
    the factory startup's wall limit.
  - **What it does:** it builds the worker's scene, then compiles every module on the CPU (`wp.force_load`).
  - **First attempt failed, as an artifact of the warm-up itself:** Newton's `geometry.narrow_phase` did not
    compile. `force_load` compiled with Warp's default tile block size of 256 (`WP_TILE_BLOCK_DIM 256`), but a
    real CPU launch always uses 1 (`wp.launch`, `context.py:11250`), as the Mac's cache shows.
  - **With `block_dim=1`:** every module registered at that point compiled, in 33.4 s. `narrow_phase` built as
    module `81632d4`, the same hash as on the Mac.
  - **What `force_load` cannot build** (corrected after port review round 1, B1): modules that a run generates while
    it runs, such as the solver's closures and per-variant kernels. They compile only in a real run. P5 attempt 02
    compiled 27 of them (below).
  - **Module hashes on both hosts:** a first comparison of cache directories (`checks/*_warp_cache_dirs.txt`) found
    28 of 32 shared modules identical.
  - **The comparison after P5,** from the runs' own load logs: the Mac's historical trials (v29–v32) loaded 49
    modules. P5 attempt 03 and P6 on the 5070ti each loaded exactly those 49, with the same names and hashes, and
    compiled none. Warp derives each hash from the kernel source and build options.
- **ARM emulation:** Dr Sun installed `qemu-user-static` 8.2.2. `qemu-aarch64` is registered with flags `POF`,
  and the factory image starts (`aarch64`, g++ 9.4.0).
- **P5 attempt 01 failed before physics** (`p5_replay_none_attempt01/`, kept):
  - **The error:** the factory actor compiled under emulation, then could not open
    `/snapshot/lib/ras_lib/libdeepras.so` ("Permission denied").
  - **The cause:** the private libraries are owner-only (mode 600) on both hosts. The factory container runs as
    `--user <uid>:<gid>` of the invoking user (1000:1000 here, 501:20 on the Mac). Docker Desktop's file sharing
    lets that user read them. In rootless podman, that uid inside the container is not the host user who owns
    them.
  - **The fix, in the shim** (translation 3): a `run` or `create` whose `--user` is the invoking host user gets
    `--userns=keep-id`. File permissions were not loosened. Tested: the container runs as uid 1000 (sun), reads
    both libraries, and the snapshot mount stays read-only. The main container's networking test still passes.
  - **The runner** became attempt-numbered (`checks/p5_replay.sh <attempt>`).
- **P5 attempt 02 failed in the replay loop** (`p5_replay_none_attempt02/`, kept):
  - **What worked:** the emulated factory controller completed the startup, and its phase times equal the Mac's
    to every printed digit.
  - **The error:** "Captured scan did not finish before the next sensor period."
  - **The cause** (corrected after port review round 1, B1; the first version named the lidar's own module,
    `geometric_lidar fd8ffc5`, which the warm-up had already compiled): Warp modules that exist only once a run
    generates them.
    - 26 compiled during the factory startup.
    - At the first scan, Newton's ray-intersection closure (`intersect_ray__locals___intersect_ray_kernel_962a4840`,
      hash `14d5500`) took 1,128 ms to compile on the scanner thread, while physics stepped ahead
      (`p5_replay_none_attempt02_stdout.log`).
  - **After it:** all 27 are cached, and attempt 03 compiled nothing.
  - **Why it matters for real runs:** the real worker makes the same check (`scripts/newton_episode.py:230`), so a
    run with a cold cache fails the same way. On a new host, a real run such as this replay must precede a trial.
- **P5 attempt 03 completed** (`p5_replay_none_attempt03/`; comparison in `checks/compare_p4_p5_attempt03.json`):
  - **Pre-registered pass: no fall.** Lowest base height 0.347 m and minimum up-vector 0.944 on the 5070ti,
    against 0.347 m and 0.959 on the Mac; 946 control steps on both.
  - **Not bit-identical, so 5070ti results are labelled numerically different from the Mac.**
    - **The metric** is the largest absolute difference in the state vector `joint_q`: base position in m,
      quaternion, and joint angles in rad (units corrected after port review round 1, N1).
    - **After the startup:** it is 9.1e-6, the base x position, in m. Joint angles differ by at most 1.5e-6 rad at
      the first replay step, and by at most 2.7e-6 rad over the standing steps 1–66 (round 2, N17).
    - **Once the recorded walking commands begin (replay step 67):** it passes 1e-3 at step 131 and reaches 0.25 by
      step 250. It peaks at 1.29 rad, a joint angle, at step 451.
    - **The bases** are 0.13 m apart at step 250, and 0.63 m apart at the end (step 946, about 17.6 s after the
      first walking command).
    - **Against the trial it replays:** the error is 1.29 on the 5070ti, against exactly 0 on the Mac.
  - **Where the difference starts** (corrected after round 1, N1): at the controller's first input.
    - Two near-zero entries differ: `gyro()`'s x and y specific force, about 1e-16 at rest. They are rounding
      residues, one with its sign flipped, consistent with different math libraries.
    - The joint angles first differ by more than 1e-7 at startup step 97, consistent with float32 kernels compiled
      for x86 rather than ARM.
    - Walking amplifies the difference, through contacts and the RL policy. The policy runs in ONNX Runtime, which
      uses different kernels on each architecture.
  - **Garbage collection** (port review round 1, N4). In this replay mode (`none`, without `gc.freeze`):
    - the 5070ti ran one automatic generation-2 collection of 241.6 ms inside the loop, the Mac none;
    - there were 234 and 21 generation-0 and generation-1 collections here, against 174 and 16 on the Mac.

    v33's worker collects and freezes its heap every 50 steps, v32's change, and the trial uses that.
  - **Speed:** the replay loop took 36.7 s against the Mac's 31.7 s, so CPU physics is about 16% slower here.
- **P4, as pre-registered, is vacuous.** No step has an identical input history, because the first input already
  differs by 3e-16. The script's `passed: true` is therefore empty and is not counted. Descriptively:
  - the controller's replies equal the Mac's for the first 7,502 of 11,020 steps (to 7.5 s, the start of the
    preparation phase);
  - they are identical at all 56 steps whose inputs are identical;
  - the phase times are identical;
  - attempts 02 and 03 gave identical records on the 5070ti.
- **P4b, added after that: passed** (`checks/p4b_request_replay.py`).
  - **The test:** the Mac's 11,020 recorded requests, fed open-loop and in order to the emulated controller.
  - **Result:** every reply's motor block, phase and zero flag equals the Mac's recorded reply.
    - Attempt 01 (`p4b/attempt01.json`) compared values.
    - Attempt 02 (`p4b/attempt02.json`) compared the motor block's raw 64-bit patterns, so a sign-of-zero difference
      would also count. It also had 0 mismatches, so the replies are bit-identical (port review round 1, N9).
  - **What it shows:** the emulated library computes exactly what it computed natively. The divergence in P5
    comes from floating-point arithmetic, not from the controller.
  - **Speed:** compile and ready in 8.7 s (limit 45 s), then 0.135 ms per step.
- **P6 attempt 01 failed before physics** (`runs/port5070_v33_flat01/`, kept):
  - **The error:** the launcher's native-build check (`run_local_episode.py:152-155`) hashes all 515 files of the
    build's `install_sha256.json`, including 17 `.pyc` files in `__pycache__`, which the copy list excluded.
  - **Why P1 missed it:** P1 had checked only `source_sha256.json`.
  - **The fix:** the build directory was copied complete (18 files added). P1 now checks both manifests and the
    launcher's 10 GiB free-disk rule, and it passes: 97 source files, 515 install files and 50 GiB free.
  - **The runner:** `checks/p6_flat_run.sh <attempt>` now numbers its run IDs, which are never reused.
- **P6 attempt 02 passed** (`runs/port5070_v33_flat02/`, copied back; all 388 files verified by SHA-256):
  - **Pre-registered criteria:**
    - no infrastructure failure: the wrapper exited 0 after 94.6 s, the state copy-back was verified, the
      container cleanup exited 0, and no container was left;
    - the factory startup completed;
    - the robot walked under SCAN's commands, with 1,094 nonzero command steps of 1,398.
  - **Reported, not judged:**
    - the run's version gate recorded v33;
    - the robot walked from x = −0.10 m to x = 11.83 m on the empty floor and ended on `arrived_hold`, with
      terminal result `arrived_after_quiescence`;
    - 39.0 s of physics in 89.7 s of worker wall time, about 0.43× real time. That rate is not comparable with the
      Mac's building runs on another scene. The controlled comparison is P5: CPU physics about 16% slower here
      (round 1, N2);
    - the gate ran on simulation time (`odom_time_base` `simulation`), with a largest simulation age of 5 ms;
    - the largest wall gap between body-pose callbacks was 21 ms;
    - the telemetry link had no reconnect, protocol error or I/O error;
    - the only stop flow was `arrived_hold`.
  - **What this implies for v33's trial here:** on this host, with the container native and nothing else
    running, no pose gap came near 0.25 s. If the historical route behaves the same, the pre-registered exposure
    rule will find no exposed gap, and the trial will then say nothing about the gate's tolerance of stalls. It
    would still show how far v33 gets on the full route without a host-induced stop.

## Summary of the validation

P1, P2, P3, P4b, P5 (no fall) and P6 pass. P4 as pre-registered was vacuous, and P4b replaced it with a strict
test. Four problems were found and fixed without changing any pinned file:
- files missing from the copy (`lite3_reference`, `stance_hold.py`, the build's `__pycache__`);
- the Python 3.12 pyzmq backend;
- podman's user namespace (`--userns=keep-id`);
- the kernel cache: modules generated at run time compile only in a real run, so one must precede a trial.

Physics on this host is numerically different from the Mac's: the same commands give trajectories 0.63 m apart
about 17.6 s after the first walking command.

## Independent review

- **Round 1** (`port_review_round1.json`) failed, with four blocking findings and twelve non-blocking ones.
  `REVIEW_RESPONSE_round1.md` answers each.
- **Round 2** (`port_review_round2.json`) failed, with two new blocking findings and eight non-blocking ones.
  `REVIEW_RESPONSE_round2.md` answers each.
  - **B5:** the runner's manifest could not verify its own log.
  - **B6:** the new command-line records captured part of a tunnel token that a root process on this host carries
    on its command line. The fragments in the first dry run's files were redacted in place on both hosts, so those
    files no longer match that dry run's own manifest. Dr Sun was told.
- **Round 3** (`port_review_round3.json`) failed, with one new blocking finding and six non-blocking ones.
  `REVIEW_RESPONSE_round3.md` answers each.
  - **B7:** the documented abort, stopping `run_bounded` alone, would have left the episode running.
  - **The fix:** SIGTERM to the runner is forwarded to the episode's process group, and the runner waits for
    `run_bounded` to record the exit. Tested with a stand-in that has `run_bounded`'s process structure.
- **Round 4** (`port_review_round4.json`) passed, with no blocking findings and four non-blocking ones.
  `REVIEW_RESPONSE_round4.md` answers each.
  - **N27:** after an abort, `run_bounded`'s final print would have overwritten the abort's lines in the runner log.
    The log is now opened in append mode.
  - **N28–N30:** the abort handler looks for the episode for up to 10 s and bounds each wait; the lock's
    descriptor is closed for the runner's podman calls; and the host note says to signal the runner's pid and what
    an abort leaves.
  - **Tested** in dry runs with a stand-in that prints `run_bounded`'s record. A control with the old log mode
    reproduced N27.
  - Because these changes touch the runner after a passing round, a fifth, confirmation round reviewed them.
- **Round 5** (`port_review_round5.json`) passed, with no blocking findings and two non-blocking ones.
  `REVIEW_RESPONSE_round5.md` answers both.
  - **N31:** if `run_bounded` itself ends while the episode runs, the runner cannot see the episode, and its
    post-run step would remove the main container under the live worker. The note forbids the two operator routes
    to this; an unexpected death of `run_bounded` remains. It is documented as a residual risk, and the runner is
    unchanged.
  - **N32:** wording in the host note and this file.

## Use: v33's trial

- **The run:** `v33_historical_full01` ran on this host at 20:51Z with the reviewed runner (sha256 `2649f0e8…`).
  - There was no refusal, no abort and no retry, and no container was left.
  - The runner's manifest listed 4,597 files and passed its own check. The MacBook's copy verifies against it,
    file for file.
  - Results: `versions/v33/RESULTS.md`.
- **The reviews ran on the execution copy.** The run records the native build's path on this host, which the
  local review re-hashes. The copy needed a `validation/` directory for their outputs; the outputs are identical on
  both hosts.
- **Kept on this host:** the execution copy keeps the run, and the private bytes stay listed in
  `LOCAL_ONLY_BYTES.json`. Removing them is Dr Sun's decision.
- **Local-only bytes of the port's own runs:** `LOCAL_ONLY_RUN_BYTES.json`, written by `local_only_inventory.py`.

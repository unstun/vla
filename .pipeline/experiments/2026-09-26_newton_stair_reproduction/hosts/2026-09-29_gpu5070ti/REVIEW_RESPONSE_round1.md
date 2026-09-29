# Response to the port's independent review, round 1 (`port_review_round1.json`, failed)

Round 1 found four blocking and twelve non-blocking problems. Each was checked against the logs and files before
anything changed. Nothing pinned changed; no physics ran for these fixes.

## Blocking

- **B1, the wrong module named as P5 attempt 02's cause.** Confirmed.
  - **What the logs show:** warm-up run 4 had compiled `geometric_lidar fd8ffc5` (`checks/warm_kernels_run4.log`
    line 104), and the cache listing taken before P5 holds it. In attempt 02, 27 modules generated at run time
    compiled lazily. 26 compiled during the factory startup. At the first scan, Newton's ray-intersection closure
    (`intersect_ray…962a4840`, hash `14d5500`) compiled on the scanner thread in 1,128 ms.
  - **Changed in PORT.md:** the cause, the statement that `force_load` compiled "every module", and the summary.
  - **Recorded:** the post-P5 comparison it had promised. The Mac's v29–v32 historical trials loaded 49 modules.
    P5 attempt 03 and P6 on the 5070ti loaded exactly those, with the same names and hashes, and compiled none.
  - **Also corrected:** the same error in the hot zone and in the session memory.
- **B2, "every file copied back" was false.** Confirmed.
  - **Copied back:** all nine log files from `~/vla_exec/logs` and `p1_scratch`, into `remote_logs/`, verified
    against the host's SHA-256 list (`SHA256SUMS_remote.txt`).
  - **Re-run with saved outputs** (`checks/record_host_checks.sh`, attempts 01 and 02): P1, the network test and
    the user-namespace test, into `checks_out/`. P1 now also covers the native build's `install_sha256.json` and the
    free-disk rule.
  - **Unrecordable:** the "Exec format error" observed before emulation was installed cannot be repeated now.
    PORT.md says so.
- **B3, the quiet-host row claimed more than the runner checked, and dropped Dr Sun's confirmation.** Confirmed. A
  `machine-dog-nav` blackbox recorder (`recorder.py`, `follow.py`) runs on the host.
  - **New refusals in the runner:** a podman failure, this user's running containers, a `qemu-aarch64` entry that
    is not `enabled`, a 1-minute load average above 1.0, and GPU compute processes.
  - **Refusals consume nothing:** each is appended to `_refusals.txt`, so the runner can be started again.
  - **Pre-run snapshot:** saved to `versions/v33/host/`.
  - **Restored:** the note again requires Dr Sun's confirmation before the run, now that no other session uses the
    host. The blackbox recorder is his call.
  - **Tested:** a copy with a stand-in launcher, writing to a scratch directory, checked the mechanics
    (`checks/runner_dry.sh`, `checks_out/runner_dry_attempt01/`).
- **B4, the Linux sampler's CPU ranking used lifetime averages.** Confirmed from the procps manual on the host
  ("cputime/realtime ratio").
  - **Rewritten:** per-process CPU over each one-second interval from `/proc/<pid>/stat` deltas, plus each CPU's
    busy fraction from `/proc/stat` and CPU, memory and I/O pressure from `/proc/pressure/*`.
  - **Documented:** every difference from the macOS sampler, in its docstring and in the host note.
  - **Dry-run to a scratch path:** it caught a 2 s single-core burst at 81.7% and 99.7%.

## Non-blocking

- **N1, units and wording.** Corrected in PORT.md:
  - **The 9.1e-6 figure** is the base x position in m; joint angles differ by at most 1.5e-6 rad after the
    startup.
  - **The first differing inputs** are `gyro()`'s x and y specific force, rounding residues near zero.
  - **The walking time** is about 17.6 s after the first walking command.
  - **Also:** the stale "pending" entry and the `--user` uid are corrected.
- **N2.** The rate comparison with the Mac's building runs is replaced by the controlled P5 comparison.
- **N3.** `checks_out/execution_copy_manifest.txt` lists the execution copy's 9,509 files with SHA-256s. PORT.md
  names the later additions and the missing `source/` snapshot.
- **N4.**
  - **(a) The garbage collection:** P5's no-freeze mode ran one automatic generation-2 collection of 241.6 ms here.
    It is recorded in PORT.md; the trial's worker collects and freezes its heap.
  - **(b)–(d) Record inaccuracies:** `ru_maxrss` in KiB, the Mac venv path in `input_identity.json`, and the Docker
    form in `container_command.json`. They are listed in the host note.
  - **The shim's log:** the shim now logs its translations when `VLA_SHIM_LOG` is set (`checks_out/shim_log_attempt02.txt`),
    and the runner sets it.
- **N5.** Added to the host note's claim boundary:
  - the shared clock (27 µs offset and 54 µs round trip, against 155,507 s and 598 µs for v32);
  - the navigation stack running natively on AVX-512;
  - which bound ends the run depending on host speed.
- **N6, running and recovering the trial.** The runner now:
  - writes its own log and is started detached (`setsid nohup`);
  - checks the sampler at start and at the end;
  - records containers after the launcher returns;
  - recovers a killed launcher's tmpfs state before removing its container;
  - writes a SHA-256 manifest before copy-back.
- **N7.** Put to Dr Sun as a decision: spend v33's single trial here, keep it for a host that stalls, or
  pre-register a separate trial for this host.
- **N8.** A rule for infrastructure failures before and after physics starts, following v26's precedent
  (`historical_full01` failed to launch, `historical_full02` was the trial). It applies only if Dr Sun approves it.
- **N9.** P4b attempt 02 compared raw 64-bit patterns and found 0 mismatches, so "bit-identical" now holds as stated.
- **N10.** `setup/LOCAL_ONLY_BYTES.json` is untracked and has a mixed schema, so it is left as is. The two new
  local-only files, the cp312 module and its wheel, are recorded in this directory's `LOCAL_ONLY_BYTES.json`.
- **N11.** The runner now checks podman's exit status separately and requires the binfmt entry to read `enabled`.
- **N12.** `LOCAL_ONLY_BYTES.json` records the private bytes on the 5070ti:
  - the snapshot copy: 68 files, 253,890,132 bytes;
  - the arm64 image archive, with its SHA-256;
  - the podman image.

  Their removal is to be proposed to Dr Sun after the trial, and done only with his approval.

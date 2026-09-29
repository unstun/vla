# v33 trial on gpu5070ti: host note

Written after the freeze and before any v33 trial physics. Revised after the port's review rounds 1 (B3, B4, N4–N8),
2 (B5, B6, N13–N18), 3 (B7, N21–N25), 4 (N27–N30) and 5 (N31, N32), still before any v33 trial physics. It is not
part of v33's manifest and changes no pinned file. It amends `PHYSICAL_RUN_PLAN.md` only where the host matters;
everything else there applies unchanged.

## Why the host changed, and Dr Sun's decisions

- **Dr Sun, 2026-09-29:** "u can process on gpu 5070ti", then "u can use newton too on 5070ti".
  - Asked where the trial should run, he chose to port the pipeline first and validate it on the 5070ti.
  - The pre-registered plan instead ran the trial on the MacBook, with the other Claude session's `machine-dog`
    activity paused.
- **The port and its validation:** `hosts/2026-09-29_gpu5070ti/PORT.md`. P1, P2, P3, P4b, P5 and P6 passed, and P4
  as pre-registered was vacuous. Nothing pinned changed.
- **Dr Sun's decisions, 2026-09-29, after P6 and before the trial:**
  1. **Where the trial runs:** on the 5070ti, as planned, although stalls may not occur there. The alternatives
     were the MacBook with the other session active, or skipping to v34. Put to him as round 1's N7.
  2. **Host use:** nobody else uses the 5070ti during the run, and the blackbox recorder may keep running.
  3. **Infrastructure failures:** the rule below applies.

## What changes for the trial

| `PHYSICAL_RUN_PLAN.md` | On gpu5070ti |
|---|---|
| Local simulation only: no robot, no remote host, no training | The simulation runs on gpu5070ti, Dr Sun's machine, as an execution copy of this repository. Still no robot and no training |
| The run through `scripts/run_bounded.py` with the listed flags | The same command and flags, unchanged, on the execution copy: `hosts/2026-09-29_gpu5070ti/v33_trial_run.sh v33_historical_full01`. It is started detached, with the absolute path given in its header, so no ssh or agent session can end it. The `docker` shim is first on PATH and logs its translations, and the worker uses the Linux environment (the same 105 packages and versions as the Mac's) |
| Gates before physics | Unchanged, and executed on the execution copy: the v33 manifest, the 99 records, the native build's two manifests and the scene inputs (P1 checked each there) |
| Quiet host: Dr Sun pauses the other session's `machine-dog` activity, and the run starts only after he confirms | Dr Sun confirmed that nobody else uses the 5070ti during the run. The MacBook's load does not reach this host, so no MacBook session is paused. The runner refuses to start if podman fails, if a container of this user runs, if `qemu-aarch64` is not enabled, if the 1-minute load average is above 1.0 (idle reads about 0.1–0.4), if a GPU compute process runs, or if a port from 46200 to 46203 is in use. It cannot see other users' or rootful containers except in the process list. It records a pre-run snapshot (`versions/v33/host/<run ID>_prerun.txt`): uptime, users, login sessions, processes by CPU over one second, all processes, containers, images, `nvidia-smi`, disk, memory, pressure, emulation and tool hashes |
| `host_sampler.py` records the host once a second | `hosts/2026-09-29_gpu5070ti/host_sampler_linux.py`, to the pre-registered path for `v33_historical_full01` (`versions/v33/host/v33_historical_full01_host.jsonl`). A retry under the rule below writes `<run ID>_host.jsonl`. Its record differs from the macOS sampler's; see below |
| The analysis | Unchanged. The runner writes a SHA-256 manifest of the run directory and the host files on the 5070ti, after its log's last line (`<run ID>_SHA256SUMS.txt`, self-checked). The copy on the MacBook is verified against it before any analysis. Analysis and videos then run on the MacBook under the rules in "How the analysis writes its outputs" |
| (no step) | After the launcher returns, the runner records the containers (`<run ID>_postrun.txt`). The launcher's own cleanup does not run if the 1800 s deadline killed it. If its container still exists then, the runner copies its tmpfs state into `runs/<run ID>/recovered_external_episode.tar`, stops and removes it, and records each step. Usually nothing remains: the signal reaches the container through podman and `--rm` removes it, as with Docker Desktop. A recovered archive is verified in the analysis the way `run_local_episode.py`'s `return_linux_state` does, against the last acknowledged SHA-256 in `applied_sent.jsonl` |

## During the run

- **Monitoring stays light:** only the tail of the runner log and a check for `process.json`. No hashing, `find` or
  `podman stats` runs over the host during the run.
- **To abort** (corrected after round 3, B7, and hardened after round 4, N28): send SIGTERM to the runner's pid, the
  first line of its log (`kill -TERM <pid>`).
  - **Not to its process group:** the runner, the sampler and `run_bounded` share it. A group signal would also stop
    `run_bounded`, which has no handler, and the episode would keep running. The runner would then take the trial
    for finished, and its post-run step would remove the main container under the live worker (round 4, N28;
    round 5, N32).
  - **What the runner does:**
    - It forwards SIGTERM to the episode's process group, as `run_bounded`'s own deadline does. Just after the
      launch, before the episode exists, it looks for it for up to 10 s.
    - It waits for `run_bounded` to record the exit. After 60 s it sends SIGKILL to the episode's group, and after
      60 s more to `run_bounded` itself.
    - It then finishes as usual.
  - Do not stop `scripts/run_bounded.py` alone: it has no signal handler, and the episode it started in its own
    session would keep running, with the same consequence.
  - **A residual risk, not guarded** (round 5, N31): if `run_bounded` dies by itself while the episode runs, for
    example after a crash or an out-of-memory kill, the same happens. The runner finds the episode only as
    `run_bounded`'s child, so it cannot see it. The runner was not changed for this: `run_bounded` only waits on
    its child, and nobody else uses the host. If it happens, the post-run record shows the container recovered and
    removed while `run_bounded`'s `process.json` is missing, and the run is the outcome under the rule below, with
    that cause.
  - Only SIGTERM reaches the runner. Started with `nohup` in the background, it ignores SIGHUP, SIGINT and SIGQUIT
    (round 3, N21).
  - **Before the handler exists:** the runner sets its handler just before the pre-run snapshot. Until then, SIGTERM
    ends it at once: during the start checks, and after it has opened its log, which then already exists, so the run
    ID cannot be reused. Nothing has started by then, so under the rule below this is a failure before physics, and
    a retry takes the next run ID (round 4, N28; round 5, N32).
  - **What an abort leaves** (round 4, N30): like the 1800 s deadline, an abort kills the episode's processes before
    they clean up. The worker's `finally` block does not run, so `startup_events.json`, `stance_status.json`,
    `video_states.json` and `sensor_manifest.json` are missing. `result.json` is missing too, unless the episode had
    already written it. The analysis must expect this.
  - **Tested in dry runs** with stand-ins that have `run_bounded`'s process structure:
    - round 3 (`checks_out/runner_dry3_tests_attempt01.txt`): aborting through the runner and through the episode's
      group;
    - round 4 (`checks_out/runner_dry4_tests_attempt01.txt`): the abort record surviving `run_bounded`'s final
      print, an abort just after the launch, and the SIGKILL escalation.
- **One runner at a time:** a lock (`versions/v33/host/v33_trial.lock`) refuses a second runner while one runs, and
  was tested (round 3, N24).
- **Login sessions:** linger is off for the user. The containers therefore depend on a login session staying open,
  and the desktop session stays logged in. The snapshot records both.

## The Linux host sampler's record

- **Per-process CPU:** each process's use over each one-second interval, from `/proc/<pid>/stat`.
  - The macOS sampler takes `ps`'s %CPU, a decaying average over up to a minute.
  - Linux `ps` reports CPU time over the process's whole life, which hides a burst from a long-running process, so
    it is not used.
- **Process names:** `comm` is the kernel's 15-character name, where macOS `ps` gives the executable path.
- **Command lines** (round 2, B6):
  - Recorded only for processes of the invoking user, and redacted. Other users' processes get none; on this host a
    root process carried a tunnel token on its command line.
  - **What redaction removes:** the value after any flag whose name contains token, passw, secret, key, credential
    or auth, and any run of 32 or more base64-like characters mixing upper case, lower case and digits.
  - **The runner's process table** uses the same code (`host_sampler_linux.py --processes`). Its `top` section runs
    without any user configuration, so it shows process names only.
  - **What protects other users** is the ownership test, made on the opened `/proc/<pid>/cmdline` so a reused pid
    cannot pass it, not redaction (round 3, N23).
  - **Redaction for the invoking user's own processes is best effort.** It also covers `scheme://user:password@`
    credentials and quoted flag values. A flag without one of the keywords, or a token shorter than 32 characters,
    is not caught (`checks_out/redaction_test_attempt01.txt`).
- **Added, with no macOS counterpart:** each CPU's busy fraction over the interval, and CPU, memory and I/O pressure
  (PSI).
- **Paging counters:** from `/proc/vmstat` and `/proc/meminfo`.
- **Git processes:** matched by the basename `git` of the first argument, where the macOS sampler required a path
  ending in `/git`.
- **Tested:** dry runs to scratch paths. One caught a 2 s single-core burst at 81.7% and 99.7%
  (`checks_out/host_sampler_dryrun_attempt01.jsonl`). The runner's dry runs recorded no other user's command line
  (`checks_out/runner_dry2/`).

## Running processes that are not stopped

- **Recorded in the snapshot and by the sampler, not stopped, as Dr Sun decided:**
  - the `machine-dog-nav` blackbox recorder (`recorder.py` and `follow.py`, running since boot);
  - clash-verge, whose WebKitWebProcess uses 2–5% of a CPU per interval and is the busiest idle process;
  - verge-mihomo, cloudflared, frpc and `x11vnc`;
  - the desktop session.

## Infrastructure failures (approved by Dr Sun, 2026-09-29)

- **Before the first physics step:** for example a refusal, a gate failure, or a container or emulation failure at
  start. This is not an outcome. It is recorded with its cause, and the trial runs under the next run ID
  (`v33_historical_full02`, and so on). This follows v26, whose `historical_full01` failed to launch before physics
  and whose `historical_full02` was the trial.
  - **The evidence that physics began:** `runs/<run ID>/factory_full_rate.npz` exists with at least one record. The
    startup's `finally` block writes the file even when it is empty.
  - **The runner:** it takes the run ID as an argument, limited to `v33_historical_full01` to `09`. Each run writes
    host files named for its ID.
- **After physics starts:** the run is the outcome, whatever ends it. An infrastructure cause is recorded as the
  cause, and a second run needs Dr Sun's decision.

## Known inaccuracies in the run's own records

In the manner of `PHYSICAL_RUN_PLAN.md`'s note on `episode_request.json`:
- **Memory figures:** `process.json`'s `child_peak_rss_bytes` comes from `ru_maxrss`, which Linux reports in KiB,
  not bytes.
- **Worker environment:** `input_identity.json`'s `newton_environment` names the Mac's virtual environment, from the
  pinned `setup/source_identity.json`. The run uses `~/vla_exec/envs/newton_worker` (PORT.md, P2).
- **Container command:** `container_command.json` keeps the Docker form. The podman arguments actually used are in
  the shim's log (`versions/v33/host/<run ID>_docker_calls.txt`).

## Claim boundary added by the host

- **Different numerics:** physics on gpu5070ti is numerically different from the MacBook's (PORT.md, P5). The same
  recorded commands leave the robots 0.63 m apart about 17.6 s after the first walking command. Comparisons with
  v32's MacBook trial are therefore qualitative, such as where the robot stops and how the run ends.
- **Native navigation stack:** the SCAN/backend container runs natively here, on an AVX-512 CPU, instead of under
  emulation. SCAN, PCT and the container's numpy/OpenBLAS may therefore produce different floating-point results
  too.
- **Timing:** CPU physics was about 16% slower in P5. Which bound ends the run depends on host speed: the 600 s
  physics limit, the 1500 s goal budget or the 1800 s deadline. Timing results describe this host only.
- **Clock:** the container shares the host's clock. In P6 the clock offset was 27 µs with a 54 µs round trip. For
  v32 on the MacBook, whose Docker VM has its own clock, they were 155,507 s and 598 µs. Clock-sync rejections, TTL
  windows and any `applied_evidence_stale` from a sync outage are therefore not comparable with v32.
- **Exposure may be empty:** on the empty floor (P6), no pose gap exceeded 21 ms. If the historical route behaves
  the same, the pre-registered exposure rule will find no exposed gap. The run then says nothing about the gate's
  tolerance of stalls, whatever its outcome, as `PHYSICAL_RUN_PLAN.md` already states.
- **No MacBook result is replaced or reproduced** by this run.

# Response to the port's independent review, round 4 (`port_review_round4.json`, passed)

Round 4 passed. It had no blocking findings, it confirmed that B7 and N21–N25 were closed, and it found four
non-blocking problems. One of them, N27, was worth fixing before the run, since an abort's record cannot be redone.
Each finding was checked before anything changed. No physics ran.

## Non-blocking

- **N27, an abort's lines would be lost from the runner log.** Confirmed.
  - **The cause:** the runner opened its log without append mode. `run_bounded` inherits that descriptor, and when
    the episode ends it prints its record, about 2 KB of JSON (`2026-09-26_newton_macos_policy/scripts/
    run_bounded.py:63`). That print lands at the descriptor's old offset, over the lines the abort handler had
    appended.
  - **The fix:** the runner opens its log in append mode, so every inherited copy writes at the end. The log cannot
    exist beforehand, since the runner refuses to start if it does.
  - **Tested** (`checks/runner_dry4_tests.sh`, `checks_out/runner_dry4_tests_attempt01.txt`, `checks_out/runner_dry4/`).
    - A new stand-in (`checks/standin_run_bounded2.py`) prints a record of the same size, as `run_bounded` does.
    - With the fix, an abort kept both abort lines, with the whole record after them.
    - **The control:** the same abort with the old log mode (`checks/runner_dry4_oldlog.sh`) kept neither line,
      which reproduces the finding.
- **N28, edge cases in the abort handler.** All five were checked: (b)–(d) changed the handler, and (a) and (e)
  changed the documentation.
  - **(a)** SIGTERM before the handler exists, during the start checks, ends the runner at once. The host note now
    says that this counts as a failure before physics.
  - **(b)** The handler now looks for the episode for up to 10 s while `run_bounded` runs.
    - **Tested:** the runner was aborted 0.58 s after the launch while the stand-in held back its episode for 3 s.
      It found the episode when it started and stopped it.
  - **(c)** When the launcher has already returned, the handler takes its status with `wait`.
    - **Why that works:** bash 5.2.21 on this host returns a remembered status again (`checks/wait_test.sh`,
      `checks_out/wait_test_attempt01.txt`). A second `wait` returned 3 and 5, and a `wait` inside a TERM handler,
      after the main `wait` had returned, gave 7.
    - **Not tested:** the window cannot be hit on purpose, so the dry tests do not exercise this branch.
  - **(d)** Every wait after a signal now has a bound. After 60 s the handler sends SIGKILL to the episode's group,
    and after 60 s more to `run_bounded` itself.
    - **Tested** with 5 s in place of 60 s, using an episode that ignores SIGTERM and a stand-in that hangs after its
      episode ends. Both escalations ran, the launcher returned 137, and no process was left.
  - **(e)** The runner's header and the host note now say to signal the runner's pid, not its process group, and
    why.
- **N29, the lock's descriptor.**
  - **The fix:** the runner's own podman calls now run with it closed, through a shell function. `run_bounded` and
    the sampler keep it.
  - **Tested** with a recording `podman` first on PATH (`checks/fd_recording_podman.sh`).
    - None of the runner's 36 podman calls in the dry tests had descriptor 9.
    - The 6 calls through the shim, which stand in for the episode's own calls, had none either. As Python's
      `subprocess` does for the episode, the dry copy closes it for them.
    - **The positive control:** a call made with the descriptor open had it.
    - While a runner ran, only the runner, the sampler and the stand-in held the lock.
- **N30.** Confirmed in `scripts/newton_episode.py:341-353`. The host note's abort bullet now says what an abort
  leaves:
  - the worker's `finally` block does not run, so `startup_events.json`, `stance_status.json`, `video_states.json`
    and `sensor_manifest.json` are missing;
  - `result.json` is missing too, unless the episode had already written it;
  - `startup_events.json` is added to the reviewer's list, because it is written in the same block.

## Other results of the dry tests

- **The normal run and the lock** behaved as in round 3.
  - All six manifests self-checked on the host, and they verify locally, 6 files each.
  - A second runner was refused while one ran.
- **Credential check, counts only.** The round-2 checker counted 3 lines in `checks_out/runner_dry4/`, and all 3
  are false positives.
  - Each is a sampler line that names `cloudflared` as a process and also holds a long run from the invoking user's
    own command lines.
  - That run is either part of the dry runs' script path or a `/home/sun` path of the `machine-dog-nav` recorder.
  - This was checked by comparing booleans, without printing the text. No other user's process has a command line.
- **Stopped containers from other work.** `podman ps -a` lists five containers from `machine-dog-nav` and SCAN work.
  Four exited six weeks ago, and one was created but never started.
  - The runner refuses to start only when containers are running.
  - Its cleanup touches only the run's own container and `vla-factory-algorithm-*`, so these are left alone.
  - The pre-run snapshot records them.

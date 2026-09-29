# Response to the port's independent review, round 3 (`port_review_round3.json`, failed)

Round 3 confirmed that B5, B6 and N13–N19 were closed, and found one new blocking problem and six non-blocking
ones. Each was checked before anything changed. No physics ran.

## Blocking

- **B7, the documented abort would not stop the trial.** Confirmed against `run_bounded.py`: it starts the episode in
  a new session, signals that session only on its own deadline, and has no signal handler.
  - **What stopping it alone would do:** the episode keeps running. The runner's `wait` then returns, and its normal
    post-run step would remove the main container under a live worker.
  - **The fix:** SIGTERM to the runner is the abort.
    - The runner finds `run_bounded`'s child, the episode's session leader, and sends SIGTERM to its process group,
      as `run_bounded`'s own deadline does.
    - It waits up to 60 s for `run_bounded` to record the exit, then sends SIGKILL to the group if needed, and then
      takes the normal post-run path.
  - **Corrected:** the runner's header and the host note, which warns against stopping `run_bounded` alone.
  - **Tested** (`checks/runner_dry3.sh`, `checks/runner_dry3_tests.sh`, `checks_out/runner_dry3_tests_attempt01.txt`,
    `checks_out/runner_dry3/`). The stand-in launcher has `run_bounded`'s process structure: the episode runs in a new
    session, with no handler.
    - **Abort through the runner:** the episode's group received SIGTERM (exit −15), the stand-in recorded it, and
      the runner finished as "aborted".
    - **Abort through the episode's group directly:** the stand-in returned, and the runner finished normally.
    - **Both:** the manifest self-check passed, and no episode process was left.

## Non-blocking

- **N21.** The runner's header and the host note now say that only SIGTERM reaches the runner, which ignores
  SIGHUP, SIGINT and SIGQUIT under `nohup` in the background. The trap handles SIGTERM only.
- **N22.** Largely resolved by B7's fix: a runner-only SIGTERM now ends the episode before the manifest is computed.
  Both `abort` and `finish` send their output back to the runner log first, so a SIGTERM during the snapshot is
  logged in the right place.
- **N23.** Hardened, and the limits are stated.
  - **Ownership:** the test is made on the opened `/proc/<pid>/cmdline` with `fstat`, which closes the pid-reuse
    window.
  - **Redaction:** it also covers `scheme://user:password@` credentials and quoted flag values.
  - **`top`:** it runs with no user configuration, so a saved `toprc` cannot turn on command lines.
  - **The synthetic test and its output are saved** (`checks/redaction_test.py`,
    `checks_out/redaction_test_attempt01.txt`). Seven cases are redacted, two are kept unchanged, and two known misses
    are listed: a keyword-less flag and a short token.
  - **Stated in the host note:** other users are protected by the ownership test; redaction of one's own processes
    is best effort.
- **N24.** A `flock` on `versions/v33/host/v33_trial.lock`, taken before the checks, stops a second runner. The
  manifest does not select the lock file. Tested: a second runner started while one ran was refused.
- **N25.**
  - **The round-1 dry-run snapshot:** its other-user rows were reduced to process names on all three copies (317
    rows each).
  - **Stray bytecode:** the `__pycache__/host_sampler_linux.cpython-312.pyc` came from the author's round-2 synthetic
    test, which imported the sampler. It was removed on both hosts, and the new test does not write bytecode.
  - **The synthetic test:** it is now saved with its output (N23).
- **N26.** The reviewer's round-2 session transcript displayed part of the tunnel token. This is reported to Dr Sun
  for his decision on rotating it. No report and no repository file contains it: count-only scans find no token in
  the port files, and the only remaining checker hit is the kernel thread name `nvidia-modeset/kthread_q`.

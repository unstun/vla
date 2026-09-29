# Response to the port's independent review, round 2 (`port_review_round2.json`, failed)

Round 2 confirmed that every round-1 finding was closed, and found two new blocking problems and eight
non-blocking ones in the rewrites. Each was checked before anything changed. No physics ran.

## Blocking

- **B5, the manifest could not verify the runner's own log.** Confirmed from the first dry run: its manifest listed
  the runner log at a hash the saved file no longer has.
  - **The fix:** the runner writes its last log line ("runner finished"), then sends its output to a separate
    `_manifest.log`, then computes the manifest. The manifest excludes itself and `_manifest.log`, and is checked
    with `sha256sum -c`.
  - **Tested** (`checks/runner_dry2.sh`, `checks_out/runner_dry2/`): the normal path and the signal path both
    reported "manifest self-check passed".
- **B6, a credential reached disk.** Confirmed without printing it. A root process on the 5070ti, `cloudflared`,
  carries its tunnel token on its command line, and the first dry run's snapshot and sampler recorded part of it.
  - **Found in:** two files here, and four on the 5070ti (the execution copy's `checks_out/` and
    `~/vla_exec/port/runner_dry/`).
  - **Redacted in place:** all six, keeping the JSON valid. Every port file on both hosts was then checked, and no
    unredacted token flag or long base64 run on a `cloudflared` line remains.
  - **Consequence:** those files no longer match that dry run's own manifest.
  - **The writers now:** the sampler records a command line only for processes of the invoking user, after
    redaction; other users' processes get none. The runner's process table uses the same code
    (`host_sampler_linux.py --processes`) and shows only the name for other users' processes. Redaction replaces the
    value after any flag whose name contains token, passw, secret, key, credential or auth, and any run of 32 or more
    base64-like characters mixing upper case, lower case and digits.
  - **Tested:** on synthetic strings, redaction caught four flag and base64 cases and left paths and hex digests
    unchanged. In the second dry run, none of 13 other-user entries carried a command line, and `cloudflared`
    appears only by name. The one line the checker still flags names the kernel thread `nvidia-modeset/kthread_q`,
    a false positive of the checker's own rule.
  - **Not redacted, and reported to Dr Sun:**
    - the reviewer's session transcript under `~/.claude` probably holds the fragment;
    - this repository sits under a synced folder (`tongbu`), which may have copied the files before redaction.

    Whether to rotate the token is his decision.

## Non-blocking

- **N13.** The host note now says the runner recovers the container "if it still exists", and that usually nothing
  remains: the signal reaches the container and `--rm` removes it. A recovered archive is verified in the analysis,
  as `return_linux_state` does.
- **N14.** Dr Sun approved the infrastructure-failure rule.
  - **Run ID:** the runner takes it as an argument, limited to `v33_historical_full01` to `09`, and each run writes
    host files under its own ID.
  - **Evidence that physics began:** `runs/<run ID>/factory_full_rate.npz` with at least one record.
- **N15.** Signals are trapped:
  - the launcher runs in the background under `wait`, so a trapped signal is handled promptly;
  - on a signal, the runner stops the sampler and records the containers without touching them.

  Also: a listener on ports 46200–46203 refuses the start, the start line uses the absolute path, and the host note
  keeps monitoring light and says how to abort.
- **N16.** The snapshot records `loginctl show-user` and `list-sessions`. The host note says linger is off and the
  desktop session stays logged in; linger was not changed.
- **N17.** Joint angles differ by at most 1.5e-6 rad at the first replay step and 2.7e-6 rad over the standing steps
  1–66. Recomputed; PORT.md updated.
- **N18.** clash-verge's WebKitWebProcess (2–5% per interval), verge-mihomo, cloudflared and frpc are added to the
  processes left running.
- **N19.** The execution-copy manifest was regenerated after these fixes, with its time in its first line.
- **N20.** Noted. The reviewer created and removed one `__pycache__` file locally; nothing else was affected.

## Dr Sun's decisions, recorded in the host note

After P6 and before the trial:
- the trial runs on the 5070ti, as planned;
- nobody else uses the host during the run, and the blackbox recorder may keep running;
- the infrastructure-failure rule applies.

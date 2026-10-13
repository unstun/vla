# Reproduction and retained evidence

Local source of truth: this audit directory. Original complete runs stay at
`gpu5070ti:/data/sun/vla_mppi_20261009/trials/v177_full_candidate_attemptNN/`.
The frozen v177 results contain full raw inventories. Capture reads verify ZIP
members; this audit returns raw-file hashes, event indices and bounded contexts.

1. In the existing remote `newton_worker` Python environment, run
   `inspect_stops.py --output NEW_DIRECTORY`, then
   `inspect_windows.py --first FIRST_DIRECTORY --output NEW_DIRECTORY`.
   Both require a fresh output directory. No physics is started.
2. `audit_drift.py` reads full run01telemetry and the exact cancellation-to-next-
   nonzero interval. It writes `results/v177_stop_drift_detailed.json` remotely.
   The local returned file SHA is
   `41f6cf9bbcc0a202b7cd0a267d979bd9637b5a850628ec3fceef2874a57d8ce6`.
3. Retained first sensor export:
   `/data/sun/vla_mppi_20261009/replay_v177_stop_inputs/`. Every case's
   `identity.json` hashes all input files, including shared clouds and static
   maps. The first exported files are still useful; the diagnostic errors were
   curve matrix layout and selection of stale timer stamps for long stalls.
4. Copy the verified first export into a temporary local execution directory.
   `prepare_local_replays.py --source FIRST_EXPORT --output NEW_DIRECTORY`
   reconstructs the six corrected curve cases, rejecting an existing output
   directory. Compare each resulting file hash against the corresponding
   returned `native_replays02` input identity before reusing the recorded claim.
5. The local temporary root used here is
   `/private/tmp/vla_stop_audit_20261012`. Mac native environment archives158,
   167,170,172,174,176are restored from verified remote
   `mac_archive_20261012/environment/` files; their hashes are recorded under the
   respective version results. The cached image is
   `sha256:a6326521265b857c85799c5d24eb8d9a78cbb19a25d2b1e5e1d01943cea3524e`.
   Mount the temporary root as `/task` and local repository read-only at
   `/task/repo`; source `/task/recovery_v174/install/setup.bash` after Foxy.
   Build this directory with CMake and `VERSIONS_ROOT` pointing at the frozen
   versions. `run_local_replays.py` records limits, source/binary hashes and
   logs. Use a fresh result directory for a new diagnostic run.
6. `gap_intervals.json` is the result of the unchanged production
   `../2026-10-12_local_recovery/gap_query.cpp` on all1513sensor poses from run01.
   Input is `x y z yaw`, one row per sensor sample; quaternion order is wxyz.
   Mask SHA:
   `219d7982eca6c7af94545158ec97fb3b0186ff0f2166f8697d53c0b0726c56d8`.
   Sensor SHA:
   `09a0e9b051648f129e1022523cbbb1c46a5468a11ccafe1f4cfaba71c8c17e9e`.
7. `make_report.py` validates returned manifests, then regenerates the35-event
   ledger,33-interval ledger, CSV, Chinese report and offline HTML. The HTML uses
   no external scripts; relative links resolve when served under `.pipeline/`.

`run_replays.py` is the retained remote attempt that was stopped by resource
admission, not the successful execution entry point. The partial redundant
`replay_v177_stop_inputs02/` export is not used in the final results. Do not
overwrite or promote either of those attempts. See `DIAGNOSTIC_LIMITS.md` for
the distinction between exact logged rejection evidence, controlled fresh-prefix
checks, static-mask tests and a new physical episode.

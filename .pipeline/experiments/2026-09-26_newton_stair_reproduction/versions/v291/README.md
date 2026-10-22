# v291 — unified terminal control and supported-leg settling

Child of immutable v290 navigation and v216 stance. `src/` is a native overlay;
all other 13 packages inherit v290. Select the opt-in stance adapter with
`activate.install()` before importing/constructing the robot. Its parent module
is SHA-256 pinned; remote workers can supply `V291_PARENT_STANCE` explicitly.

Scope: native components, recorded-input replay and strict53 offline evaluation.
**No new physics and no change to accepted v232/v233.** Runtime inputs are frozen
in `native_manifest.json`; physical-campaign freezing and held-out route selection
remain pending. See [results and limits](RESULTS.md).

[Visual progress](../../../../../docs/research/plans/2026-10-22-convergence/index.html#v291-progress)
and `.trellis/tasks/archive/2026-10/10-22-v291-terminal-settling/` record the user's requested scope.
Keep failed attempts and old recordings. Read `results/retained_evidence.json`
for remote full-log locations/hashes; only compact evidence belongs in Git.

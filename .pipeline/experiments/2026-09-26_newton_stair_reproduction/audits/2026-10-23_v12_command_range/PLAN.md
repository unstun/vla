# Phase A — retained-recording command audit

G1 explicitly approved by Dr Sun in this session on 2026-10-23. Host: ultra9 (preflight hostname ubun).
One read-only extraction campaign, 34 retained recordings, estimate 20–40 minutes; zero new physics.
Phase C remains after B; G2/G3 are pending. Local branch: local/research-unpublished; no push.

Source of truth is this local directory. `source/audit.py` runs through SSH stdin with embedded frozen
`request.json`, using `nice -n 19 /home/ubuntu/sun/vla_v234_20261017/env/newton_worker/bin/python -B -`.
Only Python standard-library read/analysis operations execute remotely. No remote directory or source
file is created. The per-run output is JSONL on stdout; local `results/extract01.jsonl` and the execution
receipt are create-exclusive. Failed rows and interrupted output remain. Source hashes travel with
that execution and are verified locally before SSH. Frozen definitions are in `DEFINITIONS.md`.

Remote originals:
- `/home/ubuntu/sun/vla_v290_20261021/physical_runs/`
- `/home/ubuntu/sun/vla_v291_pair24_20261022/physical_runs/`

Local return: compact run/band/interval JSON, historical source identities, host/execution receipts,
summary tables, scientific figures and REPORT.md. Expected <5 MB; no raw telemetry, full logs, weights,
video or build artifacts. Original multi-GB data remains on ultra9 with its historical hashes.

Checks before extraction: boundary, dt weighting, signed projection, window fallback, missingness,
pure-yaw sign/end/censoring tests; compile/import of stdlib-only audit; full 34-entry request validation.
After extraction: all requests accounted for, original source hashes matched, disjoint durations sum to
window duration, inclusive-band overlap exact, pure-yaw totals/longest agree with the interval rows,
plots agree with JSON, source freeze unchanged. Preserve failures without replacement.

Commit the phase's source, definitions, compact evidence and task records only after the checks pass,
after file-list/size review. No navigation/locomotion implementation in this phase.

# v48/v49 timing comparison

Generated from the original `v48_realtime_trial01/scan.log` and
`v49_realtime_trial02/scan.log`. The same two plots are shown for each run:
rolling one-wall-second local attempt/new-plan/continuation frequency versus
simulation time, and full nominal solve latency in milliseconds versus
simulation time. Green points denote accepted warm-only rounds below 10 ms.
Red points denote failed rounds or timeout stop commands; they do not prove
that the backend completed its stop protocol.

The first partial rolling window is omitted. Each completed outcome is assigned
to its attempt-start timestamp. Clock interpolation uses only original logged
wall/simulation pairs and never extrapolates beyond the last attempt. CSV rows
retain source log line numbers. `provenance.json` binds inputs, analysis script,
metrics, data and plots by SHA-256. The two runs have different progress and
exposure; this is not a paired live-state experiment.

Reproduce from the repository with Python, NumPy and Matplotlib:
`python3 .pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v49/analysis/analyze_and_plot.py`.
See `../../RESULTS.md` for the failed acceptance gates and the stop-protocol defect.

# v48 real-time trial time series

Post-run analysis of `v48_realtime_trial01` on `gpu5070ti`. The frozen v48
implementation and original run evidence are unchanged.

## Figure and underlying data

- `v48_planning_time_series.png`: 3120 × 2040 preview.
- `v48_planning_time_series.svg` and `.pdf`: vector exports.
- `v48_frequency.csv`: sampled rolling frequency and clock mapping.
- `v48_round_latency.csv`: every completed round, with raw log line references.
- `provenance.json`: input/output SHA-256 hashes, definitions, counts, and versions.

The top panel counts all nominal attempt starts in the trailing interval
`(t - 1 wall second, t]`, sampled every 0.05 wall seconds. Its x-coordinate is
simulation time, interpolated between the logged wall/simulation start-clock
pairs. The first partial window is excluded. This measures the wall-clock
scheduler throughput; it does not measure starts per simulated second. The
overall reference rate is `(N - 1) / (last wall start - first wall start)`.

The lower panel plots `nominal_replan_result wall_s × 1000` at the corresponding
attempt's simulation start time. It includes failed completed rounds and measures
the entire local replanning round, rather than just the optimizer. The logarithmic
axis exposes both the sub-10 ms regime and large spikes. The 33.3 ms line is the
nominal 30 Hz per-round budget.

Warm-only rounds have an accepted warm seed and no graph fallback. There are
731 warm-only rounds below 10 ms, 476 warm-only rounds at or above 10 ms, 10
warm-to-graph fallback rounds, and 94 rounds without warm acceptance. Red crosses
overlay the eight failed rounds. The single incomplete initial start contributes
to frequency but has no latency sample.

The rate approaches 30 Hz early and late in the run. The middle portion contains
a sustained slower regime, in addition to isolated spikes. Across the full start
span the attempt rate is 15.86 Hz; median latency is 3.09 ms, P99 is 207.18 ms, and
the maximum is 1,090.48 ms at simulation start time 78.9982 s.

## Regeneration and verification

From the repository root, with Python 3, NumPy, and Matplotlib installed:

```sh
python3 .pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v48/analysis/time_series/plot_v48_time_series.py
```

The script verifies the recorded raw log SHA-256 and cross-checks every plotted
round's timestamp, latency, success flag, and warm counters against its raw log
segment. It also checks counts and recomputed aggregate statistics against the
existing v48 metrics. All outputs remain beside the script.

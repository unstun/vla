# PRD: Benchmark Lite3-to-Jetson OmniVLA latency

## Goal

Measure whether an external Jetson connected through the Lite3 Wi-Fi path can
return sufficiently fresh trajectories for the intended supervisory navigation
loop, without sending robot-control commands.

## Requirements

- Use a resident model service so model load time is reported separately from
  steady-state request latency.
- Timestamp capture/decode, encode, request send/receive, queue, preprocessing,
  GPU forward, postprocessing, and result consumption with monotonic clocks.
- Run repeated trials and retain timeout, disconnect, corruption, and stale
  cases.
- Report network RTT/jitter/loss alongside application timings.
- Compare observed trajectory age with a later human-approved control budget;
  do not invent a pass threshold before measurement.

## Acceptance criteria

- [ ] Report includes warm-up, cold start, `p50`, `p95`, maximum, failure rate,
      and latency decomposition for the live Lite3-to-Jetson path.
- [ ] Raw timing records and the benchmark runner are retained locally.
- [ ] Dr Sun chooses the next architecture after reviewing the measurements.

## Out of scope

- Motor commands, autonomous navigation, and performance claims from the
  existing one-shot Jetson smoke.

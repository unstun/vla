# Experiment Records

- [`2026-08-18_omnivla_offline_smoke/`](2026-08-18_omnivla_offline_smoke/README.md)
  — OmniVLA pinned import (commit `5182600`) and offline inference smoke test.
  OmniVLA-edge: `reproduced` on macOS arm64 / CPU, not the official CUDA
  environment. OmniVLA-original (8B): `imported` at manifest level only, probe
  skipped at the pre-declared memory guard. No Lite3 claim.

Before a behavior-changing run, record the parent implementation, motivation,
exact change, expected signals, failure signals, command, local source commit,
and artifact destination. Append results after the run; do not rewrite
pre-run expectations.

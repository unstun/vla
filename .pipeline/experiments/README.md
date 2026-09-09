# Experiment Records

- [`2026-09-09_lightnav0_official_demo_rented4090/`](2026-09-09_lightnav0_official_demo_rented4090/README.md)
  — LightNav-0 official MuJoCo default-case package prepared for manual Opus
  execution on rented4090. Pinned source and all 2,236 bundled scene assets
  verified locally; checkpoint pinned but not downloaded. No inference or
  navigation run yet; `prepared_not_dispatched`.

> [待核查] Automated archive gate lacked the host/import context and did not
> complete successfully. Local source hashes and the saved SSH snapshot verify
> these facts; manual checks passed, but an automated PASS is not claimed.

- [`2026-08-18_omnivla_offline_smoke/`](2026-08-18_omnivla_offline_smoke/README.md)
  — OmniVLA pinned import (commit `5182600`) and offline inference smoke test.
  OmniVLA-edge: `reproduced` on macOS arm64 / CPU, not the official CUDA
  environment. OmniVLA-original (8B): `imported` at manifest level only, probe
  skipped at the pre-declared memory guard. No Lite3 claim.

Before a behavior-changing run, record the parent implementation, motivation,
exact change, expected signals, failure signals, command, local source commit,
and artifact destination. Append results after the run; do not rewrite
pre-run expectations.

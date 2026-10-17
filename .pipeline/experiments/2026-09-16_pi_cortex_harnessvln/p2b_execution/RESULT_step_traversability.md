# SCAN global step traversability (local)

**Status:** local tests passed. ETH remains `surveyed`, not imported.
SCAN Foxy rebuild and Isaac are **not** `integrated` or `validated`.

**Task:** `.trellis/tasks/09-22-scan-step-traversability`
**Date:** 2026-09-22

## What ran

```sh
cd .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution
python3 -m unittest test_step_traversability.py test_apply_scan_step_traversability.py -v
```

12/12 ok (AC0 five geometries; AC1 hash gate, frozen loads, immutable `scan_04` name and canonical path, overlay-manifest pin, Python/C++/patcher default parity).

## AC

| AC | Result |
|---|---|
| AC0 four geometries + flat | pass |
| AC1 hash-gated patcher; frozen occupancy loads; `scan_04` / pinned `planner.yaml` unchanged | pass |
| AC2 claim boundary | this file |

Pinned hashes after the tests (unchanged):

- `scan_04` `grid_map.h` `3a562e007f40dc78fd811b31f4326cf778cfb0e475a1d61fd0836eda3aaa28d4`
- `scan_04` `grid_map.cpp` `2b94d5e09a71f3d9349e9b816f0b1e42b3dbc03551a20b7452579122e88efc87`
- `baseline_config/planner.yaml` `42a265a35cefb69eae43896acdd13780d1a7bd36a874b2f3aae967376b6e435e`

## Defaults compiled in (not in `planner.yaml`)

critical 0.26 m, window 0.30 m, min tread 0.15 m, min step 0.04 m, band 0.05 m, enable true.

## Not done

- `python3 apply_scan_step_traversability.py scan_05` on a materialized tree
- `build_scan.py`
- Isaac walk
- ETH clone
- Building 0.74 m tread interiors more than 0.30 m from the nosing stay occupied under the flat-window rule; AC0 only checks nosings.

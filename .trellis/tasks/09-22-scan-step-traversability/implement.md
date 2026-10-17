# Implement: SCAN global step traversability

## Change boundary

- Add `p2b_execution/step_traversability.py`, `step_traversability.h`,
  `apply_scan_step_traversability.py`, and two unittest files.
- Do not edit `builds/scan_04/**`, `baseline_config/planner.yaml`, or
  unrelated dirty-worktree paths.
- No remote commands.

## Order (TDD)

1. Write `test_step_traversability.py` (four geometries + flat). Run; it
   must fail on missing module / missing function.
2. Implement `step_traversability.py` until AC0 is green.
3. Write `test_apply_scan_step_traversability.py` against a tempfile copy
   of `scan_04` `grid_map.h` / `grid_map.cpp`. Run; it must fail.
4. Implement `step_traversability.h` and the hash-gated patcher. Pin
   `scan_04` `grid_map.h` SHA from `overlay_manifest.json`.
5. Re-hash `scan_04` and pinned `planner.yaml`; they must match before.
6. Write `p2b_execution/RESULT_step_traversability.md` with AC ticks and
   claim boundary.

## Validation

```sh
cd .pipeline/experiments/2026-09-16_pi_cortex_harnessvln
python3 -m unittest p2b_execution.test_step_traversability \
  p2b_execution.test_apply_scan_step_traversability
```

(If unittest path discovery fails, run the two files by path from
`p2b_execution/`.)

## Rollback

Delete the new `p2b_execution` files. `scan_04` was never patched.

## Not this pass

`build_scan.py`, Isaac, ETH clone, heading lock.

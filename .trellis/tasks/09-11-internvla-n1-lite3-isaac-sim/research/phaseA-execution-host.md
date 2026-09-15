---
origin: lead, read-only inspection of both candidate hosts plus a static read of the pinned adapter
date: 2026-09-11
label: surveyed
---

# Phase A: which host can actually run the V12 loop

Machine-readable version: `.pipeline/experiments/2026-09-11_lite3_isaac_v12_vla/setup/host_survey.json`.

## The requirement, read from the pinned source

`run_isaac_v12_fallback.py` imports at **module level**, so these must resolve before any argument is parsed:

    isaaclab
    isaaclab_tasks.utils.parse_cfg.load_cfg_from_registry   (via run_isaac_lite3.py)
    isaaclab_rl.rsl_rl.RslRlVecEnvWrapper
    gymnasium, torch

`robot_lab` and `rsl_rl` do not need installing: the recorded recipe supplies both from the V12 tree over
`PYTHONPATH`, and the adapter calls `_activate_vendored_rsl_rl()` besides.

## The rented 4090 cannot run this today

`isaaclab_tasks` and `isaaclab_rl` are **absent**. `find_spec` returns `None` for both in all three candidate images
(`e01-walking-isaaclab`, `e01-walking-runtime`, `v17a68-dependencies`), and neither exists anywhere under the E01
workspace on disk. Only `isaaclab` 2.3.2.post1 is installed, as an ordinary PyPI wheel in the Isaac Sim bundled
python 3.11.13.

This is not an oversight upstream: E01 was locomotion **training** driven by robot_lab's own scripts and rsl_rl, and
that path never touches Isaac Lab's task registry or the RSL-RL vec-env wrapper. Our adapter does.

A correction to Phase 0.1, which recorded `e01-walking-isaaclab:20260905` as the image to reuse. It is the
*dependency* image and carries no editable installs at all; `e01-walking-runtime:20260905` is the one with the
`robot_lab` 2.3.0 and `rsl_rl_lib` 3.3.0 editable finders, pointing at
`/workspace/go2_rl_robotlab_lite3_v17a29/...`. Neither image solves the missing two packages.

Closing the gap costs something real:
- fetching Isaac Lab source on that host means GitHub, measured at 10–25 KiB/s there;
- copying from gpu5070ti means pairing `isaaclab_tasks` 0.11.12 / `isaaclab_rl` 0.4.7, built against the IsaacLab
  **source** tree whose `isaaclab` is 0.54.2, with this image's PyPI `isaaclab` 2.3.2.post1 — a combination nothing
  has tested;
- 40 GB free disk makes rebuilding a 26 GB image uncomfortable.

## gpu5070ti is ready now

Native conda env `isaaclab` (python 3.11.15, torch 2.7.0+cu128) with `isaaclab` 0.54.2, `isaaclab_tasks` 0.11.12,
`isaaclab_rl` 0.4.7 and `isaaclab_assets` 0.2.4 all present as editable installs from
`/home/sun/ssh/sun/IsaacLab`. GPU idle at 195 MiB of 16,303 MiB; 82 GB free disk.

Decisive: **the accepted `native_full02` run executed here** — 98.08 s, 74.063 m, final XY error 3.77 cm, zero
non-foot contact. Its `runtime_identity.json` records `bridge_module_sha256`
`6104fe686bcd3bc0480c0afc1b41dde84d1a35d45a6dbbe9e51d98e6719ba3e3`, which is byte-for-byte the
`run_isaac_v12_fallback.py` vendored into this repository. The recipe is recorded in that experiment's
`tools/run_native_on_host.sh` and is what `scripts/phase_a_run_native.sh` reproduces.

The caveat is VRAM: 16 GB is ample for Phase A (no cameras, no VLA) and unverified for Phase B/C, where RTX cameras
and a resident Qwen2.5-VL arrive. That is already an open item in the hot zone.

## Recommendation

Run Phase A on gpu5070ti and keep the 4090 for Phase B onward. Phase A needs no rendering and no VLA, so the 4090's
advantages do not apply yet, while its missing packages do. Sequencing this way also means the 4090 environment gets
built when `enable_cameras=True` has to be solved anyway — the same session, one bring-up instead of two.

This is Dr Sun's call, not mine: he authorized the rented 4090 on 2026-09-11, before this survey existed.

## Correction, same day: the 4090 is not missing anything

The section above is wrong where it says `isaaclab_tasks` and `isaaclab_rl` are absent. They are present. The PyPI
`isaaclab` 2.3.2.post1 wheel does not install a flat library; it bundles the entire IsaacLab source tree at

    /isaac-sim/kit/python/lib/python3.11/site-packages/isaaclab/source/
        isaaclab  isaaclab_assets  isaaclab_contrib  isaaclab_mimic  isaaclab_rl  isaaclab_tasks

`find_spec` returned `None` because those directories are not on `sys.path` by default — not because the code is
missing. I read "not importable" as "not installed". With the four package roots on `PYTHONPATH`, `isaaclab`,
`isaaclab.app`, `isaaclab_tasks`, `isaaclab_rl` and `isaaclab_assets` all resolve, out of the same wheel whose version
the image already pins. `isaaclab_tasks.utils.parse_cfg` additionally needs `pxr`, which exists only once
`AppLauncher` has started Isaac Sim; the adapter launches the app before importing it (`run_isaac_lite3.py:725`), so
that is the normal import order rather than a gap.

Consequences:

1. **Dr Sun's decision to stay on the rented 4090 stands, and costs a PYTHONPATH entry rather than hours.** No Isaac
   Lab download, no image rebuild, no mixing of `isaaclab_tasks` 0.11.12 against a 2.3.2.post1 `isaaclab`.
2. The gpu5070ti survey remains accurate and is kept as the control: if a 4090 run fails, that host ran the accepted
   74 m V12 run with byte-identical bridge source, so a difference there isolates the environment from the code.
3. The IsaacLab v2.3.2 source tarball fetched locally while diagnosing this (38,563,721 bytes, sha256
   `1db015e079c3ee5c7d86ac41ccbdbf5e2153afa3b30743efa52a926d70d282e3`) turned out to be unnecessary and was not
   shipped anywhere.

Method note for next time: `find_spec(name) is None` answers "is this importable from the current sys.path", never
"does this code exist on this machine". The second question needs a filesystem search, which is what found the
bundled tree.

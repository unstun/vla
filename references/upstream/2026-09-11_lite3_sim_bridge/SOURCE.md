# Lite3 Isaac Sim bridge source

Origin: the sibling project `/Users/sun/tongbu/study/phdproject/machine-dog-nav`, path
`integration/lite3_sim_bridge/`. Read-only reference for VLA work (AGENTS.md); nothing there was modified.

## Why these files were vendored rather than pinned to a commit

Dr Sun approved (2026-09-11) pinning clean commits where possible and vendoring by SHA-256 otherwise. For this package a
commit pin would have imported the WRONG code.

At the time of import, machine-dog-nav HEAD was `06cfd9a34c92e16354caa1a418ef2c0467ab44ad` on branch
`codex/scan-foxy-isaac`, and 28 files under `integration/lite3_sim_bridge` were modified relative to it. The four core
files differ between the working tree and HEAD:

| File | worktree | HEAD |
| --- | --- | --- |
| transport.py | `286f24e40957d0d5` | `652b74bc5bbbcf1c` |
| protocol.py | `a9f57b0ed216cb16` | `727b7b9f2be48b72` |
| command_state.py | `c755b862b7e4e98c` | `14907e403f030309` |
| isaac_adapter_core.py | `664f8227a7018b1d` | `6939506b4922a015` |

The accepted closed-loop run `native_full02` (98.08 s, 74.063 m, final XY error 3.77 cm, zero non-foot contact) records its
executed source in
`machine-dog-nav/.pipeline/experiments/2026-09-11_pct_scan_upstream_baseline/full02_evidence/runs/native_full02/executed_source_manifest.json`.
Every vendored file's SHA-256 equals that manifest's entry, and `transport.py`'s `286f24e4...` is the value that manifest
records. **HEAD's versions never produced a successful run.** So the authority for this import is the run manifest, not a
git commit, and the vendored bytes are exactly what walked.

## What was taken and what was not

Taken (15 files, see `SHA256SUMS.txt`): the wire protocol and framing, the command clamp and watchdog, the contact and
feedback-health guards, the body-state stream, the Isaac adapter core, the accepted V12 adapter
`run_isaac_v12_fallback.py`, the four modules that adapter imports at module level
(`run_isaac_lite3.py`, `mid360_pattern.py`, `office_crowd_contract.py`, `official_human_contract.py`), the
`foxy_bridge.yaml` clamp configuration, and the package README.

Not taken: everything ROS-side (`foxy_bridge_node.py`, launch files, rviz configs) and everything belonging to the
PCT/SCAN planner or the office-crowd and human-animation studies. This task drops ROS 2 Foxy entirely — the planner is
replaced by InternVLA-N1 — so the Foxy node has no role. See the task's `design.md`, Decision 1.

### Correction, 2026-09-11 (found at the start of Phase A)

The first import took 11 files and was **not importable**. `run_isaac_v12_fallback.py` has four module-level
`from .` imports that the selection missed: `.run_isaac_lite3` (line 72, and the source of `_qualification_report`),
`.mid360_pattern` (40), `.official_human_contract` (62) and `.office_crowd_contract` (67). Their names read as
scene-study code, which is why they were cut, but the import is unconditional, so `import
lite3_sim_bridge.run_isaac_v12_fallback` would have raised `ModuleNotFoundError` on the first Phase A run. All four
were added and verified against the same run manifest. Their own imports reach nothing outside the vendored set
(stdlib plus numpy, plus the already-vendored `command_state`, `isaac_adapter_core`, `protocol`, `transport`), so
the module-level closure is now complete; this is checked by parsing every vendored file's AST rather than by eye.

`office_review_presentation.py` (124 KB) is still **deliberately excluded**. It is the one remaining unvendored
`from .` target, and all six of its import sites are lazy (inside functions) and gated by
`_office_review_presentation_enabled(args)` or `args.office_review_material`, which are false unless an
`--office-review-*` flag is passed. A `--course flat` qualification run never reaches them. If an office-review
rendering path is ever needed here, vendor it then and re-verify.

## Verification

    cd references/upstream/2026-09-11_lite3_sim_bridge && shasum -a 256 -c SHA256SUMS.txt

All 15 hashes were re-checked file by file against that manifest on 2026-09-11 and every one matched. They can be
re-checked at any time; if machine-dog-nav later commits this
work, record the resulting commit here but do not replace these bytes without re-verifying against a successful run.

## License and attribution

Inherits the licensing of `machine-dog-nav`; the package embeds upstream PCT/SCAN work from
`yagami-light7/PCT-SCAN-ROS2 @ 1cf45a1c12ca785ce533293302be09d51daf0ccb` in parts not vendored here.

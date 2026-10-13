---
origin: ai+web
reviewed: false
date: 2026-09-09
stage: experiment_and_analysis
---

> [摘要] Dr Sun chose the official LightNav-0 server-side demo after TIC-VLA's distance-stop failures and mixed
> DualVLN castle results (3/5, 2/5); this records a prepared rented4090 execution package, not a reproduction.
> Crossed the 31-day threshold on 2026-10-10; the original text below is preserved unchanged.

# LightNav-0 preparation and navigation evidence boundaries

Archived at 2026-09-09 07:55 PDT for task `09-09-lightnav0-official-demo-rented4090`.
The user requested local preservation before the current session's usage limit.
No new inference or training was run as part of this archive.

## Current decision and why

Dr Sun selected the official LightNav-0 server-side example after TIC-VLA's
three-meter stop failures and the mixed DualVLN public-scene results. Retain the
author's scene, instruction, client and controller so the next observation has
clear upstream provenance. This is a prepared manual Opus execution package,
not a completed reproduction or milestone.

- Source: https://github.com/lightorigins/LightNav-0 at
  `d83fbfb9748ca6b497a2f2a7f4a3e95e2110e40c`.
- Model: https://huggingface.co/LightOriginsHQ/LightNav-0 at
  `826dc5fbfa37afa8293d2e336d329b6ffc0bfb64`, original BF16, about 4.848B
  stored parameters. Weight bytes have not been downloaded.
- Preserve the bundled ProcTHOR `val_2_ceiling.xml`, default kinematic
  TurtleBot, and `move forward, then go to the trashcan on the right`.
- Three bounded repetitions on rented4090; retain every failed attempt, raw
  action/STOP provenance and actual first-/third-person videos. Preserve the
  unrelated Isaac Sim process and recheck resources before execution.
- The preparation package records successful checks of 2,236 scene asset
  entries and 2,459 source files. This archive read those records; it did not
  repeat the whole asset or remote verification.

## Existing evidence that must not be overstated

TIC-VLA's matched Chinese/English distance-stop trials both failed. In the
Chinese trial, forward displacement crossed 3.011 m at measured 1.3817 m/s
while desired/applied speed remained 1.5 m/s. Timeout is not policy stopping.
This does not establish a general language ranking or a limit shared by all
1B models. Keep model intent, trajectory conversion and evaluator termination
separate when diagnosing the failure.

DualVLN's official evaluator ran on two custom public-castle episodes five
times: successes 3/5 and 2/5; all ten runs emitted native S2 `STOP`. This is not
standard R2R or paper-score reproduction. The lead review found two derived
manifest mismatches, while the reviewed raw run records and videos matched.
The Chinese chair trial moved 6.75 m after an initial 120-degree left turn and
emitted STOP, but exact placement between chairs is unscored. Failed attempt
logs were deleted by the executor; full dynamic prompts were not retained.

## Local evidence and continuation

All paths below are relative to the VLA repository:

- `.pipeline/experiments/2026-09-09_lightnav0_official_demo_rented4090/OPUS_EXECUTION_PACKAGE.md`
- `.trellis/tasks/09-09-lightnav0-official-demo-rented4090/task.json`
- `.pipeline/experiments/2026-09-08_tic_vla_dynanav_5070ti/distance_language_pair_2026-09-08/RESULT.md`
- `.pipeline/experiments/2026-09-08_dualvln_rented4090/review/PUBLIC_SCENES_LEAD_REVIEW.md`
- `.pipeline/experiments/2026-09-08_dualvln_rented4090/public_scenes/requests/2026-09-09_zh_between_two_chairs/review/LEAD_REVIEW.md`
- `.pipeline/handoffs/2026-09-09_vla_lightnav0_handoff.md`

The archive worker read the execution package, task metadata and three result/
review documents above. It preserved the entire previous hot-zone state, byte
for byte, in `bigmemory/冷区/改动记录/2026-09-09_075521_pre-lightnav-hot-zone/` with SHA-256 identities in
`MANIFEST.json`. Older OmniVLA decisions were not silently closed or freshly
revalidated. No Git staging or commit was performed by this worker; the lead
owns the final archive backup.

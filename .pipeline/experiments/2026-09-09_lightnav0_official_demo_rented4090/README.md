# LightNav-0 official demo on rented4090

Current manual continuation entry point:
[visual reproduction package v3](continuation_v3/EXECUTION_PACKAGE.md), with
[visual acceptance](continuation_v3/VISUAL_SPEC.md) and
[source investigation](continuation_v3/RESEARCH.md). It is **prepared_not_dispatched**.
Preparation rechecked the running host/checkpoint and tested static state rendering;
it did not start new LightNav inference or navigation episodes. The earlier packages
and round-1 evidence below remain historical inputs.

Stage: experiment + analysis. Status: **executed_round1_corrections_required**
(package v2 executed by Opus on 2026-09-09; lead review in
`review/LEAD_REVIEW_2026-09-09.md`; round-2 corrections in `OPUS_CORRECTION_PACKAGE.md`).

Dr Sun requested server-side reproduction of the official LightNav-0 case.
`OPUS_EXECUTION_PACKAGE.md` (v2) is the manual English Opus package; it
supersedes the 14:48Z version kept in git history (`3635579`). Round 1 ran the
official demo loop three times with genuine BF16 inference and a native model
stop each time (`reproduced` for the demo loop only). Lead assessment: all three
runs stopped next to a dog bed about 2.3-2.6 m short of the instructed trashcan,
so the task outcome is a navigation failure (0/3). Third-person raw frames of
round 1 are incomplete because of a harness naming defect; videos, analysis,
manifests and three recorder-complete repetitions are pending in round 2.

Selected case: upstream MuJoCo ProcTHOR `val_2` scene, default TurtleBot, and
`move forward, then go to the trashcan on the right`. The complete official
source is pinned locally; its 2,236 bundled asset entries passed size/hash checks.

What the lead pre-staged (details and measurements in
`setup/lead_prestage_2026-09-09.json`):

- Remote root `/home/ubuntu/sun/vla_exec/2026-09-09_lightnav0_official_demo_rented4090`
  with the verified work copy (`setup/work_copy_verification_clean.json`),
  a conda-forge Python 3.11.16 base plus uv 0.11.21 (`runs/env_py311`, remote),
  and a running pinned-checkpoint download (`runs/download_ckpt`, remote).
- A local pinned-checkpoint download into `checkpoints/LightNav-0/` (ignored
  bytes; manifest `setup/checkpoint_manifest_local.json` on completion).
- `scripts/`: job supervisor, verified checkpoint downloader, work-copy
  verifier, and the two official-environment install scripts (not executed).
- Measured host and network facts: PyPI must go through the Tsinghua mirror,
  GitHub is unusable from the host, Hugging Face is fast.

`setup/` contains official API responses, checkpoint configuration, full source
file hashes, scene verification, server preflight, and lead pre-stage evidence.
These are preparation artifacts, not runtime outputs.
`setup/preparation_manifest.json` hashes the finalized package and preparation
inputs, excluding itself and the final validation report.

Local source of truth is `/Users/sun/tongbu/study/phdproject/vla`.
Use existing SSH alias `rented4090`; never write credentials into artifacts.

Source recovery: clone https://github.com/lightorigins/LightNav-0 and checkout
`d83fbfb9748ca6b497a2f2a7f4a3e95e2110e40c`, then verify against
`setup/upstream_file_manifest.json`. Model recovery: run
`scripts/download_checkpoint.py setup/model_source.json <out_dir> <manifest>`,
which downloads `LightOriginsHQ/LightNav-0` at
`826dc5fbfa37afa8293d2e336d329b6ffc0bfb64` and checks every LFS hash and blob id.
Source clone bytes use the existing `references/upstream/.gitignore` rule;
their provenance and SHA-256 manifest remain visible to Git.

# LightNav-0 official demo on rented4090

Stage: experiment preparation. Status: **prepared_not_dispatched**.

Dr Sun requested server-side reproduction of the official LightNav-0 case.
`OPUS_EXECUTION_PACKAGE.md` is the manual English Opus package. No model
inference, navigation rollout, or reproduction claim has been made during
preparation. The dedicated Trellis task remains at planning until execution.

Selected case: upstream MuJoCo ProcTHOR `val_2` scene, default TurtleBot, and
`move forward, then go to the trashcan on the right`. The complete official
source is pinned locally; its 2,236 bundled asset entries passed size/hash checks.
The checkpoint is pinned but has not yet been downloaded. The model and
simulator environments have not been installed by the lead.

`setup/` contains official API responses, checkpoint configuration, full source
file hashes, scene verification and server preflight evidence. These are
preparation artifacts, not runtime outputs. `setup/preparation_manifest.json`
hashes the finalized package and preparation inputs, excluding itself and the
final validation report.

Local source of truth is `/Users/sun/tongbu/study/phdproject/vla`.
Remote root is `/home/ubuntu/sun/vla_exec/2026-09-09_lightnav0_official_demo_rented4090`.
Use existing SSH alias `rented4090`; never write credentials into artifacts.

Source recovery: clone https://github.com/lightorigins/LightNav-0 and checkout
`d83fbfb9748ca6b497a2f2a7f4a3e95e2110e40c`, then verify against
`setup/upstream_file_manifest.json`. Model recovery: download
`LightOriginsHQ/LightNav-0` at `826dc5fbfa37afa8293d2e336d329b6ffc0bfb64` and
check all recorded LFS hashes and sizes from `setup/model_source.json`.
Source clone bytes use the existing `references/upstream/.gitignore` rule;
their provenance and SHA-256 manifest remain visible to Git.

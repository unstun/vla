# LightNav-0 RTX 5070 Ti inference probe

Stage: experiment + analysis. Status: BF16 open-loop inference passed; pending
human review. See [RESULT.md](RESULT.md) for measured results and limitations.

User authorization: "可以试试", following the BF16-first / official LLM-only FP8
discussion. This task is separate from the rented4090 simulation reproduction.

Local source of truth: `/Users/sun/tongbu/study/phdproject/vla`.
Remote execution copy: `gpu5070ti:/home/sun/vla_exec/2026-09-09_lightnav0_5070ti_inference`.
The historical gpu5070ti-relay alias is absent in the current SSH configuration;
the effective gpu5070ti target and GPU were checked live.

Source: https://github.com/lightorigins/LightNav-0 at
`d83fbfb9748ca6b497a2f2a7f4a3e95e2110e40c`, Apache-2.0. Reuse the pristine source
snapshot and its manifest from the sibling official-demo preparation.
Checkpoint: https://huggingface.co/LightOriginsHQ/LightNav-0 at
`826dc5fbfa37afa8293d2e336d329b6ffc0bfb64`, Apache-2.0. Shard SHA-256:
`ffc4a925378a881afa761865048eb8d07c55cacf5eaf66548b6641c39f67af18`.
The complete verified local checkpoint is reused from
`../2026-09-09_lightnav0_official_demo_rented4090/checkpoints/LightNav-0`.
Remote checkpoint bytes are acquired from the exact same public revision.

Input: unchanged first-person JPEGs from the sibling official MuJoCo demo's
rep_01. These are replay observations generated under a different run, not new
5070 Ti closed-loop observations. The 64-observation stress fixture repeats the
last frame after the available chronological images; record this explicitly.
Instruction: `move forward, then go to the trashcan on the right`.
Scene assets retain the sibling provenance: MolmoSpaces ProcTHOR, CC BY 4.0.

Reuse `run_job.py`, `download_checkpoint.py`, and `verify_work_copy.py` from the
sibling preparation without changing their logic; copies and hashes are recorded.
The task also reuses the tested range downloader and its tests from the earlier
TIC-VLA task; `resume_parallel.py` adapts only the pinned LightNav shard metadata.
No compute-helper was found in the workspace or configured tool paths, so use
SSH and rsync with the same explicit local-to-remote sync and return gates.

Execution: install pinned upstream extras in an isolated Python 3.11 venv;
run BF16 with one sequence first; test fp8_llm_only only on memory failure.
Keep the original 64-frame history, visual resolution/pooling, greedy decoding,
and shipped RVQ decoder. Setup/download jobs have 1800-second deadlines; each
GPU probe has a 600-second deadline. Only task-owned process groups may be stopped.

Sync gate: verify pristine source files, all checkpoint files against published
identities, and task script/input SHA-256 before inference. Return setup logs,
raw outputs, timing/memory/quantization evidence, and exit metadata locally and
verify their hashes. No model-fit claim for concurrent simulation, no navigation
success claim, and no measured FPS claim until the appropriate runtime exists.

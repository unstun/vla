---
origin: human_approved
reviewed: false
as_of: 2026-08-19
---

# Pre-run decision log: OmniVLA-original official CUDA reproduction

This section was written before the first model process. Results are appended;
the expectations and stop rules below are not rewritten after observing output.

## Authorization and identity

Dr Sun authorized the gpu40901 deployment work. The only source identity is
OmniVLA commit `5182600cb4a9ee07684e17cdd2a6cbafc56b8a68`; the only original
checkpoint identity is `NHirose/omnivla-original` revision
`e36a84d4923c041149d441f93f3bdb7092bb5f07`. The remote execution copy is
`/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_original_cuda/`.

## Expected result

The original upstream entry point exits zero after one CUDA forward pass and
writes a finite raw trajectory of shape `(8, 4)`, metric-scaled trajectory,
finite controller diagnostic values, a figure, timing, peak process VRAM, and
the exact source/checkpoint identities. This is reproduction evidence, not
Lite3 integration or semantic validation.

## Failure signals

- source or checkpoint manifest mismatch;
- 60-second preflight minimum free VRAM below 24,576 MiB;
- CUDA unavailable or the 0.45 process-memory cap not applied;
- dependency/import/model-load failure, CUDA OOM, timeout, non-zero exit;
- missing figure/JSON, wrong trajectory shape, or non-finite values;
- interference with any pre-existing process or file outside the declared
  `/home/ubuntu/sun/` execution root.

## Stop rules

- Never signal another user's training or CARLA process.
- Never relax the 24,576 MiB preflight guard, 0.45 memory fraction, `nice=10`,
  30-minute timeout, or one-model-process rule.
- The first failed model attempt may be diagnosed and corrected only through a
  local recorded patch; at most three model attempts are allowed.
- Do not claim `reproduced` unless the forward-pass artifacts pass validation.
- Weights remain remote; only logs, hashes, JSON, and figures sync back.

## Results appended after execution

The prerequisite gate passed on the first original-model attempt. Run
`20260819T101229Z_original_upstream_default` exited 0 after one CUDA forward,
produced a finite `(8, 4)` trajectory and figure, and recorded 0.356 seconds of
forward time. Its 60-second guard observed at least 33,701 MiB free VRAM; peak
CUDA allocation was 16,031,429,632 bytes and the 0.45 cap was active.

The deployment-specific confirmation
`20260819T102034Z_original_language_move_forward` also exited 0 with modality
ID 7, instruction `move forward`, and finite shape `(8, 4)`. Forward time was
0.361 seconds, the preflight minimum was 33,705 MiB, and peak CUDA allocation
was 16,038,781,440 bytes.

The original checkpoint therefore earns `reproduced` for the declared pinned
official-CUDA single-forward contract. The wider sweep, reference-image
comparison, and edge CPU-vs-CUDA comparison remain pending and are not implied
by this result.

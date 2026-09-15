# OmniVLA-original CUDA reproduction on gpu40901

Status: `OmniVLA-original` is `reproduced` for the pinned official-CUDA
single-forward contract. The upstream-default and language-only `move forward`
configurations both passed. The broader configuration sweep and edge
CPU-vs-CUDA comparison in the parent task remain unexecuted, so that parent
task remains in progress.

The local source of truth is the pinned third-party snapshot plus the recorded
patches and scripts in this experiment directory. The execution copy is
`/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_original_cuda/`. Model weights
remain remote. The source is pinned at commit
`5182600cb4a9ee07684e17cdd2a6cbafc56b8a68`; the original checkpoint is pinned
at revision `e36a84d4923c041149d441f93f3bdb7092bb5f07`. Remote checkpoint
verification passed with 29 present artifacts, zero absent artifacts, and zero
mismatches.

## Successful runs

| Run | Modality | Result | Forward | Min free VRAM | Peak allocated |
|---|---|---|---:|---:|---:|
| `20260819T101229Z_original_upstream_default` | image only | exit 0, finite 8x4 | 0.356 s | 33,701 MiB | 14.93 GiB |
| `20260819T102034Z_original_language_move_forward` | language only | exit 0, finite 8x4 | 0.361 s | 33,705 MiB | 14.94 GiB |

Both processes used Python 3.10.20, PyTorch 2.2.0+cu121, Flash Attention
2.5.5, `nice=10`, a 1,800-second wall deadline, and the reviewed 0.45 CUDA
memory-fraction cap. The exact environment compatibility deviations are in
`env/DEVIATIONS.md`. No task-owned model process remained after either run, and
the pre-existing CARLA and IsaacLab processes were not signalled.

This evidence supports only reproduction of the pinned original model's
single CUDA forward. It is not semantic task validation, a benchmark, Lite3
integration, closed-loop navigation, or locomotion evidence.

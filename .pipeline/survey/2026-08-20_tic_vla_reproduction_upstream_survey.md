---
origin: ai_only
reviewed: false
---

# TIC-VLA upstream reproduction survey

## Decision context

Dr Sun selected TIC-VLA for the next reproduction target after OmniVLA showed
weak safety-prompt and directional semantics in a bounded offline audit. This
record verifies the newly selected upstream before import or execution. It does
not approve training or robot actuation.

## Canonical sources

- Paper: <https://arxiv.org/html/2602.02459>
- Project: <https://ucla-mobility.github.io/TIC-VLA/>
- Repository: <https://github.com/ucla-mobility/TIC-VLA>
- Released checkpoint and data: <https://huggingface.co/datasets/handsomeYun/TIC-VLA>
- Selected branch and commit: `main` at
  `9fa6f8b66b9e121d5df5df071297bba8e5353ebb`
- Repository license: UCLA Academic Software License, academic/nonprofit
  research only, no further transfer, commercial use requires contact with the
  licensor.

## Released interface and assets

- Model: InternVL3-1B semantic reasoner plus a fast action expert.
- Observation: delayed visual-language context, current RGB observation, robot
  state, explicit reasoning delay, and ego-motion offsets.
- Output: a short horizon of continuous local waypoint/action offsets. The
  training/evaluation package represents 30 two-dimensional waypoint steps;
  paper-level control converts a future target to linear/angular velocity.
- Official checkpoint: `TIC-VLA-model.ckpt`, approximately 1.94 GB; published
  SHA-256
  `376263f89fad0f42c267d85655019232edc91d36e214e23424804dd4cd42e036`.
- Official dependencies: Python 3.10+, PyTorch 2.8.0+cu128, torchvision
  0.23.0+cu128, Transformers 4.x, and separate Isaac Sim 5.0 for DynaNav.
- Official commands include open-loop evaluation and DynaNav smoke/full
  benchmark scripts. The repository does not provide a Lite3 deployment entry.

## Evidence relevant to reproduction cost

- The paper reports Go2 evaluation on Jetson Orin NX and an asynchronous split
  between slow VLM reasoning and the faster action policy. This is a paper
  result, not local evidence.
- The public DynaNav example currently exercises four Nova Carter episodes.
  Exact paper-table reproduction requires Isaac Sim and more work than a model
  checkpoint smoke.
- The six published data archives total more than 500 GB. The first smoke must
  extract or construct the smallest official-format sample instead of mirroring
  all data.
- The current Jetson AGX Orin 64GB uses JetPack 5.1.2, Python 3.8, and Jetson
  PyTorch 2.1. It cannot install the upstream x86 CUDA 12.8 wheel set unchanged.
- `gpu40901` has the compatible x86_64/Python 3.10 shape and enough GPU/disk
  capacity to establish the upstream checkpoint gate before any Jetson port.

## Recommended first reproduction target

Run one released-checkpoint, official-format CUDA inference on `gpu40901`, keep
the exact upstream commit pristine, and record checkpoint-key loading, language
response, waypoint output, latency, VRAM, and three serial repeats. Only after
that gate, attempt a receive-only Orin compatibility overlay using the same
input and checkpoint.

## Human selection

Dr Sun selected the alternative direct-Orin route on 2026-08-20: use the
released pretrained weights on the Jetson AGX Orin 64GB, skip `gpu40901`, and
perform no training. This lowers time to the target device but means the first
result is an Orin compatibility smoke rather than an exact official x86-stack
reproduction.

## Status and uncertainty

- Paper and repository: `surveyed`.
- Source: not yet `imported` in this task.
- Runtime: not yet `reproduced` in this task.
- Lite3 integration and validation: not attempted.
- The released checkpoint has not yet been checked locally for exact state-dict
  compatibility with both the training and DynaNav inference classes.
- No conclusion is justified yet about Lite3 navigation, collision avoidance,
  language compliance, stop behavior, or external-Jetson Wi-Fi latency.

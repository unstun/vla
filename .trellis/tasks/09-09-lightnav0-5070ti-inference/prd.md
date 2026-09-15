# LightNav-0 inference on RTX 5070 Ti

Stage: experiment + analysis. Dr Sun authorized a bounded trial in the current
conversation after discussing BF16 and the official fp8_llm_only alternative.

Determine whether the pinned pretrained model can perform GPU inference on the
16 GB RTX 5070 Ti. Use BF16 first; if memory prevents it, evaluate the official
LLM-only FP8 option while retaining BF16 vision. Keep the existing 4090 task intact.

Acceptance: verified source/checkpoint/input identities, successful real-image
inference with raw tokens and finite 10x3 decoded waypoints, measured GPU usage
and synchronized latency, recorded dependency versions, bounded process exit,
and locally returned artifacts with matching SHA-256. Failed attempts remain.
Test fixed replay inputs, including a 64-observation capacity case. This is an
open-loop compatibility probe, not navigation success or a benchmark.

No training, robot actuation, unrelated process changes, or system driver changes.
Owned experiment: .pipeline/experiments/2026-09-09_lightnav0_5070ti_inference.
Maximum setup/download 1800 seconds per job; GPU probe 600 seconds per attempt.
Preserve upstream model processing/history/decoder settings and record all resource
overrides. Start with one sequence and 2 GiB KV cache. No service is exposed.

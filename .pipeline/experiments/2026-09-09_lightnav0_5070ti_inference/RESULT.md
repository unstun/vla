# LightNav-0 BF16 inference on RTX 5070 Ti

Date: 2026-09-09. Stage: experiment + analysis. Review status: pending human review.

**The original BF16 checkpoint ran successfully on the 16 GB RTX 5070 Ti.**
Nine open-loop predictions passed the declared compatibility checks, without
quantization, CPU weight offload, processing overrides or upstream code changes.
The original plan only called for FP8 if memory blocked BF16; FP8 was not tested.

## Measured result

| Observations supplied | Repeats | First call (ms) | Later-call median (ms) |
| --- | ---: | ---: | ---: |
| 1 | 3 | 16,675.2 | 95.2 |
| 16 | 3 | 170.3 | 130.9 |
| 64 | 3 | 295.8 | 192.5 |

Times are CUDA-synchronized wall time around the upstream `predict_waypoints`
call, including its preprocessing and decoding, after image loading/observation.
Each median uses the two later calls for that identical observation buffer.
The first-ever call incurs substantial cold-start work and must not be mixed
into steady-state latency. Engine construction separately took 75.34 seconds.
The complete bounded job took 101.59 seconds and exited 0 without timeout.
These timings are not camera-to-controller latency or navigation FPS.

- Total-card NVML sampled peak: **12,646.625 MiB = 12.3502 GiB**, including the
  small desktop baseline. 875 samples were collected with a 0.1-second target
  interval; this is a sampled peak, not an exact high-water mark.
- PyTorch forward allocation high-water mark: 11.0042 GiB; reservation peak:
  11.3477 GiB. These quantities exclude some CUDA/runtime allocations.
- All 9 outputs contain raw model tokens and finite `(10, 3)` waypoints.
  The raw tokens match across all three repeats within each input case.
- Runtime inspection found all enumerated parameters on `cuda:0`, with BF16
  vision and language parameters and unquantized linear methods. Runtime unique
  parameter enumeration is separate from the HF stored-tensor count; the
  checkpoint configuration uses tied word embeddings.
- Postflight: no task jobs or GPU compute processes; total GPU use 186 MiB,
  reported free memory 15,633 MiB, GPU utilization 0%.

## Exact scope and configuration

Source commit: `d83fbfb9748ca6b497a2f2a7f4a3e95e2110e40c`.
Model revision: `826dc5fbfa37afa8293d2e336d329b6ffc0bfb64`.
Shard SHA-256: `ffc4a925378a881afa761865048eb8d07c55cacf5eaf66548b6641c39f67af18`.
Official source and checkpoint links are in `README.md` and `setup/model_source.json`.

Python 3.11.15; torch 2.10.0+cu128; vLLM 0.19.1; Transformers 5.8.0;
nvidia-cutlass-dsl 4.5.2; GPU driver 580.126.09; compute capability 12.0.
The installed torch build includes `sm_120`; a finite BF16 CUDA matrix operation
was checked separately before full model inference.

The wrapper uses the same upstream engine, `TrackingAgent`, frame preprocessing,
SlowFast history selection and RVQ decoder as the public prediction API.
Resource settings: one sequence, GPU memory utilization 0.85, upstream default
2 GiB KV cache and enabled CUDA Graphs. Processing remains checkpoint-defined:
256x448 model frames, 4 Hz timestamp basis, 64-frame setting, post-ViT pooling,
original SlowFast tiers, greedy decoding, maximum 8 new tokens as in the
official prediction CLI. See `runs/bf16_default/evidence/request.json` and
`model_state.json` for the resolved settings and parameter/device inspection.

Instruction: `move forward, then go to the trashcan on the right`.
Input uses 56 saved first-person JPEGs from the earlier rented4090 official-demo
rep_01, with the last image repeated 8 times for the 64-observation capacity case.
All JPEG bytes are retained in `fixtures/`, with provenance and padding labels
in `setup/fixture_manifest.json`. Replay uses synthetic 4 Hz timestamps; it does
not reproduce the earlier episode's clock or exact model observations. SlowFast
can retain longer episode history: this 64-observation probe does not establish
memory bounds for arbitrary-duration sessions.

No simulator/controller ran on the 5070 Ti. The outputs do not establish target
arrival, learned stopping, simultaneous simulator capacity, or Lite3 readiness.

## Evidence and checks

- `runs/bf16_default/{stdout.log,stderr.log,meta.json,process.json}`: raw output,
  warnings, explicit command, process identity and deadline/exit metadata.
- `runs/bf16_default/evidence/`: raw predictions, GPU samples, model state, request
  and result. `analysis.json` summarizes those records.
- Source sync gate: 2,449 upstream files match, zero missing/mismatched/extra
  source files; documented generated files and docs assets are excluded.
- Full checkpoint: all 20 files / 9,709,350,260 bytes verified both on the GPU
  host and against the complete local sibling checkpoint copy. No extra local
  weight copy was necessary.
- Task script/input hash gate passed. All **48** returned evidence files match
  their remote SHA-256; see `setup/local_return_verification.json`.
- Range-download tests covered truncation, ignored ranges, parallel failure,
  retained pieces and resume. Python scripts parse; shell scripts pass `bash -n`.

The first serial download was deliberately stopped to resume its 3,144,794,112
bytes with the existing four-worker range downloader. Its exit 143 is retained
under `runs/download/`; this is a transport handoff, not a failed inference.
The parallel download and installation both exited 0 within their deadlines.

Warnings remain in the raw logs: vLLM warns about upstream disabling chunked
prefill, Transformers/CUDA bindings emit deprecations, and NCCL warns that its
process group was not explicitly destroyed at interpreter exit. No warning was
suppressed. Postflight directly confirms release of GPU memory and task processes.
This probe checks executable finite output, not numerical parity or navigation quality.

## Rerun

On the existing isolated remote environment, from the experiment root:

```bash
python3 scripts/run_job.py --seconds 600 bf16_repeat -- bash scripts/run_probe.sh bf16 bf16_repeat
```

Use a new run name: the supervisor rejects reuse to preserve earlier evidence.
Prerequisites are the manifests, verified source/checkpoint, task scripts and
fixtures from this directory, plus the environment installed by `scripts/install.sh`.
Review available GPU resources before rerunning.

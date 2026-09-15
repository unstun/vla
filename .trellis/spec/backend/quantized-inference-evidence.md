# Quantized VLA inference evidence

## 1. Scope / Trigger

Use for pretrained low-bit deployment probes. The concrete reference is
`.pipeline/experiments/2026-09-08_navila_8b_quantized_5070ti`.
Quantization compatibility, action quality, simulator integration and full
artifact mirroring are separate outcomes.

## 2. Signatures

```bash
python scripts/prepare_workcopy.py PINNED_SOURCE EXPERIMENT
python scripts/make_package_manifest.py
python scripts/run_bounded.py UNIQUE_RUN_ID [--reload] [--limit N]
python scripts/analyze_run.py RUN_DIR --reload-run RELOAD_RUN_DIR
```

`probe.py` consumes `--model`, `--source`, `--fixtures`, `--output` and optional
`--export`. Requests are UTF-8 JSON cases with `instruction` and ordered `images`.

## 3. Contracts

- Pin source, checkpoint revision and original file SHA-256. Retain compatibility
  patches separately from the pristine source and verify source/input hashes.
- Label NF4 and AWQ separately. A paper's W4A16 measurement is not an NF4 result.
- For NF4, inspect actual `Linear4bit` layers, initialized `quant_state`,
  `quant_type`, compute dtype and device placement. A loading flag is insufficient.
- Preserve the model's image/history sampling, chat template and verbatim
  instruction. Explicitly label black padding and histories from other policies.
- Measure synchronized model time separately from loading, preprocessing,
  network transfer and total run time. Report allocation versus total GPU use,
  binary memory units, first-call warmup and workload context.
- Bound the child process, preserve stderr and record timeout/exit status.
- Export/reload verification compares actual output IDs for identical inputs.
  Record whether complete weight bytes, or only provenance/evidence, were mirrored.

## 4. Validation and error matrix

| Condition | Required outcome |
| --- | --- |
| Hash/size/range mismatch | Reject the artifact; do not disable verification |
| No actual quantized layers or unexpected CPU parameters | Reject the declared GPU-only four-bit claim |
| Dependency import or tiny random-model test succeeds | Dependency check only |
| Real pretrained model emits recorded actions | Open-loop inference evidence |
| Child crashes/times out, or output is missing | Retain failure; no passing-run claim |
| Repeated/reloaded output IDs differ | Report the discrepancy and investigate |
| Model fits, simulator not executed | No combined simulator-capacity claim |

## 5. Good / base / bad cases

- Good: full checkpoint loaded, real images tested, actual low-bit layers
  inspected, export reloaded, artifacts hashed locally, limits reported.
- Base: model-only inference works; deployment integration remains untested.
- Bad: a tiny NF4 matrix operation is presented as successful VLA deployment,
  or a replayed stop string is presented as the robot stopping accurately.

## 6. Required checks

Assert finite real CUDA outputs in dependency checks; for the full VLA assert
actual quantization state/device, nonempty outputs, repeated-input equality,
reload equality, successful child termination and artifact hashes. Inspect raw
actions against instructions separately; nonempty text is not task success.

For downloads on unreliable links, a socket read timeout is not a whole-request
deadline. The reference uses curl `--max-time` and low-speed limits for stalled
ranges, followed by complete LFS SHA-256 verification. Progress counters that
include resumed bytes must not be reported as fresh network throughput.

## 7. Wrong versus correct

Wrong: "8B four-bit needs 4 GB, so it fits alongside our simulator."
Correct: record actual full-VLA GPU use, including unquantized vision/projector,
embeddings, activations and runtime overhead; measure simulator coexistence.

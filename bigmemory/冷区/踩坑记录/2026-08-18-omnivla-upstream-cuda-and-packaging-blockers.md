---
origin: human_directed
reviewed: false
date: 2026-08-18
---

# OmniVLA Upstream Packaging And CUDA-Only Blockers

Two upstream defects at commit `5182600cb4a9ee07684e17cdd2a6cbafc56b8a68` block
the documented procedure. Both were hit during task
`08-18-omnivla-offline-smoke` and both root causes were verified by execution,
not inferred.

## Pitfall 1: `pyproject.toml` Is Not Valid TOML

### Symptom

The official `SETUP.md` command `pip install -e .` aborted before resolving any
dependency:

```
pip._vendor.tomli._parser.TOMLDecodeError: Unclosed array (at line 67, column 5)
```

### Verified Root Cause

`pyproject.toml` lines 66-67 are `"av"` followed by `"openai-clip"` with no
separating comma. Python would silently concatenate these into `"avopenai-clip"`,
but TOML has no implicit string concatenation, so the dependency array never
closes. This is platform-independent: the official setup command cannot succeed
on any machine at this commit.

### Fix

`patches/0001-upstream-pyproject-invalid-toml.patch` adds the comma. Afterwards
the full official dependency set resolved, including `tensorflow==2.15.0` via
`tensorflow-macos`, so the authors' intended dependency list is unchanged.

## Pitfall 2: `Tensor.get_device()` Returns `-1` On CPU

### Symptom

After the environment was built, the first inference attempt failed 85 s in:

```
  File "inference/model_omnivla_edge.py", line 272, in forward
    src_key_padding_mask = torch.index_select(self.all_masks.to(device), 0, no_goal_mask)
RuntimeError: Device index must not be negative
```

### Verified Root Cause

`model_omnivla_edge.py` line 241 sets `device = obs_img.get_device()`.
`Tensor.get_device()` returns the integer CUDA ordinal, and `-1` for CPU
tensors; `.to(-1)` is invalid. Line 49 has the same pattern
(`no_goal_mask.get_device()`). This is a CUDA-only assumption in upstream code,
not an environment misconfiguration — the entry point itself selects
`torch.device("cuda:0" if torch.cuda.is_available() else "cpu")`, so its own CPU
fallback path is unreachable.

### Fix

`patches/0004-edge-cpu-device-get-device-minus-one.patch` replaces both with
`Tensor.device`, which is device-agnostic and resolves to the same device on
CUDA. The next attempt exited 0 and produced the declared artifacts.

## Related, Not Yet Hit

`inference/run_omnivla.py` (the 8B path) has the same class of problem and was
confirmed by direct execution without loading the model:

- line 502 `torch.cuda.set_device(device_id)` raises
  `ValueError: Expected a cuda device, but got: cpu`;
- line 439 `torch.autocast("cuda", dtype=torch.bfloat16)` warns
  `User provided device_type of 'cuda', but CUDA is not available. Disabling`
  and silently computes in float32.

Anyone attempting the 8B model off CUDA must patch both deliberately rather than
discover them mid-run.

## Future Rule

When reproducing an upstream repository, treat the published setup command as
untested until it actually runs. Record the verbatim failure, fix it in a
numbered patch against a pristine snapshot, and never edit the snapshot in
place — otherwise the distinction between "upstream is broken" and "we changed
it" is lost. A CPU-only host is a useful filter: it surfaces hard-coded CUDA
assumptions that a GPU host would silently hide.

## Affected Paths

- `third_party/2026-08-18_omnivla_5182600/OmniVLA/pyproject.toml` (pristine, unedited)
- `third_party/2026-08-18_omnivla_5182600/OmniVLA/inference/model_omnivla_edge.py` (pristine, unedited)
- `.pipeline/experiments/2026-08-18_omnivla_offline_smoke/patches/0001-*.patch`
- `.pipeline/experiments/2026-08-18_omnivla_offline_smoke/patches/0004-*.patch`
- `.pipeline/experiments/2026-08-18_omnivla_offline_smoke/env/DEVIATIONS.md`

## Upstream Reporting

Not reported to `NHirose/OmniVLA`. Whether to open issues or a pull request is
Dr Sun's decision.

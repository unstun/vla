# Deviations from the official OmniVLA procedure

Every difference between the upstream instructions
(`third_party/2026-08-18_omnivla_5182600/OmniVLA/SETUP.md` and `README.md` at
commit `5182600cb4a9ee07684e17cdd2a6cbafc56b8a68`) and what was actually done on
this host, with the reason and the observed error that forced it.

Host: Apple M5, macOS 26.5.2, arm64, 32 GiB unified memory, **no CUDA device**.
Environment: conda env `omnivla`, python 3.10.20
(`/opt/homebrew/Caskroom/miniforge/base/envs/omnivla`). No pre-existing
environment was modified; `base` was not touched.

## Followed exactly (no deviation)

| Official step | Result |
|---|---|
| `conda create -n omnivla python=3.10 -y` | ok — python 3.10.20 |
| `pip3 install numpy==1.26.4 torch==2.2.0 torchvision==0.17.0 torchaudio==2.2.0` | ok — **all four official pins installed exactly**, arm64 wheels |
| `pip install packaging ninja` + `ninja --version` | ok — ninja 1.13.0 |
| `pip install -e .` (after D1 below) | ok — full official dependency set resolved, including `tensorflow==2.15.0` (satisfied by `tensorflow-macos==2.15.0`), `transformers` fork `git+https://github.com/moojink/transformers-openvla-oft.git@bc339d9ad707454c0c115970db43c260067c61ab` (4.40.1), `dlimp`, `timm==0.9.10`, `peft==0.11.1`, `tokenizers==0.19.1`, `diffusers==0.11.1`, `sentencepiece==0.1.99`, `huggingface_hub==0.29.1`, `openai-clip`, `efficientnet_pytorch`, `utm` |

No package was substituted or version-shifted to make the install pass. Full
resolved set: `pip_freeze.txt` (152 entries); conda form: `conda_env.yml`.

## D1 — upstream `pyproject.toml` is not valid TOML (blocking, patched)

Official command `pip install -e .` fails at the pinned commit on **every**
platform, not only macOS. `pyproject.toml` lines 66–67 are

```toml
    "av"
    "openai-clip"
```

with no separating comma. TOML has no implicit string concatenation (Python
does), so the array never closes. Verbatim error from the first attempt:

```
pip._vendor.tomli._parser.TOMLDecodeError: Unclosed array (at line 67, column 5)
```

Fix: `patches/0001-upstream-pyproject-invalid-toml.patch` adds the missing
comma — one character, applied to the working copy only. This is the minimal
change that lets the official command run at all; it does not alter the
dependency set the authors intended (`av` and `openai-clip` are both real
packages and both installed after the fix).

## D2 — `flash-attn==2.5.5` not installed (CUDA-only, skipped as planned)

Official command `pip install "flash-attn==2.5.5" --no-build-isolation` was run
and failed as expected. Verbatim tail:

```
  File ".../torch/utils/cpp_extension.py", line 2407, in _join_cuda_home
    raise OSError('CUDA_HOME environment variable is not set. '
OSError: CUDA_HOME environment variable is not set. Please set it to your CUDA install root.
error: metadata-generation-failed
```

SETUP.md marks Flash Attention 2 as "for training". The OmniVLA-edge inference
path (`inference/run_omnivla_edge.py` → `inference/model_omnivla_edge.py`,
EfficientNet-b0 + CLIP ViT-B/32) contains no FlashAttention call, so it is
unaffected. The 8B `inference/run_omnivla.py` path loads an OpenVLA/Prismatic
model whose remote code may request `flash_attention_2`; that is a real blocker
for the 8B probe on this host and is handled there, not here.

## D3 — `setuptools` installed explicitly (not in SETUP.md)

`import clip` failed on a fresh env:

```
  File ".../site-packages/clip/clip.py", line 6, in <module>
    from pkg_resources import packaging
ModuleNotFoundError: No module named 'pkg_resources'
```

`openai-clip==1.0.1` needs `pkg_resources` at import time. Current conda-forge
python 3.10 environments no longer ship `setuptools` by default, and pip builds
in isolation, so nothing pulled it in. Installed `setuptools==69.5.1` (a version
contemporary with the upstream pins, before the `pkg_resources` deprecation
cycle). This is an environment addition only; no source was changed.

## D4 — `timeout` replaced by a local shim (tooling, not behaviour)

`implement.md` requires a wall-clock `timeout` on every model process. macOS
ships no GNU coreutils `timeout` and none was installed on this host
(`which timeout gtimeout` → not found). `scripts/portable_timeout.pl` provides
the same contract: own process group, SIGTERM at the limit, SIGKILL 5 s later,
exit code 124 on timeout. Self-tested before first use (fast command → 0,
`cat /dev/zero` at 2 s → 124).

## D5 — env invoked by absolute interpreter path instead of `conda run`

`conda` is only a shell function on this host and the wrapper is not executable
in this non-interactive sandbox (`__conda_exe: permission denied`). Commands use
`/opt/homebrew/Caskroom/miniforge/base/bin/conda` for env management and
`/opt/homebrew/Caskroom/miniforge/base/envs/omnivla/bin/python` to run code.
This is equivalent to `conda activate omnivla` for a plain python process, and
it keeps stdout unbuffered and signals deliverable, which `conda run` does not.

## D6 — checkpoint directory provided as a symlink, not a copy

Upstream `run_omnivla_edge.py` hard-codes `MODEL_WEIGHTS_PATH = "./omnivla-edge"`
relative to the current working directory. Instead of patching that string, the
working copy gets a symlink `work/OmniVLA/omnivla-edge` →
`third_party/2026-08-18_omnivla_5182600/checkpoints/omnivla-edge` (created by
`scripts/make_workcopy.sh`). The upstream path string is untouched and the
weights stay in one tracked location.

## D7 — device is CPU (upstream's own fallback), not CUDA

`inference/run_omnivla_edge.py` selects
`torch.device("cuda:0" if torch.cuda.is_available() else "cpu")`. On this host
`torch.cuda.is_available()` is `False`, so upstream's own `cpu` branch is taken.
**No device patch was applied for the edge model** — the run follows the
upstream code path unmodified. `torch.backends.mps.is_available()` is `True` on
this host, but MPS is not what upstream selects, so it was not forced.

Consequence for the claim: the edge run is not the official CUDA/RTX-4090
environment. Numerics are float32 CPU. See the claim boundary in `README.md`.

## D8 — CLIP text-encoder weights relocated into the project

`inference/utils_policy.py` line 44 calls `clip.load(config["clip_type"])`
without a `download_root`, so OpenAI CLIP placed its 354 MB `ViT-B-32.pt` text
encoder in `~/.cache/clip/` on the first run — a research dependency living
outside the project, which `AGENTS.md` rule 8 does not allow.

Resolution (2026-08-19, after review):

- the file was **copied** (not moved) to
  `third_party/2026-08-18_omnivla_5182600/checkpoints/clip/ViT-B-32.pt`; the
  user's own cache was left untouched;
- its SHA-256 `40d365715913c9da98579312b702a82c18be219cc2a73407c4526f58eba950af`
  equals the digest OpenAI embeds in the download URL, which CLIP's own loader
  checks on every load, and is recorded in `CHECKPOINT_MANIFEST.tsv`
  (`license=mit`, https://github.com/openai/CLIP/blob/main/LICENSE) with a
  path-specific entry in the same dated `.gitignore` block;
- `patches/0005-edge-clip-download-root-in-project.patch` passes
  `download_root=os.environ.get("OMNIVLA_CLIP_ROOT")`, and `scripts/run_edge.sh`
  exports that variable. Upstream resolves `download_root or
  os.path.expanduser("~/.cache/clip")`, so with the variable set the home cache
  is never referenced, and with it unset behaviour is exactly upstream's.

Evidence that this changed nothing numerically: run
`runs/20260819T062802Z_edge_default_after_clip_relocation/` reproduced the
original default run with **max abs Δ = 0.0** over the raw `8×4` trajectory and
identical `(v, ω)`, and its `stdout.log` records the resolved path:

```
[local] clip download_root: '/Users/sun/tongbu/study/phdproject/vla/third_party/2026-08-18_omnivla_5182600/checkpoints/clip'
[local] clip weights resolved to: /Users/sun/tongbu/study/phdproject/vla/third_party/2026-08-18_omnivla_5182600/checkpoints/clip/ViT-B-32.pt
```

The run took 3 s, so no re-download happened; the hash-matching local copy was
used directly.

---
origin: human_directed
reviewed: false
as_of: 2026-08-19
---

# OmniVLA offline reproduction — evidence summary

Task: `.trellis/tasks/08-18-omnivla-offline-smoke`.
Executed 2026-08-18/19 on the local Mac. Nothing ran remotely.

**Strongest justified labels: `imported` for the OmniVLA source and both pinned
checkpoints' identity; `reproduced` for OmniVLA-edge only, in a
non-official environment. Not `integrated`, not `validated`, and no Lite3
statement of any kind.**

## 1. What actually ran

The official upstream entry point, unchanged in behaviour:

```bash
cd .pipeline/experiments/2026-08-18_omnivla_offline_smoke/work/OmniVLA
python inference/run_omnivla_edge.py
```

on the sample inputs shipped in the repository (`inference/current_img.jpg`,
`inference/goal_img.jpg`), with the official `omnivla-edge` checkpoint at its
pinned Hugging Face revision. Seven successful runs plus one recorded failure.
Each produced the upstream figure, a raw `8×4` trajectory, the metric-scaled
trajectory, and the `(v, ω)` command from upstream's own PD controller and
velocity limiter.

## 2. Evidence paths

| What | Path |
|---|---|
| Pinned source snapshot (tracked, pristine) | `third_party/2026-08-18_omnivla_5182600/OmniVLA/` |
| Provenance (URL, commit, tree, license, method) | `third_party/2026-08-18_omnivla_5182600/PROVENANCE.md` |
| Source integrity manifest (108 files) | `third_party/2026-08-18_omnivla_5182600/SOURCE_MANIFEST.sha256` |
| Checkpoint identities (both repos, pinned revisions) | `third_party/2026-08-18_omnivla_5182600/checkpoints/CHECKPOINT_MANIFEST.tsv` |
| Checkpoint download / regeneration | `third_party/2026-08-18_omnivla_5182600/checkpoints/README.md` |
| Pre-run decision log + appended results | `decision_log.md` |
| Environment record and every deviation | `env/` (`hardware.txt`, `install_log.txt`, `pip_freeze.txt`, `conda_env.yml`, `torch_probe.txt`, `DEVIATIONS.md`) |
| Patch series + rationale | `patches/` (`README.md`, `0001`–`0004`) |
| Scripts | `scripts/` (`make_workcopy.sh`, `mkpatch.sh`, `run_edge.sh`, `run_original_probe.sh`, `check_outputs.py`, `compare_runs.py`, `compare_reference_figure.py`, `verify_checkpoints.py`, `portable_timeout.pl`) |
| Runs (logs, figures, raw arrays, meta) | `runs/<UTC>_<tag>/` |
| Sweep table | `runs/comparison_table.md` |

## 3. Pinned identities

| Item | Value |
|---|---|
| Repository | https://github.com/NHirose/OmniVLA, MIT |
| Commit | `5182600cb4a9ee07684e17cdd2a6cbafc56b8a68` (tree `c2cdba2b3ca036684007fe4ab1c12ada73623cc5`, 2026-03-24, "Add publication") |
| Edge checkpoint | `NHirose/omnivla-edge` @ `b1361b7e24f101edea795a98b00a826b61a97394`, MIT — `omnivla-edge.pth`, 434,276,465 B, sha256 `f93b056f124380899fce3e087a5c2b41ce4d8c07e211daad52b6ebf02e80d04d` (downloaded, verified) |
| 8B checkpoint | `NHirose/omnivla-original` @ `e36a84d4923c041149d441f93f3bdb7092bb5f07`, MIT — 26 files, 15,998,670,997 B (manifest only, **not downloaded**) |
| CLIP text encoder | `ViT-B/32`, MIT (https://github.com/openai/CLIP/blob/main/LICENSE) — `third_party/2026-08-18_omnivla_5182600/checkpoints/clip/ViT-B-32.pt`, 353,976,522 B, sha256 `40d365715913c9da98579312b702a82c18be219cc2a73407c4526f58eba950af`, equal to the digest OpenAI embeds in the download URL and re-checked by CLIP's own loader on every load. Upstream pulls this at runtime into `~/.cache/clip`; patch 0005 redirects it into the project (deviation D8). |

## 4. Host and environment

Apple M5, macOS 26.5.2, arm64, 32 GiB unified memory, **no CUDA device**.
Conda env `omnivla`, python 3.10.20. The four official pins installed exactly:
`numpy==1.26.4`, `torch==2.2.0`, `torchvision==0.17.0`, `torchaudio==2.2.0`.
The full official `pip install -e .` dependency set resolved, including
`tensorflow==2.15.0` (via `tensorflow-macos`), the `transformers-openvla-oft`
fork at `bc339d9ad707454c0c115970db43c260067c61ab`, `timm==0.9.10`,
`peft==0.11.1`, `diffusers==0.11.1`, `openai-clip`, `efficientnet_pytorch`,
`utm`. No package was substituted or version-shifted.

Deviations (full detail with verbatim errors in `env/DEVIATIONS.md`):

1. **Upstream `pyproject.toml` is invalid TOML** — `"av"` on line 66 is missing
   its comma, so the official `pip install -e .` aborts with
   `TOMLDecodeError: Unclosed array (at line 67, column 5)`. This blocks the
   official setup command on *every* platform, not just macOS. Patch 0001.
2. **`flash-attn==2.5.5` not installed** — CUDA-only;
   `OSError: CUDA_HOME environment variable is not set`. SETUP.md marks it as
   for training, and the edge inference path never calls it.
3. **`setuptools==69.5.1` added** — `openai-clip` does
   `from pkg_resources import packaging` at import time and a fresh python 3.10
   env no longer ships setuptools.
4. `timeout` shim (macOS has no GNU coreutils), absolute interpreter path
   instead of the `conda` shell function, checkpoint provided as a symlink.
5. **Device is CPU** — upstream's own `else "cpu"` fallback. No device patch was
   applied to select it, and MPS was not forced.

## 5. Patches

`work/OmniVLA` = pristine snapshot + `patches/*.patch`; the rebuild was verified
byte-identical to the tree the runs used, and `diff -rq` against the pristine
tree shows only `pyproject.toml`, `inference/run_omnivla_edge.py`,
`inference/model_omnivla_edge.py` and the checkpoint symlink.

| Patch | Rationale |
|---|---|
| `0001-upstream-pyproject-invalid-toml` | one missing comma; without it the official install command cannot run at all |
| `0002-edge-dump-raw-outputs` | writes the raw `8×4` trajectory, metric trajectory and `(v, ω)` to JSON; upstream only renders a figure, which cannot be checked numerically. Pure sink, no computed quantity changes |
| `0003-edge-parameterise-prompt-and-modality` | reads the modality switches and prompt from the environment instead of hand-editing constants between runs (upstream README step 3). All defaults equal the upstream literals |
| `0004-edge-cpu-device-get-device-minus-one` | `Tensor.get_device()` returns `-1` on CPU and `.to(-1)` raises `RuntimeError: Device index must not be negative`; replaced with `Tensor.device`, identical on CUDA |
| `0005-edge-clip-download-root-in-project` | passes `download_root=$OMNIVLA_CLIP_ROOT` to `clip.load()` so the 354 MB CLIP text encoder lives inside the project instead of `~/.cache/clip` (`AGENTS.md` rule 8). `None` is `clip.load`'s own default, so unset = upstream behaviour; verified bit-identical (max abs Δ = 0.0) |

No patch touches a model, a weight, a normalisation, a controller gain, a
clipping bound, or the `metric_waypoint_spacing = 0.1` scale. Upstream issues
#26 (velocity clipping order) and #27 (trajectory scale) are left exactly as
written, so the numbers below are upstream's numbers.

## 6. Runs and sensitivity sweep

| run | modality | prompt | exit | wall s | peak RSS MiB | finite | shape | max abs Δ (all) | max abs Δ (x,y) | max abs Δ (heading) | endpoint shift m | v | ω | forward s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `default_lan_bluetrashbin` | 7 (language only) | `blue trash bin` | 0 | 5 | 3207.7 | True | (8, 4) | 0.0000 (baseline) | 0.0000 | 0.0000 | 0.0000 | 0.300000 | -0.121271 | 0.280 |
| `lan_turnleftdoor` | 7 (language only) | `turn left and go to the door` | 0 | 3 | 3254.8 | True | (8, 4) | 4.2927 | 4.2927 | 0.4179 | 0.4350 | 0.300000 | 0.128396 | 0.276 |
| `lan_stopdontmove` | 7 (language only) | `stop, do not move forward` | 0 | 4 | 3213.0 | True | (8, 4) | 1.9214 | 1.9214 | 0.1985 | 0.1997 | 0.300000 | -0.010896 | 0.317 |
| `goalimage_only` | 6 (image only) | `xxxx` | 0 | 4 | 3283.2 | True | (8, 4) | 4.6269 | 4.6269 | 0.8868 | 0.6150 | 0.262615 | 0.300000 | 0.261 |
| `pose_only` | 4 (pose only) | `xxxx` | 0 | 4 | 3239.8 | True | (8, 4) | 3.5357 | 3.5357 | 0.2413 | 0.3536 | 0.222376 | -0.300000 | 0.291 |
| `pose_and_lan` | 8 (language and pose) | `blue trash bin` | 0 | 4 | 3221.1 | True | (8, 4) | 1.9872 | 1.9872 | 0.2991 | 0.2111 | 0.186486 | -0.300000 | 0.267 |

Plus `20260819T061759Z_edge_default_repeat_determinism` (exit 0, 4 s,
3154.5 MiB), a repeat of the default configuration whose trajectory is
**bit-identical** to the baseline (max abs difference exactly 0.0). Inference is
deterministic here, so every delta above is caused by the input change.

A final end-to-end check (`20260819T062252Z_edge_reproducibility_check`) rebuilt `work/OmniVLA` from the tracked
pristine snapshot plus the tracked patch series and re-ran the entry point: the
trajectory and `(v, ω)` are bit-identical to the baseline, so the recorded
artifacts alone are sufficient to regenerate the result.

### Comparison against the authors' shipped reference figure

The pinned tree ships `inference/1_ex_omnivla_edge.jpg`: the authors' own
rendered output for exactly the default configuration this task runs. Comparing
it with the default run's figure (both 2720x1280,
`scripts/compare_reference_figure.py`, numbers in
`runs/20260819T061614Z_edge_default_lan_bluetrashbin/reference_figure_comparison.txt`,
heat-map `reference_figure_diff.png`):

| Region | mean abs pixel difference | max | pixels differing > 16 |
|---|---|---|---|
| whole image | 0.0208 / 255 | 227 | 0.0448 % |
| trajectory panel (right half) | 0.0415 / 255 | 227 | 0.0896 % |

All 1,559 differing pixels (of 3,481,600) fall in the right half, inside the
bounding box x 1984-2285, y 153-765 — that is, on the drawn trajectory curve
itself. The two camera-image panels are pixel-identical, as expected since they
render the same input JPEGs.

Reading this honestly: the local CPU run reproduces the authors' published
figure for this configuration to a close **visual** match — the trajectory lies
essentially on top of theirs. It is not a numeric trajectory match, because
upstream ships no reference arrays; the residual differences are confined to the
curve's own anti-aliased pixels and cannot be separated into "matplotlib
version/renderer drift" versus "small CPU-vs-CUDA numeric offset" from this
evidence alone.

And one recorded failure:
`20260819T061412Z_edge_default_lan_bluetrashbin_failed_get_device` (exit 1,
85 s) — the `get_device()` bug described above, kept because it is evidence.

Every successful run passed `scripts/check_outputs.py`: shape `(8, 4)`, all
finite, `v ∈ [0, 0.5]` and `ω ∈ [-1, 1]` after the PD clip, `|v| ≤ 0.3` and
`|ω| ≤ 0.3` after the limiter, unit-norm heading components, figure > 10 KB,
exit 0.

### Observation on language sensitivity

On this single sample image the language pathway is not inert: swapping the
prompt moves the trajectory endpoint by up to 0.435 m and flips the commanded
yaw rate sign. That is one image and three prompts — it does not resolve
upstream issue #28 in either direction, and it is not an evaluation. Worth
flagging for later Lite3 work: commanded linear velocity stayed pinned at the
0.3 m/s limiter ceiling for **all** language prompts, including
`"stop, do not move forward"`. This model, in this configuration, has no stop
behaviour; a Lite3 safety layer must not inherit that assumption.

## 7. 8B model: not probed

The probe stopped at a guard that was written down before any run: available
memory 17.27 GB against a required 22 GB (`runs/20260819T061936Z_original_probe_skipped/`).
The guard was not relaxed, and the 14.90 GiB of weights were therefore not
downloaded. Confirmed by direct execution for whoever picks this up on a GPU
host: `inference/run_omnivla.py` line 502 calls `torch.cuda.set_device()`
unconditionally (`ValueError: Expected a cuda device, but got: cpu`), and line
439 uses `torch.autocast("cuda", …)` which silently degrades to float32 off
CUDA. FlashAttention is probably not a blocker: the pinned `config.json` sets
no `_attn_implementation`.

## 8. Resource usage

| Item | Value |
|---|---|
| Peak RSS per edge run | 3.15–3.28 GiB |
| Forward pass | 0.26–0.32 s (CPU) |
| Wall per run | 3–5 s (first run 85 s including the one-time CLIP download) |
| Tracked bytes added | `OmniVLA/` 1.3 MB, `runs/` 1.0 MB |
| Local-only bytes (git-ignored, manifested) | `checkpoints/omnivla-edge/` 416 MB, `checkpoints/clip/` 338 MB, `work/` 1.4 MB |
| Outside the repository | none — the pre-existing `~/.cache/clip/` copy was left alone but is no longer what the runs read |

## 9. Claim boundary

This work establishes:

- `imported` — a pinned, hash-verified OmniVLA source snapshot and pinned
  checkpoint identities exist in this repository;
- `reproduced` — **OmniVLA-edge only**, on macOS arm64 / CPU / float32 / no
  FlashAttention, with patches 0001–0004, on the sample inputs shipped upstream.

This work does **not** establish:

- anything about the 8B `omnivla-original` model beyond its recorded identity;
- the official CUDA reproduction — blocked until Dr Sun designates a GPU host
  (≥ 20 GB VRAM per upstream guidance);
- any accuracy, success-rate, or benchmark claim — one sample forward pass is
  not an evaluation, and no number from the paper is reproduced here. The
  figure comparison in §6 is a visual match against the authors' shipped
  rendering for one configuration, which is corroborating evidence for the
  reproduction, not a metric;
- `integrated` or `validated` in the `AGENTS.md` sense;
- anything about Lite3. No camera calibration, no action interface, no
  navigation or locomotion integration, no robot command was produced or sent.
  The `(v, ω)` values above are numbers in a JSON file.

## 10. Next gates

1. Review this evidence bundle and the patch series; decide whether the
   `reproduced` (non-official-environment) label for edge is accepted.
2. Designate a CUDA host if the 8B model matters; it needs a device patch for
   `run_omnivla.py` line 502 plus a decision about the `autocast("cuda")` path.
3. Only afterwards: a broader prompt/image sensitivity study, and separately the
   Lite3 interface contract (camera, goal, trajectory sanitiser, command bridge,
   safety supervisor) as required by
   `.trellis/spec/backend/quality-guidelines.md` §4.

## 11. Open problems

1. **No numeric reference.** Upstream ships a rendered reference figure but no
   trajectory arrays, so the check in §6 is visual. It is a close match (all
   differences confined to the drawn curve's own pixels, 0.045 % of the image),
   which is meaningful corroboration, but it cannot prove the CPU float32 result
   is numerically equal to a CUDA run, and it cannot attribute the residual
   difference between renderer drift and a small numeric offset.
2. **One image only.** The sweep varies prompt and goal modality on a single
   sample image. The survey (`§7.7`) asks for three image sets; that is not
   done and is out of this task's declared scope.
3. **Uncovered modality combinations.** Upstream's `if/elif` chain in
   `run_forward_pass` does not cover every combination of the four switches
   (for example pose+satellite+image+language), which would leave `modality_id`
   unbound and raise `UnboundLocalError`. Only covered combinations were used.
   The gap is unpatched and not reported upstream.
4. **MPS untested.** `torch.backends.mps.is_available()` is True on this host,
   but every run used CPU (upstream's own fallback). No MPS numbers exist.
5. **The 8B path is essentially untested** beyond two isolated API calls; see §7.
6. **Upstream bugs not reported upstream.** The invalid `pyproject.toml` and the
   `get_device()` CPU failure are fixed locally in `patches/` only. Whether to
   open issues or a pull request against `NHirose/OmniVLA` is Dr Sun's call.

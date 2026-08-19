# Patch series against the pinned OmniVLA snapshot

Base: `third_party/2026-08-18_omnivla_5182600/OmniVLA/` (upstream
`5182600cb4a9ee07684e17cdd2a6cbafc56b8a68`, tree
`c2cdba2b3ca036684007fe4ab1c12ada73623cc5`). The base tree is never edited.
`scripts/make_workcopy.sh` rebuilds `work/OmniVLA` as *base + these patches, in
numeric order*, and that rebuild was verified byte-identical to the tree the
runs used.

Apply/verify:

```bash
bash .pipeline/experiments/2026-08-18_omnivla_offline_smoke/scripts/make_workcopy.sh
diff -rq third_party/2026-08-18_omnivla_5182600/OmniVLA \
         .pipeline/experiments/2026-08-18_omnivla_offline_smoke/work/OmniVLA
# expected: only pyproject.toml, inference/run_omnivla_edge.py, and the
# ./omnivla-edge checkpoint symlink differ
```

| Patch | File / upstream lines | Purpose | Why unavoidable |
|---|---|---|---|
| `0001-upstream-pyproject-invalid-toml.patch` | `pyproject.toml` 66–67 | adds the missing comma after `"av"` | **Blocking upstream bug.** TOML has no implicit string concatenation, so the dependency array never closes and the official `pip install -e .` aborts with `TOMLDecodeError: Unclosed array (at line 67, column 5)` on any platform. One character; the intended dependency set is unchanged (`av` and `openai-clip` both install afterwards). |
| `0002-edge-dump-raw-outputs.patch` | `inference/run_omnivla_edge.py` — new `dump_run_artifacts()` after `count_parameters`; two timing lines around `run_forward_pass`; a call before `return` in `run_omnivla()` | writes the raw `8×4` trajectory, the metric-scaled trajectory, the chosen waypoint, `(v, ω)` before and after the velocity limiter, modality id, dtype and forward time to `outputs.json` | Upstream only renders a matplotlib figure and prints; neither can be checked numerically, and AC5/AC6 require the raw arrays. The `__main__` block cannot be imported and reused as a function (design.md §3 allows a patch in exactly this case). The helper is a pure sink: it reads already-computed values, computes no model quantity, and is a no-op unless `OMNIVLA_RUN_DIR` is set. |
| `0003-edge-parameterise-prompt-and-modality.patch` | `inference/run_omnivla_edge.py` `__main__` (upstream lines ~493–496, ~505, ~559) | reads the four modality switches and the language prompt from environment variables, and sends the output figure to the run directory | Upstream's documented way to change modality is to hand-edit these constants (README step 3: "modify the settings around line 425"). The sweep needs several configurations without editing the file between runs. **Every default equals the upstream literal**, so an unset environment reproduces upstream behaviour exactly; the redirected `save_dir` only prevents runs from overwriting each other's figure. |
| `0005-edge-clip-download-root-in-project.patch` | `inference/utils_policy.py` line 44 (`load_model`) | passes `download_root=os.environ.get("OMNIVLA_CLIP_ROOT")` to `clip.load()` and prints the resolved path | Upstream calls `clip.load("ViT-B/32")` with no `download_root`, so CLIP writes 354 MB of weights to `~/.cache/clip`, outside the project, against `AGENTS.md` rule 8. `download_root=None` is `clip.load`'s own default (`_download(url, download_root or os.path.expanduser("~/.cache/clip"))`), so an unset `OMNIVLA_CLIP_ROOT` reproduces upstream byte for byte. Verified: re-running the default configuration with the project root gave a bit-identical trajectory (max abs Δ = 0.0). |

No patch changes a model, a weight, a normalisation, a controller gain, a
clipping bound, or a device selection. In particular the disputed velocity
clipping order (upstream issue #26) and the `metric_waypoint_spacing = 0.1`
scale (issue #27) are left exactly as upstream wrote them, so the recorded
numbers are upstream's numbers.

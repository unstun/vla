# OmniVLA checkpoints — pinned provenance

Recorded for task `.trellis/tasks/08-18-omnivla-offline-smoke` on 2026-08-18.

Weight bytes are **local-only**. They are excluded by a dated, path-specific
`.gitignore` block (repository root, "2026-08-18 OmniVLA offline reproduction
bytes"). Their identity is tracked here and in `CHECKPOINT_MANIFEST.tsv`
(repo, revision, file, size, sha256, sha256 kind, license, source, verified,
local path), so the bytes are reconstructible without being committed.

## Pinned revisions

| Repo | Revision | Files | Total size | License (HF `cardData`) | Local state |
|---|---|---|---|---|---|
| `NHirose/omnivla-edge` | `b1361b7e24f101edea795a98b00a826b61a97394` | 3 | 434,278,008 B (0.40 GiB) | `mit` | downloaded, all 3 files hash-verified |
| `NHirose/omnivla-original` | `e36a84d4923c041149d441f93f3bdb7092bb5f07` | 26 | 15,998,670,997 B (14.90 GiB) | `mit` | manifest only — see "original" below |

Both revisions were read from the Hugging Face model API on 2026-08-18:

```bash
curl -sS -L "https://huggingface.co/api/models/NHirose/omnivla-edge/revision/b1361b7e24f101edea795a98b00a826b61a97394?blobs=true"
curl -sS -L "https://huggingface.co/api/models/NHirose/omnivla-original/revision/e36a84d4923c041149d441f93f3bdb7092bb5f07?blobs=true"
```

`sha256_kind` in the manifest distinguishes the two identifiers the API
returns: `lfs-sha256` is the true SHA-256 of the file content (LFS-tracked
weights); `git-blob-sha1` is the Git blob SHA-1 that HF reports for small
non-LFS files, verifiable locally with `git hash-object <file>`.

## Regeneration — edge (required by this task)

Actually used (deterministic, pinned revision in the URL, no extra dependency):

```bash
REV=b1361b7e24f101edea795a98b00a826b61a97394
DST=third_party/2026-08-18_omnivla_5182600/checkpoints/omnivla-edge
mkdir -p "$DST"
for f in README.md .gitattributes omnivla-edge.pth; do
  curl -sS -L --fail "https://huggingface.co/NHirose/omnivla-edge/resolve/$REV/$f" -o "$DST/$f"
done
shasum -a 256 "$DST/omnivla-edge.pth"
# must print f93b056f124380899fce3e087a5c2b41ce4d8c07e211daad52b6ebf02e80d04d
```

Equivalent Python form (design.md's preferred form; same revision, same bytes):

```python
from huggingface_hub import snapshot_download
snapshot_download("NHirose/omnivla-edge",
                  revision="b1361b7e24f101edea795a98b00a826b61a97394",
                  local_dir="third_party/2026-08-18_omnivla_5182600/checkpoints/omnivla-edge")
```

Upstream `README.md` gives the unpinned form `git clone
https://huggingface.co/NHirose/omnivla-edge`; a pinned revision is mandatory
here, so the plain clone is not used.

Verified locally on 2026-08-18: `omnivla-edge.pth`, 434,276,465 B,
SHA-256 `f93b056f124380899fce3e087a5c2b41ce4d8c07e211daad52b6ebf02e80d04d`,
equal to the LFS oid at the pinned revision. On-disk directory size 416 MB.

## Regeneration — original (8B, manifest tracked; download optional)

```python
from huggingface_hub import snapshot_download
snapshot_download("NHirose/omnivla-original",
                  revision="e36a84d4923c041149d441f93f3bdb7092bb5f07",
                  local_dir="third_party/2026-08-18_omnivla_5182600/checkpoints/omnivla-original")
```

Content at the pinned revision: 4 `model-0000N-of-00004.safetensors` shards
(≈14.06 GiB total), `action_head--120000_checkpoint.pt`,
`dist_head--120000_checkpoint.pt`, `proprio_projector--120000_checkpoint.pt`,
`lora_adapter/adapter_model.safetensors`, tokenizer/processor/config files, and
two `modeling_prismatic*.py` files (`custom_code` tag — the model loads with
`trust_remote_code=True`, so the code that executes is the code in this pinned
revision).

`verified=no` rows in `CHECKPOINT_MANIFEST.tsv` mean "identity recorded from the
HF API at the pinned revision, bytes not present locally". They must not be read
as a local integrity check.

## CLIP ViT-B/32 (third dependency, pulled at runtime by upstream code)

`inference/utils_policy.py` line 44 calls `clip.load(config["clip_type"])` with
`clip_type = "ViT-B/32"` and no `download_root`, so OpenAI CLIP downloads its
text encoder to `~/.cache/clip/` the first time the edge script runs. That put a
354 MB research dependency outside the project, against `AGENTS.md` rule 8, so
the file now also lives here:

| Field | Value |
|---|---|
| Local path | `checkpoints/clip/ViT-B-32.pt` |
| Size | 353,976,522 B |
| SHA-256 | `40d365715913c9da98579312b702a82c18be219cc2a73407c4526f58eba950af` |
| Source | https://openaipublic.azureedge.net/clip/models/40d365715913c9da98579312b702a82c18be219cc2a73407c4526f58eba950af/ViT-B-32.pt |
| License | MIT — https://github.com/openai/CLIP/blob/main/LICENSE |
| Verified | yes |

OpenAI's own loader embeds the expected SHA-256 in the download URL and checks
it on every load (`clip/clip.py::_download`), so this identifier is upstream's
own integrity check rather than one this project invented. The local copy's
hash matches it.

Regeneration:

```bash
DST=third_party/2026-08-18_omnivla_5182600/checkpoints/clip
mkdir -p "$DST"
curl -sS -L --fail \
  "https://openaipublic.azureedge.net/clip/models/40d365715913c9da98579312b702a82c18be219cc2a73407c4526f58eba950af/ViT-B-32.pt" \
  -o "$DST/ViT-B-32.pt"
shasum -a 256 "$DST/ViT-B-32.pt"
# must print 40d365715913c9da98579312b702a82c18be219cc2a73407c4526f58eba950af
```

Runs point CLIP at this copy through `OMNIVLA_CLIP_ROOT` (patch 0005); with the
variable unset the upstream default cache path is used unchanged. Because the
file is already present and its hash matches, loading it performs no network
access. The pre-existing `~/.cache/clip/` copy was left untouched — it belongs
to the user, not to this task.

## Safety note

`.pth`/`.pt` files are Python pickles. Only load them from the pinned official
revisions recorded above.

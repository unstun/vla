# v51 artifact pipeline

Storage/rendering version only. Renderer parent: frozen v46. Navigation reference
remains v48; no planner, controller, sensor rate, dynamics or stop changes.

## Default entry point

For new bounded recordings and renders, use `scripts/run_managed.py` with the
same child command previously passed to `scripts/run_bounded.py`. Existing
frozen launchers remain available for historical reproduction; they do not
automatically adopt this policy. Do not wrap an entire launcher that itself
creates the same run directory: use its recorded child command, retaining its
normal source/build preflight. A current VLA agent should use this entry point
when preparing future runs, then perform the existing artifact-return gate.

From the experiment directory:

```sh
python scripts/run_managed.py --run-id NEW_RUN --deadline 180 -- CHILD_COMMAND ...
```

The default `auto` policy checks at least4 GiB free before launching and runs
retention only after the bounded supervisor exits. This is a preflight reserve,
not a guarantee for arbitrary-duration captures. It never changes planner stop
semantics or introduces an in-loop storage cleanup. Successful macOS recordings
use transparent closed-log compression, preserving original paths and bytes.
Explicit process/terminal failures use lossless ZIP archives. Other hosts use
portable ZIP archival. `--retention archive` requests archival even for a
successful process; `--retention compatible` retains expanded paths on macOS.
An interrupted manager leaves an active marker for inspection, preventing cleanup.
No completion evidence means retain the outputs. Child failure exit codes survive
successful archival. A retention failure is separately reported and retains
originals or an already verified archive.

## Render directly from a recorded run

Use the existing Newton environment with `render_heading_v51.py` (or
`render_episode_v51.py` for the original camera), through the managed entry point.

```sh
python scripts/run_managed.py --run-id NEW_VIDEO --deadline 900 -- \
  ../2026-09-26_newton_macos_policy/runtime/.venv/bin/python \
  versions/v51/render_heading_v51.py --source-run ORIGINAL_RUN
```

Recorded navigation wall timestamps define the30 FPS causal replay. Untimed
factory-startup prefixes are omitted from this initialized-navigation view;
their original records remain. Missing timestamps inside navigation are errors.
The renderer reads original data without a duplicate `view` run and streams
RGB24 frames to FFmpeg. It retains three preview PNGs, compact frame provenance,
and the MP4. Full decode and frame-count/fps validation precede final acceptance.
`--keep-frames` on the renderer explicitly retains every PNG for debugging.
The writer has a512 MiB video cap and checks a disk reserve as it renders;
failure preserves the partial MP4/provenance and never labels it complete.

The backend log is read line by line and reduced in memory to the status fields
actually drawn. Full historical snapshots remain in the original log/archive.
Physics and sensor capture are not executed by rendering.

## Existing outputs and restoration

```sh
python versions/v51/artifacts.py prune-frames --run EXISTING_VIDEO --apply
python versions/v51/artifacts.py compress-logs --run CLOSED_RUN --apply
python versions/v51/artifacts.py pack-raw --run CLOSED_FAILED_RUN --apply
python versions/v51/artifacts.py verify-archive --run CLOSED_FAILED_RUN
python versions/v51/artifacts.py restore --run CLOSED_FAILED_RUN --apply
```

Pruning requires the original MP4 hash, source-state hash, every PNG hash,
matching frame count/fps, full video decode and no active writer. Existing MP4s,
original frame manifests and three exact preview images remain. MP4 is lossy:
this intentionally removes redundant derived PNGs, not a lossless PNG archive.

`raw_capture.zip` stores original NPZ bytes without recompressing them; NPZ is
already compressed. Large JSONL/log members use ZIP LZMA. The external
`raw_capture_manifest.json` records original paths, hashes, sizes, modes and
mtimes, plus archive identity. Every member is read and verified before expanded
files are removed. Restore refuses changed existing files and checks free space.
**Legacy readers requiring original expanded paths need restoration first.**
v51 display readers can read archived text directly. Failure data has not been
discarded or reclassified. Portable ZIP archival was exercised locally; no new
remote physics or Linux managed-run integration is claimed.

Audit: `audits/2026-10-01_artifact_storage/operations.jsonl` records each change.
`verify_storage.py` verifies hashes against original manifests and archives.
Frozen native/source fixtures are ineligible for archival. Metadata that cannot
be preserved by transparent compression causes a skip, never a relaxed check.

## Validation

21 focused tests cover corrupt/mismatched/incomplete video, active runs, symlinks,
source mutation, byte-exact compression, ZIP round-trip/failure handling, changed
restore destinations, causal timestamp selection, and streaming interruption.
Real recorded-state smokes use the existing Mac graphics runtime and zero physics
steps. The first preserved-frame RGB comparison is exact. A failed-child smoke
checks automatic archival and exit-code preservation. See RESULTS.md.

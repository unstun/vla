# v34 video preparation

Prepared on 2026-09-29 (America/Los_Angeles). Stage: experiment and analysis.
This package prepares the existing recorded-state renderers. It does not start
physics, change v34, or stand in for its independent review or freeze.

## Current readiness

The local rendering environment imports NumPy, Newton, Warp, Pillow, OpenUSD
and Trimesh. Scene input hashes verify. The four standard renderer/scene files
and the heading wrapper match the bytes executed for v33. FFmpeg and FFprobe
are available. See `preflight.json` for measured results. No GL frame was
rendered by this preparation check.

There is no v34 physical run yet. Its independent review and frozen manifest
are also absent. Before generating v34 footage:

1. Pass K5 and freeze under `versions/v34/PLAN.md` and `freeze.py`.
2. Sync and verify the execution copy, then execute the single trial under
   `versions/v34/PHYSICAL_RUN_PLAN.md` and `HOST_NOTE_gpu5070ti.md`.
3. Return the trial and host records to the same local paths, and verify every
   returned file against the runner's `<run>_SHA256SUMS.txt`. A failed route
   remains a valid source for a video of that failure; preserve its outcome.

Do not use component replay states or another version's states as v34 footage.

## Render commands after the verified return

Use the actual physical run ID. A pre-physics infrastructure retry uses the
next ID specified by the run plan. Both output run IDs must be new.

```bash
export VLA_VIDEO_BASE=/Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction
export VLA_VIDEO_RUN=v34_historical_full01
VLA_VIDEO_PY=/Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-26_newton_macos_policy/runtime/.venv/bin/python
cd "$VLA_VIDEO_BASE"

"$VLA_VIDEO_PY" - <<'PY'
import json, os, re
from pathlib import Path
base = Path(os.environ['VLA_VIDEO_BASE'])
run = os.environ['VLA_VIDEO_RUN']
assert re.fullmatch(r'v34_historical_full0[1-9]', run), run
source = base / 'runs' / run
assert (base / 'versions/v34/manifest.json').is_file(), 'v34 is not frozen'
request = json.loads((source / 'episode_request.json').read_text())
assert request['integration_version'] == 'v34'
assert request['scene'] == 'building_full'
assert (source / 'result.json').is_file(), 'the run has no final result record'
states = json.loads((source / 'video_states.json').read_text())
assert states and all('joint_q' in row and 'physics_time_s' in row for row in states)
for suffix in ('_video01', '_video02'):
    assert not (base / 'runs' / (run + suffix)).exists(), 'use a new render run ID'
print(f'{run}: {len(states)} recorded frames; v34 Building render inputs present')
PY

"$VLA_VIDEO_PY" scripts/run_bounded.py --run-id "${VLA_VIDEO_RUN}_video01" --deadline 1800 -- \
  "$VLA_VIDEO_PY" scripts/render_episode.py --source-run "$VLA_VIDEO_RUN"

"$VLA_VIDEO_PY" scripts/run_bounded.py --run-id "${VLA_VIDEO_RUN}_video02" --deadline 1800 -- \
  "$VLA_VIDEO_PY" scripts/render_heading_view.py --source-run "$VLA_VIDEO_RUN"
```

These commands follow v33's recorded render requests. Each render reads the
physical run's immutable states and writes a separate output directory. The
second view changes only the display camera. Encoding is H.264, 1280×720,
12.5 FPS, using the unchanged renderer.

## Verification and delivery

For each view, require the bounded process to finish successfully and its
`result.json` to name the actual source run and `integration_version=v34`,
report `render_only_no_physics_steps=true`, and match the source-state hash.
Compare the source-state SHA-256 before and after rendering. Decode the whole
MP4, then inspect frames covering startup, stairs, the corridor entry, the
farthest progress and the final outcome. The standard and heading views must
show the same physical timeline and outcome.

```bash
ffmpeg -nostdin -v error -i "runs/${VLA_VIDEO_RUN}_video01/newton_stair_recorded.mp4" -f null -
ffmpeg -nostdin -v error -i "runs/${VLA_VIDEO_RUN}_video02/newton_stair_recorded.mp4" -f null -
```

After verification, copy the ordinary MP4 files to
`output/2026-09-27_lite3_versions/`, named with the actual v34 run ID and view.
Record source/render run IDs, physical outcome, video/frame hashes, resolution,
FPS, full-decode result and inspected frames in a new video receipt. Deliver
the two absolute file links. Raw frames and captures remain in the project;
any local-only ignore entry needs path-specific provenance under the existing
artifact policy.

The footage will be a replay visualization of actual logged physics, with
its navigation outcome retained. Rendering is not an additional navigation
trial or evidence of real-time rendering.

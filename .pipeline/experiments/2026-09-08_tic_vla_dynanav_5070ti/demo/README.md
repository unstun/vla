# Local voice to simulation video

Current result: direct Chinese text reaches the model unchanged, but the first
tested Chinese navigation episode failed to reach the goal and reported a
collision. See [the recorded outcome and scope](RESULT.md#direct-chinese-input--navigation-failed).
The later [matched full-instruction pair](paired_language_2026-09-08/RESULT.md)
also recorded Chinese failure and English success under the same configured
conditions and seeds; it remains a one-pair exploratory result.

The current user-approved interface is `录音并生成视频.command`. It opens a
terminal, waits for Enter, counts down, records six seconds from the Mac's
default microphone, transcribes on the Mac CPU and runs one remote hospital
episode. No website, HTTP server, SSH video forwarding or live image streaming
is started by this entrypoint. The older `启动演示.command` redirects here.

For the first trial, say **走到自动售货机前**. The recognized Chinese command is
now passed verbatim to TIC-VLA; no English substitution or translation is applied. Other
destinations are rejected instead of silently substituting this goal. An offline
batch has no interactive stop/resume commands. It ends at the original 1.5 m goal
threshold, the 70-second frame-derived scenario limit, an upstream error or its
600-second wall deadline. Offline startup waits for frame 120 and nonempty front
and third-person camera buffers before issuing the goal.

macOS may request microphone access for Terminal/Python on first use. The input
device was enumerated as `MacBook Pro Microphone`, 48000 Hz; enumerating the
device is not a human recording test. Audio is not uploaded. The local request
record contains its SHA-256, recognized text, source kind and video path.

## Existing recording / repeatable validation

```bash
demo/.venv/bin/python demo/scripts/voice_to_video.py --audio RECORDING.wav
```

For direct Chinese text without microphone/ASR:

```bash
demo/.venv/bin/python demo/scripts/voice_to_video.py --instruction '走到自动售货机前' --view top_down
```

The UTF-8 request is transferred as a JSON file. Offline execution requires that
request and writes a per-run `hospital_demo.yaml`; its instruction is also logged
at every model call. Missing requests fail instead of falling back to English.
The existing goal vocabulary still limits this demo's destination, but recognized
wording and punctuation are preserved after outer whitespace is trimmed.
`--inference-seed 36` optionally resets inference RNGs at the first offline goal
for paired trials. It does not guarantee bitwise deterministic simulator output.

Add `--view top_down` for a fixed overhead scene recording. The output camera
is orthographic, with a 20x11.25 m footprint centered at `(4,0.5)`. Its near clip
removes ceiling obstruction from this camera view; scene geometry and the model's
front camera remain unchanged. This creates a new episode, not a reconstruction
of a previous clip. `third_person` remains the default recording mode.
The camera's aperture and clipping units follow the
[official OpenUSD camera contract](https://openusd.org/release/api/class_usd_geom_camera.html).

The validation fixture was generated locally with macOS `say -v Tingting` and
must be labeled with `--synthetic`; it is not Dr Sun's voice. The finished MP4 is
saved under `demo/runs/RUN_ID/navigation_with_trajectory.mp4`, SHA-256 verified,
and opened locally. Transfer retries retain partial files. The remote run is
detached and bounded independently from the SSH connection.

Video annotations: cyan is the current predicted trajectory; orange is the
driven path. Projection uses body/FLU coordinates and the third-person camera
matrix. The overlay does not perform depth occlusion and never changes the
front-camera images used by the model. Video timing follows actual wall
timestamps. Only the initial stationary wait may be trimmed, with its duration
recorded in `analysis.json`.

## Rebuild and provenance

1. Install `requirements.txt` into `demo/.venv` with Python 3.12 on the Mac.
2. `prepare_asr.py` obtains the exact model revision from
   `manifests/asr_upstream.json`, verifies upstream Git/LFS identities, and writes
   `manifests/asr_assets.json`. Model source: SenseVoice via the sherpa-onnx
   maintainer's ONNX conversion, revision
   `2365baeacb507f821a0c8120fcee3d484dba7a07`. The int8 ONNX file is
   239233841 bytes, SHA-256
   `c71f0ce00bec95b07744e116345e33d8cbbe08cef896382cf907bf4b51a2cd51`.
   The pinned LICENSE file points to FunASR's model license terms; the conversion
   repository license must not be described as the model license.
3. `prepare_demo.py` verifies the earlier successful 44-file source snapshot and
   creates a separate work copy, patch and source manifest. The pretrained VLA
   and Isaac runtime are reused from the parent experiment, without modifying
   the original successful work copy.
4. Sync `scripts/`, `web/` (historical only), `work/`, `hospital_demo.yaml` and
   `manifests/source.json` to the same paths under
   `gpu5070ti:/home/sun/vla_exec/2026-09-08_tic_vla_dynanav_5070ti/demo/`.
   Exclude only root `/models/`, never all directories named `models` because
   `work/ticvla/models/` is required source.
5. `launch_batch.sh` checks the complete source manifest before launch.
   `batch_worker.py` runs offline inference and `collect_demo.py` packages the
   video, raw overlay-frame archive, metrics and checksums. The local launcher
   downloads and verifies all packaged evidence. Raw individual frames remain
   recoverable from the locally downloaded archive.

The `web/`, `server.py`, `tunnel.py` and online command exercise are retained as
an abandoned exploratory prototype. Its browser synthetic-microphone path did
not pass: Chrome delivered near-zero samples. HTTP upload of the same synthetic
audio passed CPU recognition. Its first online run consumed real VLA outputs,
but stop/resume validation was interrupted by transport failures. These are not
claims about the final local microphone implementation.

# TIC-VLA Orin pretrained receive-only compatibility result

## Outcome

The bounded compatibility run passed on the real Jetson AGX Orin CUDA device.
It loaded the pinned TIC-VLA source, the official InternVL3-1B base model, and
the official TIC-VLA checkpoint; performed one warm-up and three serial
measured forwards; and returned finite waypoint tensors with the source-derived
shape `(1, 30, 2)`.

This is not a paper reproduction or a navigation/safety result. The input was
one offline Lite3 image rather than a DynaNav sample. The delayed and current
frames repeated that same image, while robot state, ego-motion, and delay used
neutral placeholders.

## Identities

- TIC-VLA source: `https://github.com/ucla-mobility/TIC-VLA`
- Source commit: `9fa6f8b66b9e121d5df5df071297bba8e5353ebb`
- License: UCLA Academic Software License; local license SHA-256
  `1949b03d5d1d93c51ac2c22c1ec13b926aea4d56b84477e930a942316c497e15`
- Base model: `OpenGVLab/InternVL3-1B` revision
  `4415a3b810e636d11dfa86b0e9ba40bb00535aa8`
- Checkpoint: `handsomeYun/TIC-VLA`, dataset revision
  `671de608f39ccae41b66cbb24ab923c0275f8fb4`, file
  `TIC-VLA-model.ckpt`, 1,938,501,547 bytes
- Expected and observed checkpoint SHA-256:
  `376263f89fad0f42c267d85655019232edc91d36e214e23424804dd4cd42e036`
- Fixture SHA-256:
  `c982be19a4b55213252902c4cc957a7e74903a6f253fc2378f512e0051237f09`

The CPU structure check found 1,324 state-dict keys. Strict model comparison
found 637 VLM keys and 50 action-expert keys, with zero missing keys, zero
unexpected keys, and zero shape mismatches. The duplicated direct/nested VLM
entries were storage aliases. Loading then succeeded with `strict=True`.

## Runtime

Runtime device: Orin, aarch64, Python 3.8.10, Jetson PyTorch
2.1.0a0+41361538.nv23.06, CUDA 11.4. Model construction, strict checkpoint
loading, and CUDA transfer took 7.438 seconds and left 1.797 GiB allocated
(1.832 GiB reserved).

| Forward | End-to-end | VLM chat | State VLM forward | Action expert | Peak allocated | Peak reserved | GPU before/after | Max SoC thermal | Power |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| measured 1 | 13.498 s | 12.977 s | 0.279 s | 0.0137 s | 2.042 GiB | 2.088 GiB | 38.94/40.50 C | 44.47 C | unavailable |
| measured 2 | 14.118 s | 13.600 s | 0.281 s | 0.0134 s | 2.044 GiB | 2.092 GiB | 39.19/40.53 C | 44.47 C | unavailable |
| measured 3 | 13.882 s | 13.371 s | 0.275 s | 0.0116 s | 2.044 GiB | 2.092 GiB | 39.09/40.75 C | 45.03 C | unavailable |

Mean measured end-to-end latency was 13.833 seconds. Component timers are
instrumented call durations; visual feature extraction occurs both inside VLM
chat and for the current frame, so component durations must not be summed as
independent end-to-end stages. The JetPack sensor interfaces exposed
temperature but did not expose a usable VDD/power reading, so power is recorded
as unavailable rather than estimated.

All three measured waypoint outputs used model dtype `torch.float32`, had shape
`(1, 30, 2)`, and passed the complete finite-value check. Each run's full
language output, prompt, raw waypoint JSON, and `.npy` array are retained under
`runs/013_offline_cuda/`.

## Compatibility overlays

1. `0001-python38-deferred-annotations.patch`: defer type-annotation evaluation
   for Python 3.8.
2. `0002-inference-import-isolation.patch`: remove unused top-level training/data
   imports from the inference path.
3. `0003-transformers-no-fsdp-import.patch`: treat unavailable FSDP as false in
   the task-local Transformers copy; the Jetson PyTorch build has no distributed
   backend and this was a single-device run.
4. `0004-jetson-no-distributed-query.patch`: provide the read-only
   `is_initialized() -> False` query expected by InternVL in this non-distributed
   process.
5. `0005-jetson-cuda-explicit-init.patch`: explicitly initialize CUDA before
   resetting Jetson PyTorch memory statistics.

The pristine TIC-VLA snapshot was not modified. No system Python, PyTorch,
CUDA, JetPack, driver, network, or global package was changed. Python
dependencies were installed only under the task-owned `python_deps/` directory.

## Safety and audit boundary

The executed TIC-VLA code and runner contained no robot sender/listener patterns.
The task started no listener, server, daemon, ROS process, SDK control path, or
motion command. Pre-existing Lite3 DDS and root-session processes remained
untouched under the explicit coexistence authorization. Post-run route,
listeners, processes, disk, task directory, checkpoint, and fixture identities
were captured. Root storage stayed above the required 10 GiB reserve.

The earlier literal stop and subsequent human coexistence authorization remain
recorded in `STOP_REPORT.md`; failed compatibility attempts 010-012 are retained
and are not counted as successful runs.

After local and remote hash verification, the 3.6 GiB task-local download
staging directory was moved to the macOS Trash. It is recoverable there; the
official URLs, resolved revisions, byte sizes, and hash inventories remain
local, while the Orin task directory retains the execution assets.

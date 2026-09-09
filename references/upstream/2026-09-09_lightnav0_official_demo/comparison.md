---
origin: official_upstream+local_inspection
reviewed: false
date: 2026-09-09
---

# LightNav-0 official demo source map

Dr Sun selected this model. The pinned source is imported; inference has not run.
The default demonstration is self-contained in `mujoco_demo/`, using the bundled
ProcTHOR `val_2_ceiling` scene and a kinematic TurtleBot, not a quadruped.

| Component | Pinned source entry | Contract |
|---|---|---|
| Install | `pyproject.toml`, `AGENTS.md` | Python 3.11; exact vLLM/Transformers/CUTLASS pins |
| Model server | `src/lightnav/serving/ws_server.py` | BF16 model, task `vln`, localhost WebSocket, recorder |
| Action representation | `README.md`, `src/lightnav/tracking.py` | RVQ codes decode to 10 `[forward, left, yaw]` waypoints; native stop decoding |
| Demo launch | `mujoco_demo/run.sh`, `vln_mujoco/__main__.py` | Separate uv environment; default TurtleBot; Linux EGL rendering |
| Fixed input | `mujoco_demo/vln_mujoco/web/index.html:48` | `move forward, then go to the trashcan on the right` |
| Scene | `mujoco_demo/vln_mujoco/assets/manifest.json` | 2,236 files, 65,457,963 bytes; all local size/SHA-256 checks passed |
| Cameras/robot | `mujoco_demo/vln_mujoco/robots/turtlebot.py` | Front RGB and native third-person view; kinematic motion |
| Client/control | `mujoco_demo/vln_mujoco/vln_client.py`, `server.py`, `mpc.py` | Existing WebSocket loop, capture-time pose alignment, MPC |
| Native termination | `mujoco_demo/vln_mujoco/server.py:369` | `result.stop is True` zeroes command and releases auto ownership |
| Recording | `docs/VISUALIZATION.md`, `src/lightnav/viz/` | Raw text/frame records and rendered overlays; long gaps may be clamped in playback |

HF model metadata pins revision `826dc5fbfa37afa8293d2e336d329b6ffc0bfb64` and
reports 4,847,825,408 BF16 parameters, with a 9,695,744,034-byte weight shard.
The public API reports `gated=false`; anonymous metadata and config access was
verified, but weights have not been downloaded or loaded by the lead.

The official demo is a functional navigation example with user-entered text,
not the full R2R/RxR/ObjectNav evaluator. Its default text is used for the first
reproduction to avoid creating a different benchmark task. Native stop and
correct target arrival must be assessed separately. Kinematic motion cannot
establish contact safety or Lite3 locomotion behavior.

Recovery: clone the canonical repository into the manifest's local source path,
checkout the exact commit, and compare every file with the experiment's
`setup/upstream_file_manifest.json`. Validate scene bytes using the upstream
asset manifest. Pinned HF metadata and LFS hashes are retained in experiment
`setup/model_source.json`; use that exact revision for checkpoint download.

No controller, inference, scene or camera modifications were made during preparation.

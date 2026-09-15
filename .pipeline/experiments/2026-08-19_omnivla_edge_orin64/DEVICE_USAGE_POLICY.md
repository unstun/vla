# Jetson AGX Orin 64GB usage boundary for VLA experiments

## Ownership boundary

The VLA project owns only `/home/nvidia/sun/`. All execution copies, virtual
environments, weights, inputs, logs, and temporary artifacts created by this
project must remain under that directory.

Everything outside `/home/nvidia/sun/` is pre-existing and protected by
default. In particular, do not rename, move, modify, archive, delete, or reuse:

- any `catkin_ws*`, ROS, SLAM, lidar, camera, PCD, bag, trajectory, vehicle
  control, autonomous-driving, or experiment directory under `/home/nvidia/`;
- `/home/nvidia/桌面`, `/home/nvidia/下载`, `/home/nvidia/文档`,
  `/home/nvidia/视频`, or their contents;
- `/home/nvidia/.local/lib/python3.8/site-packages`, which contains the working
  Jetson CUDA PyTorch stack;
- `/opt`, `/usr/local`, `/var/lib`, Docker/container data, network profiles,
  boot services, and robot-facing software;
- `/home/nvidia/.local/share/Trash`, even though its contents already occupy
  the desktop trash, unless Dr Sun separately approves permanent emptying.

## Storage rules

1. Before every transfer, record `df -h /`, exact incoming byte count, and the
   task-owned remote target. Refuse the transfer if it would leave less than
   10 GiB free.
2. Do not place VLA files on the desktop, in downloads, in a vehicle workspace,
   or in a global cache. Use a dated directory under
   `/home/nvidia/sun/vla_exec/`.
3. Reuse JetPack PyTorch from its existing location. Put only lightweight
   missing dependencies in a task-scoped `python_deps/` directory and disable
   pip caching. Do not require or install system `python3-venv`.
4. A task may delete only its own dated execution directory after an exact-path
   inventory and explicit authorization. It may clean regenerable caches only
   when the cache path and expected reclaimed size have first been reviewed.
5. Do not use `apt autoremove`, Docker prune, recursive deletion of a home or
   project root, wildcard deletion outside a task-owned directory, or deletion
   based only on age or filename resemblance.

## Cleanup performed on 2026-08-19

The following regenerable, non-project data was permanently removed:

- `/home/nvidia/.cache/vscode-cpptools`;
- `/home/nvidia/.cache/pip`;
- `/root/.cache/pip`;
- apt package archives;
- seven disabled historical Snap revisions.

Root filesystem availability changed from approximately 13 GiB (95% used) to
approximately 17 GiB (93% used). No vehicle project, bag, PCD, model,
experiment log, active Snap revision, Docker object, or trash item was deleted
in this first cleanup stage.

After deployment, Dr Sun separately and explicitly approved permanent desktop
trash emptying. Exactly the contents of
`/home/nvidia/.local/share/Trash/files` and
`/home/nvidia/.local/share/Trash/info` were deleted: 1,827 entries occupying
approximately 46 GB. The two trash directories were retained and verified
empty. Root availability increased from approximately 16 GB (93% used) to
62 GB (73% used). Protected vehicle working directories and the VLA deployment
were then rechecked and remained present; the 125-entry VLA input manifest
still passed.

## Runtime rules

- No VLA daemon or autostart entry.
- No network-profile or route changes.
- No robot command/control interface in receive-only tests.
- Each run has a unique directory, explicit hashes, logs, resource evidence,
  and a sync-back to the local VLA repository.

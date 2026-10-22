# ultra9 storage cleanup,2026-10-20

Completed the exact user-approved cleanup. No model, teacher bank, experiment archive, video, installed environment or other user's data was deleted.

| Observation | GiB |
|---|---:|
| Free immediately before cleanup | 74.613 |
| Free immediately after cleanup | 113.177 |
| Observed free-space increase | 38.564 |

Removed the unreferenced2023 Noetic Docker image `sha256:ebd660bc59a0a27901d3a002a4666cf73b310e61b170f1a927e68c6bbcbb6f38` and exactly543 downloaded `.conda`/`.tar.bz2` package archives,687618903bytes, from the four directories in the [reviewed plan](evidence/storage_cleanup_plan01.json). Extracted packages and environments remain intact. Retained the active Foxy image `sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343`.

The old image can be requested by its original registry digest:

```sh
docker pull wenjingtang/noetic_cuda11_1_cudnn8_libtorch_opencv4_ws_noentry@sha256:ebd660bc59a0a27901d3a002a4666cf73b310e61b170f1a927e68c6bbcbb6f38
```

The old RoboGauge evaluation tree contains77.7GiB in158 `subtasks.tar.xz` experiment archives. They are retained as research evidence. The1.01TiB `sun`,371.85GiB `ljh` and109.54GiB `gpu40901-data` trees were inventoried only; their nested rows must not be summed with their parents. Ordinary home caches were only0.67GiB and were not the main space consumer.

[Execution receipt](evidence/storage_cleanup_execution01.json) and [post-clean verification](evidence/storage_cleanup_verification01.json) bind the exact plan SHA. Verification confirms543 archives absent, only the approved image removed,329 frozenv286 sources unchanged, and imports of NumPy/Warp/Newton successful. The same frozen source rebuilt all14 native packages onultra9 in214s, Docker exit0; further native/offline/physics qualification remains separate.

The VLA migration prefix is `/home/ubuntu/sun/vla_v286_20261020`. The local repository remains the source of truth. Later migration outputs can reduce free space; the figures above are the immediate cleanup observations, not a reserved quota.

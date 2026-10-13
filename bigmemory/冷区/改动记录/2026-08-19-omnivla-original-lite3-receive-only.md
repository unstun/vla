> [摘要] Pinned official-CUDA forward and one Lite3 receive-only camera request passed; no robot motion or navigation claim.

# OmniVLA-original CUDA and Lite3 receive-only milestone

Date: 2026-08-19

- Pinned source: OmniVLA commit
  `5182600cb4a9ee07684e17cdd2a6cbafc56b8a68` (MIT).
- Pinned original checkpoint revision:
  `e36a84d4923c041149d441f93f3bdb7092bb5f07`.
- The original checkpoint completed upstream-default and language-only
  `move forward` single forwards in the official CUDA stack on gpu40901. Both
  exited 0 with finite shape `(8, 4)` under the 24,576 MiB preflight guard and
  0.45 process-memory cap.
- Lite3 captured one real 1280x720 front-camera frame from its unchanged local
  RTSP service and received a matching finite `(8, 4)` response from the pinned
  original model. The wire contract recorded `actuation_enabled=false` and
  `uncalibrated_for_lite3`.
- The service was stopped after the single request. Network routes, both
  gpu40901 FRP services, SSH, Lite3 camera processes, CARLA, and IsaacLab stayed
  healthy.
- Claim boundary: `reproduced` for the original official-CUDA single forward;
  `integrated` and `validated` only for the single-frame receive-only Lite3
  contract. No calibrated trajectory, closed-loop navigation, locomotion, or
  real-robot motion result.

Evidence:

- `.pipeline/experiments/2026-08-19_omnivla_original_cuda_gpu40901/`
- `.pipeline/experiments/2026-08-19_omnivla_lite3_receive_only/`

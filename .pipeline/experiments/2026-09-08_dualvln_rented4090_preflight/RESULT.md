# Rented RTX 4090 preflight

Date: 2026-09-08. Stage: planning / environment preflight.
Authorization: Dr Sun supplied the rented server connection for VLA inference and simulation assessment.

Read-only SSH succeeded at `ubuntu@117.50.179.202` (existing local alias `rented4090`), hostname `10-60-164-100`. Existing SSH key authentication worked; no supplied password was written to these artifacts.

| Item | Observed |
| --- | --- |
| GPU | RTX 4090, 24564 MiB total, 2903 MiB used |
| Driver | 575.57.08 |
| OS / Python | Ubuntu 22.04.4 LTS / Python 3.10.12 |
| RAM | 62 GiB total, 55 GiB available |
| Root filesystem | 194G total, 125G available |
| GPU process | PID 1324, `/isaac-sim/kit/kit`, 2859 MiB |
| Running container | `isaac-sim`, image `nvcr.io/nvidia/isaac-sim:5.1.0`, id `16998b63e8dd` |

The normal Ubuntu account cannot directly access the Docker socket. Read-only `sudo -n docker ps` succeeded. No container, process, route, driver, or remote file was changed.

Assessment: appropriate hardware for a first original-precision DualVLN inference test. The paper reports about 20GB for the full model on RTX 4090; that is not a memory measurement on this instance. Concurrent simulation leaves little VRAM margin and must be profiled. Existing Isaac Sim 5.1.0 availability does not establish compatibility with the pinned InternNav/InternUtopia evaluation stack.

Next execution should isolate the VLA environment and model source, preserve existing locomotion work, validate inference first, then perform a bounded simulator episode and return a playable local video. No model or simulator workload was launched during this preflight. Recheck mutable process/resource observations before execution.

Source: <https://arxiv.org/html/2512.08186v1#S5.SS2>. Raw observations and the executed probe bodies are in this directory. Local repository `/Users/sun/tongbu/study/phdproject/vla` remains the source of truth; an experiment execution root on this server has not yet been created.

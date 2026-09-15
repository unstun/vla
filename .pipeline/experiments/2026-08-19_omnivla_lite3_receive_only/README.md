# OmniVLA Lite3 receive-only deployment evidence

Status: `integrated` and `validated` for the declared single-frame receive-only
contract. One real Lite3 front-camera frame and `move forward` instruction
completed a round trip through the pinned OmniVLA-original service on
`gpu40901`. No control path was present, and the service is installed but
stopped. See `decision_log.md` for the frozen expectations, deviations, stop
rules, and claim boundary.

## Evidence available so far

- Prerequisite CUDA evidence is under the sibling experiment
  `2026-08-19_omnivla_original_cuda_gpu40901/`. The pinned original checkpoint
  completed an upstream-default forward and a language-only `move forward`
  forward on the RTX 4090. Both exited 0 with finite shape `(8, 4)`; the
  language-only forward took 0.361 seconds and its 60-second preflight observed
  at least 33,705 MiB free VRAM.

- Local: 18 protocol/client/service/safety tests passed under
  `env/local_tests.txt`; the shared client files also parsed with Python 3.8
  syntax and the shell scripts passed syntax checks.
- gpu40901: the exact source manifest passed and the same 18 fake-backend tests
  passed under `verify/source_manifest.txt` and `env/remote_fake_tests.txt`.
- Lite3 real camera to fake backend: one explicit `move forward` request passed.
  The saved JPEG is 1280x720 and 139,567 bytes, with SHA-256
  `c88ce397f783fec817b15d0880f03b592482853927cecf7542c60e5963e5d52a`.
  Request/response IDs match; the fake response is finite shape `(8, 4)` and
  has `actuation_enabled: false`. Evidence is under `runs/fake_roundtrip/`.
  This proves only camera capture, Wi-Fi transport, and protocol handling; its
  trajectory is deterministic fake data, not OmniVLA output.
- The fake listener was restricted to `192.168.2.109:8765` and was stopped
  afterward. `verify/post_fake_preflight.txt` shows the port closed and the
  original gpu40901 routes unchanged.

## Real original-model result

- Run ID:
  `20260819T103300.657356Z_61711107-9e58-4341-9c47-80e2b40f086d`.
- Lite3 captured one visually inspected, non-blank 1280x720 JPEG from the
  existing robot-loopback RTSP stream. It is 122,721 bytes with SHA-256
  `c982be19a4b55213252902c4cc957a7e74903a6f253fc2378f512e0051237f09`.
- The server received `move forward` from `192.168.2.1`. The request ID matched
  end to end; the response identities matched the pinned source and checkpoint;
  and the normalized trajectory was finite shape `(8, 4)`.
- Model inference took 456.746 ms and Lite3 monotonic end-to-end time was
  5,029.914 ms. These are acceptance-run observations, not a benchmark.
- The response recorded `language_only`, `actuation_enabled: false`, and
  `metric_scale_status: uncalibrated_for_lite3`.
- The original service listened only on `192.168.2.109:8765`. Online probes
  rejected a bad token with 401, an oversized body with 413, and invalid JPEG
  bytes with 400 before the accepted request.
- The real-service 60-second VRAM preflight minimum was 33,701 MiB. After the
  one request, the recorded task PID was stopped, port 8765 closed, and the
  model's approximately 15.7 GiB allocation disappeared. Existing CARLA and
  IsaacLab PIDs remained present.

## Acceptance summary

| Criterion | Result | Evidence |
|---|---|---|
| AC1 prerequisite | PASS | sibling original-CUDA experiment, two validated forwards |
| AC2 local quality | PASS | 18 tests, Python 3.8 syntax and shell checks |
| AC3 identity and guard | PASS | exact manifests; 33,701 MiB minimum; 0.45 cap |
| AC4 scoped service | PASS | `verify/real_listener.txt`, negative probes, health identity |
| AC5 real capture | PASS | saved 1280x720 JPEG; camera owner unchanged |
| AC6 end to end | PASS | matching request/response and finite 8x4 trajectory |
| AC7 fail closed | PASS | unit suite, static scan, and three online rejection probes |
| AC8 non-interference | PASS | routes/SSH/FRP/camera and unrelated GPU jobs rechecked |
| AC9 closeout | PASS | evidence manifest passes; server and listener stopped |
| AC10 claim boundary | PASS | receive-only scope stated below |

## Live deviations

The existing root-owned camera service already holds `/dev/video0` and
restreams it at robot-loopback `rtsp://127.0.0.1:8554/test`. Direct V4L2
therefore returns `EBUSY`. The client now reads one software-decoded JPEG from
that fixed loopback stream instead of stopping or reconfiguring the owner.
Verbatim failures are under `logs/camera_preflight/`.

The Lite3 wall clock was measured about 45 seconds ahead of gpu40901. No system
clock was changed. Request elapsed time is measured with the Lite3 monotonic
clock; cross-host UTC ordering is treated as uncalibrated evidence metadata.

## Claim boundary

This result validates only the installed, manually invoked, single-frame
camera-plus-language-to-trajectory contract. It does not validate the upstream
0.1 m scale on Lite3, semantic navigation success, obstacle avoidance,
closed-loop operation, locomotion integration, or any real-robot motion.

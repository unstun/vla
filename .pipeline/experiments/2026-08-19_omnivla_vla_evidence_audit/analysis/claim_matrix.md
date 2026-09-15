# Claim matrix for human review

| Candidate | surveyed | imported | reproduced | integrated | validated | Not established |
|---|---|---|---|---|---|---|
| OmniVLA-original | Pinned paper/repository interface and code path inspected. | Pinned commit `5182600...` and local receive-only adapter are present. | Frozen 24-forward CUDA matrix ran on `gpu40901`; all attempts retained. | Receive-only callable adapter accepts the frozen image/instruction contract and returns a validated trajectory record. | The declared audit record/identity/shape/finite/sync-back checks passed for this matrix. | Final VLA classification, semantic reliability, collision avoidance, Lite3 scale, navigation success, locomotion compatibility, latency, and actuation safety. |
| OmniVLA-edge | Pinned repository interface and code path inspected. | Pinned commit `5182600...`, recorded edge patches, and local audit runner are present. | Frozen 24-forward CUDA matrix ran on Jetson AGX Orin 64GB; all attempts retained. | Receive-only audit runner uses the pinned edge/CLIP path and returns validated trajectory records. | The declared audit record/identity/shape/finite/sync-back checks passed for this matrix. | Final VLA classification, semantic reliability, collision avoidance, Lite3 scale, navigation success, locomotion compatibility, latency, and actuation safety. |

`validated` above is strictly limited to the frozen receive-only audit contract.
It is not a whole-system VLA, navigation, safety, deployment, or real-motion
validation label.


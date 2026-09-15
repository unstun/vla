# Environment deviations

Status before the first model process:

- Python 3.10 and the exact PyTorch family pins remain as specified upstream.
- Package downloads use `https://pypi.tuna.tsinghua.edu.cn/simple` because a
  measured `pypi.org` transfer delivered only about 60--130 KiB/s and did not
  complete the first torch wheel after roughly 100 minutes. This changes the
  index transport only, not the selected package versions.
- Flash Attention 2.5.5 follows the recorded prebuilt-wheel, bounded-source-
  build, then documented-skip sequence. Its actual outcome is appended after
  phase B finishes.
- The first phase-A process inherited pip's default `/home/ubuntu/.cache/pip`
  before the task-local cache guard was added. That cache pre-existed at 17 GB,
  so task-created entries cannot be isolated safely and nothing there will be
  deleted. All subsequent pip processes set
  `PIP_CACHE_DIR=$REMOTE/pip_cache`; a phase-A retry would do the same.
- The first phase-B editable install reached the official
  `transformers-openvla-oft` GitHub dependency but received no additional bytes
  for five minutes. Only that task-owned process group was terminated. Both Git
  dependencies were then acquired from their official URLs on the local source
  host, pinned to commits `bc339d9ad707454c0c115970db43c260067c61ab` and
  `040105d256bd28866cc6620621a3d5f7b6b91b46`, manifest-verified, and substituted
  as local `file://` transports. Package source is unchanged; the exact upstream
  dependency list is retained in `scripts/remote_requirements.txt`.
- The first post-install `import prismatic` failed because pip selected
  `tensorflow-metadata 1.21.0`, whose generated protobuf code imports
  `google.protobuf.runtime_version`, while TensorFlow 2.15 constrained protobuf
  to 4.25.9 where that API is absent. `tensorflow-metadata==1.15.0` is pinned as
  the TensorFlow 2.15-era compatibility version; its wheel metadata for Python
  3.10 requires protobuf `>=3.20.3,<4.21`, and its generated code does not import
  `runtime_version`. The probed wheel SHA-256 is
  `cb84d8e159128aeae7b3f6013ccd7969c69d2e6d1a7b255dbfa6f5344d962986`.
- Pinning that compatible protobuf exposed a declared conflict with the newest
  unpinned `wandb 0.28.0`, which requires protobuf `>4.21`. `wandb==0.16.6` is
  pinned because its official wheel metadata for Python >3.9 on Linux requires
  protobuf `>=3.19,<5,!=4.21.0`, covering 3.20.3. The probed wheel SHA-256 is
  `5810019a3b981c796e98ea58557a7c380f18834e0c6bdaed15df115522e5616e`.

# OmniVLA Lite3 receive-only deployment

This package implements the reviewed first integration slice:

```text
Lite3 front camera -> one JPEG + language instruction -> gpu40901
  -> pinned OmniVLA-original -> 8x4 trajectory -> Lite3 evidence files only
```

It contains no navigation or locomotion sender. The upstream `0.1 m` trajectory
scale is preserved but explicitly uncalibrated for Lite3. The model service is
on-demand and must be stopped after the supervised acceptance request.

The source of truth is this local directory. Execution copies are:

- gpu40901: `/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_lite3_receive_only/`
- Lite3: `/home/user/omnivla_receive_only/`

Runtime tokens are generated remotely with mode `0600`; their values are never
tracked or printed in run evidence.

The client can read `/dev/video0` directly when it is free. On the inspected
Lite3 installation, the existing `/home/ysc/rtsp_stream/start_stream.sh`
already owns that device and restreams the same front-camera frames at
`rtsp://127.0.0.1:8554/test`. The reviewed deployment therefore uses
`--rtsp-url rtsp://127.0.0.1:8554/test` with software decoding, leaving that
pre-existing camera service untouched.

The server enforces a 30-second socket I/O timeout, and the complete on-demand
server process has a 30-minute wall deadline. Model inference remains serial.

## Manual lifecycle

After the pinned original-model prerequisite has passed, run these only on
`gpu40901`:

```bash
/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_lite3_receive_only/deploy/omnivla_lite3_receive_only/scripts/start_server.sh
/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_lite3_receive_only/deploy/omnivla_lite3_receive_only/scripts/status_server.sh
/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_lite3_receive_only/deploy/omnivla_lite3_receive_only/scripts/stop_server.sh
```

One explicit receive-only request on Lite3 is:

```bash
ROOT=/home/user/omnivla_receive_only
PYTHONPATH="$ROOT/deploy" python3 -m omnivla_lite3_receive_only.lite3_client \
  --server-url http://192.168.2.109:8765 \
  --instruction 'move forward' \
  --token-file "$ROOT/runtime/token" \
  --output-dir "$ROOT/runs/real_original" \
  --rtsp-url rtsp://127.0.0.1:8554/test \
  --capture-timeout 4 \
  --timeout 600
```

The normal closeout is `stop_server.sh`; installed files are retained. A full
rollback is deliberately manual and separately authorized: first stop and prove
port 8765 closed, validate the two exact execution roots shown above, and then
remove only those roots. Removing `user` from `video` is a separate reversible
change and is not part of normal rollback. Never remove the prerequisite
checkpoint root or alter Wi-Fi, FRP, camera, navigation, or locomotion services.

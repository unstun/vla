# P2B executable overlay

The old sketch patches were replaced by the hash-gated materializer:

```bash
python3 -m backend_adapter.materialize_overlay \
  --source references/upstream/2026-09-16_lite3_isaac_harness_backend/source/pct_scan_foxy/src \
  --output /home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/overlay_ws/src
```

The materializer verifies frozen source hashes, then writes typed ROS messages and concrete C++ changes for SCAN admission, cancellation, B-spline identity propagation and generation-tagged raw command output.

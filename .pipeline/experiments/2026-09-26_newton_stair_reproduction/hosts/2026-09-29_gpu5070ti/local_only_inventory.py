"""Write hosts/2026-09-29_gpu5070ti/LOCAL_ONLY_RUN_BYTES.json: local-only bytes of the port's own validation runs, by the
v29-v32 conventions (LOCAL_ONLY_BYTES.json in this directory covers the runtime additions and the private bytes on
gpu5070ti, and is not edited).

- P5 replay caches (as v32's K3 caches): clouds, rows.jsonl, writer_sink.jsonl and factory_full_rate.npz of each
  attempt; summary.json, gc_events.npy, the factory records and the stdout logs are tracked.
- P6's run port5070_v33_flat02: the thirteen raw-capture kinds of v31's convention. port5070_v33_flat01, which failed
  before physics, is small and tracked whole.
Usage: python3 local_only_inventory.py
"""
from pathlib import Path
import hashlib, json, os

H = Path(__file__).resolve().parent
E = H.parents[1]
ROOT = E.parents[2]
P5 = [f"hosts/2026-09-29_gpu5070ti/p5_replay_none_attempt{n:02d}/{name}" for n in (1, 2, 3)
      for name in ("clouds", "rows.jsonl", "writer_sink.jsonl", "factory_full_rate.npz")]
P6 = [f"runs/port5070_v33_flat02/{name}" for name in
      ("applied_channel.jsonl", "applied_sent.jsonl", "artifacts", "backend_body_callbacks.jsonl", "backend_states.jsonl",
       "clock_samples.jsonl", "clouds", "factory_full_rate.npz", "inputs", "linux_external_episode.tar", "sensor.jsonl",
       "telemetry.jsonl", "video_states.json")]
symlinks = []


def entry(relative):
    base = E / relative
    paths = [base] if base.is_file() else sorted(p for p in base.rglob("*") if p.is_file() or p.is_symlink())
    files = []
    for p in paths:
        if p.is_symlink():
            symlinks.append({"path": str(p.relative_to(ROOT)), "target": os.readlink(p)})
            continue
        files.append({"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
    return {"entry": str(base.relative_to(ROOT)), "files": files}


count = lambda g: sum(len(e["files"]) for e in g)
size = lambda g: sum(f["bytes"] for e in g for f in e["files"])
caches = [entry(c) for c in P5 if (E / c).exists()]
raw = [entry(r) for r in P6 if (E / r).exists()]
record = {"storage_root": str(ROOT), "deletion_performed": False,
          "scope": "Local-only bytes of the gpu5070ti port's validation runs: P5's replay caches and P6's raw captures, "
                   "copied from gpu5070ti and verified by SHA-256 (PORT.md). Their summaries, logs and results are tracked.",
          "regeneration": {
              "p5": "Rerun checks/p5_replay.sh on gpu5070ti with a new attempt number; it replays v31_historical_full01's "
                    "recorded commands. The joint states are deterministic on that host; timings are not.",
              "p6": "Not regenerable. These are the recorded physical-run captures of P6 on gpu5070ti; preserve at the exact "
                    "project paths."},
          "regenerable_caches": caches, "raw_artifacts": raw, "symlinks_skipped": symlinks,
          "missing_entries": [m for m in P5 + P6 if not (E / m).exists()],
          "raw_count": count(raw), "raw_bytes": size(raw), "cache_count": count(caches), "cache_bytes": size(caches)}
(H / "LOCAL_ONLY_RUN_BYTES.json").write_text(json.dumps(record, indent=2) + "\n")
print({k: record[k] for k in ("raw_count", "raw_bytes", "cache_count", "cache_bytes")}, "symlinks", len(symlinks),
      "missing", record["missing_entries"])

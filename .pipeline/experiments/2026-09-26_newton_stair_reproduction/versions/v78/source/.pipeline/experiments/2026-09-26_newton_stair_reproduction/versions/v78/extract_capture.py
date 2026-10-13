"""Read-only remote extraction of the original v76 scan prefix to stdout ZIP."""
from pathlib import Path
import hashlib
import json
import sys
import zipfile

ROOT = Path("/home/sun/vla_artifacts/2026-10-04_corner_start/v76_mac_trial01_attempt01")
manifest = json.loads((ROOT / "storage_manifest.json").read_text())
archive = ROOT / "raw_capture.zip"
row = manifest["files"]["raw_capture.zip"]
assert row["sha256"] == "0b09868a9652ee6807432f278b27593a098554a50ecddf48db5586d746b8dce8"
assert archive.stat().st_size == row["bytes"]
assert hashlib.sha256(archive.read_bytes()).hexdigest() == row["sha256"]
sensor_bytes = (ROOT / "sensor.jsonl").read_bytes()
assert manifest["files"]["sensor.jsonl"]["sha256"] == "ba34b3cd7398b09b38122e1d143d480a06dd6294f470b7821f5143cd7d21c74e"
assert hashlib.sha256(sensor_bytes).hexdigest() == manifest["files"]["sensor.jsonl"]["sha256"]
records = [json.loads(line) for line in sensor_bytes.splitlines()]
records = [r for r in records if r["sensor"]["scan_window"]["scan_index"] <= 187]
assert len(records) == 188 and records[-1]["stamp_ns"] == 29815242767
with zipfile.ZipFile(archive) as original, zipfile.ZipFile(sys.stdout.buffer, "w", compression=zipfile.ZIP_DEFLATED) as output:
    sources = {}
    for r in records:
        name = r["file"]
        data = original.read(name)
        assert hashlib.sha256(data).hexdigest() == r["sha256"]
        sources[name] = {"sha256": r["sha256"], "bytes": len(data)}
        output.writestr(name, data)
    output.writestr("sensor_records.json", json.dumps(records))
    scan = original.read("scan.log").decode().splitlines()
    output.writestr("original_spike.log", "\n".join(f"{i+1}: {scan[i]}" for i in range(15140, 15231)) + "\n")
    output.writestr("identity.json", json.dumps({"original_raw_sha256": row["sha256"], "original_sensor_sha256": manifest["files"]["sensor.jsonl"]["sha256"], "source_members": sources, "scans": len(records), "last_scan": 187, "gpu_job_started": False}, indent=2))

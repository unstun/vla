"""Independently audit completed trials and deliver regular local video files."""
import ast
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess

import numpy as np
from PIL import Image

BASE = Path(__file__).resolve().parents[1]
PROJECT = BASE.parents[2]
DELIVERY = PROJECT / "output/2026-09-26_newton_macos"
OUT = BASE / "validation"


def digest(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def main():
    OUT.mkdir(exist_ok=True)
    DELIVERY.mkdir(exist_ok=True)
    report = {"runs": {}, "syntax": {}, "source_parity": {}, "storage": {}}
    for label, name in (("go2", "go2_video_v3"), ("lite3", "lite3_video_v2")):
        run = BASE / "runs" / name
        process = json.loads((run / "process.json").read_text())
        result = json.loads((run / "result.json").read_text())
        assert process["exit_code"] == 0 and not process["timed_out"] and result["acceptance"]
        rows = [json.loads(line) for line in (run / "telemetry.jsonl").read_text().splitlines()]
        expected_steps, expected_duration = (400, 8) if label == "go2" else (600, 12)
        assert len(rows) == expected_steps
        clocks = np.array([r["physics_time_s"] for r in rows])
        assert np.all(np.diff(clocks) > 0) and abs(clocks[-1] - expected_duration) < .001
        for field in ("joint_q", "joint_qd", "observation", "action"):
            assert np.isfinite(np.asarray([r[field] for r in rows])).all()
        assert np.isfinite(np.asarray([r.get("applied_torque", r.get("applied_joint_force")) for r in rows])).all()
        manifest = json.loads((run / "frames.json").read_text())
        assert len(manifest) == expected_steps // 2
        for index, item in enumerate(manifest):
            assert digest(run / item["file"]) == item["sha256"]
            assert item["policy_step"] == 2 * (index + 1)
            assert abs(item["physics_time_s"] - rows[item["policy_step"] - 1]["physics_time_s"]) < 1e-9
        video = Path(result["video"])
        assert digest(video) == result["video_sha256"]
        probe_command = ["/opt/homebrew/bin/ffprobe", "-v", "error", "-show_entries",
                         "stream=codec_name,width,height,nb_frames,r_frame_rate,duration", "-of", "json", str(video)]
        probed = subprocess.run(probe_command, capture_output=True, text=True, timeout=30, check=True)
        stream = json.loads(probed.stdout)["streams"][0]
        assert int(stream["nb_frames"]) == len(manifest)
        assert float(stream["duration"]) == expected_duration and stream["r_frame_rate"] == "25/1"
        decode_command = ["/opt/homebrew/bin/ffmpeg", "-nostdin", "-v", "error", "-i", str(video), "-f", "null", "-"]
        decoded = subprocess.run(decode_command, capture_output=True, text=True, timeout=30, check=True)
        assert not decoded.stderr.strip()
        destination = DELIVERY / (label + "_newton_macos.mp4")
        if destination.exists():
            assert destination.is_file() and not destination.is_symlink() and digest(destination) == digest(video)
        else:
            shutil.copyfile(video, destination)
        # Contact sheet is a review derivative of the preserved raw framebuffer images.
        selected = [0, len(manifest) // 3, 2 * len(manifest) // 3, len(manifest) - 1]
        sheet = Image.new("RGB", (1280, 720))
        for cell, index in enumerate(selected):
            im = Image.open(run / manifest[index]["file"]).convert("RGB")
            assert np.asarray(im).std() > 5
            im.thumbnail((640, 360))
            sheet.paste(im, ((cell % 2) * 640, (cell // 2) * 360))
        sheet.save(OUT / (label + "_contact_sheet.png"))
        start_pos = np.array([0, 0, .76 if label == "go2" else .35])
        points = np.array([r["joint_q"][:3] for r in rows])
        quaternion = np.array(rows[-1]["joint_q"][3:7])
        x, y, z, w = quaternion / np.linalg.norm(quaternion)
        report["runs"][label] = {
            "run": name, "checks_passed": True, "process": process, "result": result,
            "video_probe": stream, "video_decode_exit": decoded.returncode,
            "frame_hashes_verified": len(manifest), "unique_frame_hashes": len({f["sha256"] for f in manifest}),
            "planar_net_displacement_m": float(np.linalg.norm(points[-1, :2] - start_pos[:2])),
            "planar_path_length_m": float(np.linalg.norm(np.diff(points[:, :2], axis=0), axis=1).sum()),
            "final_yaw_deg": math.degrees(math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))),
            "delivered_file": str(destination), "delivery_sha256": digest(destination),
            "delivery_regular_file": not destination.is_symlink(),
            "probe_command": probe_command, "decode_command": decode_command,
        }
    for path in sorted((BASE / "scripts").glob("*.py")) + sorted((BASE / "setup").glob("*.py")):
        ast.parse(path.read_text(), filename=str(path))
        report["syntax"][str(path.relative_to(BASE))] = "passed"
    import newton
    installed = Path(newton.__file__).parent
    pristine = BASE / "source/newton-c2ca70bec5998062b0b2d35869865cbe3a49feee/newton"
    count = 0
    for path in pristine.rglob("*.py"):
        assert digest(path) == digest(installed / path.relative_to(pristine))
        count += 1
    report["source_parity"] = {"matched_python_files": count, "patched_upstream_files": 0}
    report["contracts"] = json.loads((BASE / "runs/contracts_v1/result.json").read_text())
    assert report["contracts"]["passed"]
    report["storage"]["free_gib"] = shutil.disk_usage(BASE).free / 1024**3
    assert report["storage"]["free_gib"] >= 10
    (OUT / "RESULTS.json").write_text(json.dumps(report, indent=2) + "\n")
    (DELIVERY / "provenance.json").write_text(json.dumps({
        "source_of_truth": str(BASE), "validation": str(OUT / "RESULTS.json"),
        "videos": {key: {field: value[field] for field in ("run", "delivery_sha256", "delivered_file")}
                   for key, value in report["runs"].items()},
    }, indent=2) + "\n")
    print(json.dumps({key: {k: v for k, v in value.items() if k in
                     ("checks_passed", "planar_net_displacement_m", "final_yaw_deg", "delivered_file")}
                     for key, value in report["runs"].items()}, indent=2))


if __name__ == "__main__":
    main()

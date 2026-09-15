"""Verify the declared pair's actual inputs and local evidence before comparison."""
import copy
import hashlib
import json
import subprocess
import tarfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent


def main():
    plan = json.loads((ROOT / "plan.json").read_text())
    execution = json.loads((ROOT / "execution.json").read_text())
    assert execution["plan_sha256"] == hashlib.sha256((ROOT / "plan.json").read_bytes()).hexdigest()
    assert [r["language"] for r in execution["runs"]] == plan["order"]
    configs, source_hashes, rows = [], [], []
    for record in execution["runs"]:
        assert record["returncode"] == 0
        language = record["language"]
        run = ROOT.parent / "runs" / record["run_id"]
        meta = json.loads((run / "meta.json").read_text())
        result = json.loads((run / "analysis.json").read_text())
        request = json.loads((run / "input_request.json").read_text())
        config = yaml.safe_load((run / "hospital_demo.yaml").read_text())
        instruction = plan["instructions"][language]
        assert meta["instruction"] == request["instruction"] == result["episode"]["instruction"] == instruction
        assert result["model_instructions"] == [instruction]
        assert config["episode_hospital_demo"]["instruction"] == instruction
        assert meta["inference_seed"] == request["inference_seed"] == result["inference_seed"] == plan["inference_seed"]
        assert f"TICVLA_INFERENCE_SEED {plan['inference_seed']}" in (run / "stdout.log").read_text()
        assert not meta["timed_out"] and meta["exit_code"] == 0
        configs.append(copy.deepcopy(config))
        configs[-1]["episode_hospital_demo"].pop("instruction")
        source_hashes.append(meta["source_manifest_sha256"])
        inventory = json.loads((run / "artifact_sha256.json").read_text())
        checks = []
        with tarfile.open(run / "raw_overlay_frames.tar.gz") as archive:
            for item in inventory:
                data = archive.extractfile(item["path"]).read() if item["path"].startswith("frames/") else (run / item["path"]).read_bytes()
                match = len(data) == item["bytes"] and hashlib.sha256(data).hexdigest() == item["sha256"]
                checks.append({"path": item["path"], "passed": match})
        assert all(check["passed"] for check in checks)
        (run / "local_integrity.json").write_text(json.dumps(checks, indent=2) + "\n")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(run / "navigation_with_trajectory.mp4"), "-f", "null", "-"], check=True)
        duration = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(run / "navigation_with_trajectory.mp4")]))["format"]["duration"]
        episode = result["episode"]
        rows.append({"language": language, "run_id": record["run_id"], "instruction": instruction,
                     "success": episode["success"], "navigation_error_m": episode["navigation_error"],
                     "path_length_m": episode["path_length"], "physical_collision": episode["physical_collision_detected"],
                     "model_calls": result["model_calls"], "finite_30x2": result["finite_30x2"],
                     "video_seconds": float(duration), "video": str(run / "navigation_with_trajectory.mp4"),
                     "artifact_checks": len(checks), "gpu_peak_sampled_mib": result["gpu_peak_sampled_mib"]})
    assert configs[0] == configs[1], "Non-language scenario settings differ"
    assert len(set(source_hashes)) == 1, "Source differs between pair members"
    summary = {"same_non_language_config": True, "same_source_manifest": source_hashes[0],
               "scenario_seed": plan["scenario_seed"], "inference_seed": plan["inference_seed"],
               "rows": rows, "boundary": plan["claim_boundary"]}
    (ROOT / "comparison.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

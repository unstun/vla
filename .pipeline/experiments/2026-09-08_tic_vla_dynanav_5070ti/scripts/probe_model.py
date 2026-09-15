"""Bounded model compatibility probe before starting the simulator episode."""

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import torch
from ticvla import TICVLA


def main():
    root = Path(os.environ["TICVLA_TASK_ROOT"])
    manifest = json.loads((root / "manifests/official_assets.json").read_text())
    if "--construct-only" in sys.argv:
        model = TICVLA(model_path=os.environ["TICVLA_BASE_MODEL_PATH"], device="cuda:0", num_action_chunks=30)
        print("MODEL_CONSTRUCTOR_READY", len(model.state_dict()), "state keys; no checkpoint or inference test", flush=True)
        model.cleanup()
        return
    checkpoint = Path(os.environ["TICVLA_CHECKPOINT_PATH"])
    digest = hashlib.sha256()
    with checkpoint.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != manifest["checkpoint"]["sha256"]:
        raise RuntimeError("Checkpoint identity mismatch")
    torch.cuda.init()
    started = time.perf_counter()
    model = TICVLA(model_path=os.environ["TICVLA_BASE_MODEL_PATH"], device="cuda:0", num_action_chunks=30)
    # The verified official Lightning checkpoint contains metadata in addition to tensors.
    payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
    state = payload["state_dict"]
    if not all(key.startswith("model.") for key in state):
        raise RuntimeError("Unexpected checkpoint key namespace")
    model.load_state_dict({key[len("model."):]: value for key, value in state.items()}, strict=True)
    model.eval()
    del payload, state
    records = []
    report = {"load_seconds": time.perf_counter() - started, "strict_load": True,
              "checkpoint_sha256": digest.hexdigest(), "torch": torch.__version__,
              "gpu": torch.cuda.get_device_name(0), "records": records,
              "claim_boundary": "offline repeated-image compatibility probe; no simulation or navigation result"}
    image = str(Path(os.environ["TICVLA_BASE_MODEL_PATH"]) / "examples/image1.jpg")
    try:
        for step in range(4):
            started = time.perf_counter()
            with torch.inference_mode():
                response, waypoints, generation, available, pose = model.predict_async(
                    image_paths=[image] * 4, instruction="Move forward safely.",
                    robot_state=torch.zeros(6), current_step=step,
                    current_robot_pose={"position": [0.0, 0.0, 0.0], "quaternion": [1.0, 0.0, 0.0, 0.0]},
                    time_delay=0.0, previous_waypoints_text="The robot has remained at (0, 0, 0).",
                    robot_type="wheeled robot")
            torch.cuda.synchronize()
            record = {"step": step, "seconds": time.perf_counter() - started,
                      "shape": list(waypoints.shape), "finite": bool(torch.isfinite(waypoints).all()),
                      "cache_available": bool(available), "response": response,
                      "allocated_bytes": torch.cuda.memory_allocated(), "reserved_bytes": torch.cuda.memory_reserved()}
            records.append(record)
            (root / "logs/model_probe.json").write_text(json.dumps(report, indent=2) + "\n")
            print("MODEL_PROBE", json.dumps(record), flush=True)
            if record["shape"] != [1, 30, 2] or not record["finite"]:
                raise RuntimeError("Invalid model trajectory")
    finally:
        model.cleanup()


if __name__ == "__main__":
    main()

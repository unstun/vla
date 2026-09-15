#!/usr/bin/env python3
"""Load pinned OmniVLA-edge and CLIP once, then run the frozen matrix."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import random
import sys
import time
import traceback
from pathlib import Path

from audit_contract import (
    base_record,
    canonical_bytes,
    retain_record,
    scheduled_attempts,
    sha256_file,
    utc_now,
    validate_record,
)


SOURCE_COMMIT = "5182600cb4a9ee07684e17cdd2a6cbafc56b8a68"
CHECKPOINT_REVISION = "b1361b7e24f101edea795a98b00a826b61a97394"
CHECKPOINT_SHA256 = "f93b056f124380899fce3e087a5c2b41ce4d8c07e211daad52b6ebf02e80d04d"
CLIP_SHA256 = "40d365715913c9da98579312b702a82c18be219cc2a73407c4526f58eba950af"


def event(path: Path, kind: str, **fields) -> None:
    payload = {"utc": utc_now(), "kind": kind}
    payload.update(fields)
    with path.open("ab") as stream:
        stream.write(canonical_bytes(payload))


class EdgeEngine:
    """Receive-only callable extraction of the pinned upstream edge path."""

    def __init__(self, upstream_root: Path, checkpoint_path: Path, clip_root: Path) -> None:
        import numpy as np
        import torch
        from PIL import Image

        self._np = np
        self._torch = torch
        self._Image = Image
        inference_dir = upstream_root / "inference"
        sys.path.insert(0, str(inference_dir))
        os.environ["OMNIVLA_CLIP_ROOT"] = str(clip_root)
        specification = importlib.util.spec_from_file_location(
            "omnivla_pinned_edge", str(inference_dir / "run_omnivla_edge.py")
        )
        if specification is None or specification.loader is None:
            raise RuntimeError("could not import pinned edge runner")
        module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(module)
        module.pose_goal = False
        module.satellite = False
        module.image_goal = False
        module.lan_prompt = True
        module.imgsize = (96, 96)
        module.imgsize_clip = (224, 224)
        module.device = torch.device("cuda:0")
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is unavailable")
        params = {
            "model_type": "omnivla-edge",
            "len_traj_pred": 8,
            "learn_angle": True,
            "context_size": 5,
            "obs_encoder": "efficientnet-b0",
            "encoding_size": 256,
            "obs_encoding_size": 1024,
            "goal_encoding_size": 1024,
            "late_fusion": False,
            "mha_num_attention_heads": 4,
            "mha_num_attention_layers": 4,
            "mha_ff_dim_factor": 4,
            "clip_type": "ViT-B/32",
        }
        model, text_encoder, _ = module.load_model(str(checkpoint_path), params, module.device)
        module.model = model.to(module.device).eval()
        module.text_encoder = text_encoder.to(module.device).eval()
        module.mask_360_pil_96 = np.ones((96, 96, 3), dtype=np.float32)
        module.mask_360_pil_224 = np.ones((224, 224, 3), dtype=np.float32)
        self._module = module
        goal_utm = (0.0, 0.0)
        goal_image = Image.open(inference_dir / "goal_img.jpg").convert("RGB").resize((96, 96))
        self._inference = module.Inference(
            save_dir="/dev/null",
            lan_inst_prompt="move forward",
            goal_utm=goal_utm,
            goal_compass=0.0,
            goal_image_PIL=goal_image,
        )

    def infer(self, image_path: Path, instruction: str):
        module = self._module
        np = self._np
        torch = self._torch
        image = self._Image.open(image_path).convert("RGB")
        image_96 = image.resize(module.imgsize)
        image_224 = image.resize(module.imgsize_clip)
        context = [image_96] * 6
        obs_images = module.transform_images_PIL_mask(context, module.mask_360_pil_96)
        split = torch.split(obs_images.to(module.device), 3, dim=1)
        obs_image_cur = split[-1].to(module.device)
        obs_images = torch.cat(split, dim=1).to(module.device)
        cur_large_img = module.transform_images_PIL_mask(
            image_224, module.mask_360_pil_224
        ).to(module.device)
        satellite = self._Image.new("RGB", (352, 352), color=(0, 0, 0))
        current_map = module.transform_images_map(satellite)
        goal_map = module.transform_images_map(satellite)
        map_images = torch.cat(
            (current_map.to(module.device), goal_map.to(module.device), obs_image_cur), axis=1
        )
        goal_pose = torch.tensor([[10.0, -100.0, 0.0, -1.0]], dtype=torch.float32).to(
            module.device
        )
        language_tokens = module.clip.tokenize(instruction, truncate=True).to(module.device)
        goal_image = module.transform_images_PIL_mask(
            self._inference.goal_image_PIL, module.mask_360_pil_96
        ).to(module.device)
        batch = {
            "obs_images": obs_images,
            "goal_pose_torch": goal_pose,
            "map_images": map_images,
            "goal_image": goal_image,
            "obj_inst_lan": language_tokens,
            "cur_large_img": cur_large_img,
        }
        with torch.no_grad():
            actions, modality = self._inference.run_forward_pass(
                model=module.model,
                batch=batch,
                device_id=module.device,
                mode="train",
                idrun=self._inference.count_id,
            )
        self._inference.count_id += 1
        modality_id = int(modality.detach().cpu().numpy()[0])
        if modality_id != 7:
            raise RuntimeError("language-only modality id must be 7")
        trajectory = actions.float().detach().cpu().numpy()
        if trajectory.shape != (1, 8, 4):
            raise RuntimeError("unexpected output shape: %r" % (trajectory.shape,))
        return trajectory[0].astype(float).tolist()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-root", type=Path, required=True)
    parser.add_argument("--upstream-root", type=Path, required=True)
    parser.add_argument("--checkpoint-path", type=Path, required=True)
    parser.add_argument("--clip-root", type=Path, required=True)
    args = parser.parse_args()
    experiment_root = args.experiment_root.resolve()
    checkpoint_path = args.checkpoint_path.resolve()
    clip_path = args.clip_root.resolve() / "ViT-B-32.pt"
    if sha256_file(checkpoint_path) != CHECKPOINT_SHA256:
        raise SystemExit("edge checkpoint identity mismatch")
    if sha256_file(clip_path) != CLIP_SHA256:
        raise SystemExit("CLIP identity mismatch")
    import numpy as np
    import torch

    random.seed(0)
    np.random.seed(0)
    torch.manual_seed(0)
    fixtures = json.loads((experiment_root / "fixtures.json").read_text(encoding="utf-8"))
    records_dir = experiment_root / "raw/omnivla_edge/records"
    events_path = experiment_root / "raw/omnivla_edge/attempt_events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    if records_dir.exists() and any(records_dir.iterdir()):
        raise SystemExit("refusing to reuse immutable edge records directory")
    event(events_path, "batch_start", model_id="omnivla_edge")
    load_started = time.monotonic()
    engine = EdgeEngine(args.upstream_root.resolve(), checkpoint_path, args.clip_root.resolve())
    load_seconds = time.monotonic() - load_started
    event(events_path, "model_loaded", load_seconds=load_seconds)
    success_count = 0
    failure_count = 0
    for row in scheduled_attempts("omnivla_edge"):
        record = base_record(
            row, fixtures, SOURCE_COMMIT, CHECKPOINT_REVISION, "CLIP tokenize({instruction})"
        )
        record["host"] = {"role": "orin64", "hostname": None}
        record["model_load_seconds"] = load_seconds
        run_id = record["run_id"]
        event(events_path, "attempt_start", run_id=run_id)
        image_path = experiment_root / fixtures["images"][row["image_id"]]["path"]
        if sha256_file(image_path) != fixtures["images"][row["image_id"]]["sha256"]:
            raise RuntimeError("fixture identity changed during batch")
        started = time.monotonic()
        try:
            trajectory = engine.infer(image_path, record["instruction"])
            elapsed = time.monotonic() - started
            record.update(
                {
                    "status": "success",
                    "trajectory_normalized": trajectory,
                    "failure": None,
                    "timings_seconds": {
                        "preprocess_and_forward": elapsed,
                        "forward_only": None,
                        "postprocess": None,
                    },
                    "process": {"exit_code": 0, "warnings": []},
                }
            )
            validate_record(
                record,
                expected_model_id="omnivla_edge",
                expected_source_commit=SOURCE_COMMIT,
                expected_checkpoint_revision=CHECKPOINT_REVISION,
            )
            success_count += 1
            event(events_path, "attempt_success", run_id=run_id, elapsed_seconds=elapsed)
        except Exception as exc:
            elapsed = time.monotonic() - started
            record.update(
                {
                    "status": "failure",
                    "trajectory_normalized": None,
                    "failure": {
                        "type": type(exc).__name__,
                        "reason": str(exc),
                        "traceback": traceback.format_exc(),
                    },
                    "timings_seconds": {
                        "preprocess_and_forward": elapsed,
                        "forward_only": None,
                        "postprocess": None,
                    },
                    "process": {"exit_code": 1, "warnings": []},
                }
            )
            failure_count += 1
            event(events_path, "attempt_failure", run_id=run_id, reason=str(exc))
        retain_record(record, records_dir)
    event(events_path, "batch_end", success_count=success_count, failure_count=failure_count, retained_count=success_count + failure_count)
    print(json.dumps({"success": success_count, "failure": failure_count, "retained": success_count + failure_count}))


if __name__ == "__main__":
    main()


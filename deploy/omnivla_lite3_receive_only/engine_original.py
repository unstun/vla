"""Callable adapter for the pinned upstream OmniVLA-original inference code."""

from io import BytesIO
import importlib.util
import os
from pathlib import Path
import sys
from typing import List


class OriginalEngine:
    """Load the pinned model once and expose language-only trajectory inference."""

    def __init__(self, upstream_root: Path, checkpoint_path: Path) -> None:
        upstream_root = upstream_root.resolve()
        checkpoint_path = checkpoint_path.resolve()
        script_path = upstream_root / "inference" / "run_omnivla.py"
        if not script_path.is_file():
            raise RuntimeError("pinned run_omnivla.py is missing: %s" % script_path)
        if not checkpoint_path.is_dir():
            raise RuntimeError("pinned checkpoint directory is missing: %s" % checkpoint_path)

        sys.path.insert(0, str(upstream_root))
        os.environ["OMNIVLA_ORIGINAL_PATH"] = str(checkpoint_path)
        os.environ.setdefault("OMNIVLA_CUDA_MEM_FRACTION", "0.45")
        specification = importlib.util.spec_from_file_location(
            "omnivla_pinned_run_omnivla", str(script_path)
        )
        if specification is None or specification.loader is None:
            raise RuntimeError("could not import pinned OmniVLA script")
        module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(module)

        module.pose_goal = False
        module.satellite = False
        module.image_goal = False
        module.lan_prompt = True
        components = module.define_model(module.InferenceConfig())
        (
            module.vla,
            module.action_head,
            module.pose_projector,
            module.device_id,
            module.NUM_PATCHES,
            module.action_tokenizer,
            module.processor,
        ) = components

        from PIL import Image

        self._module = module
        self._placeholder = Image.new("RGB", (1280, 720), color=(0, 0, 0))
        self._inference = module.Inference(
            save_dir="/dev/null",
            lan_inst_prompt="move forward",
            goal_utm=(0.0, 0.0),
            goal_compass=0.0,
            goal_image_PIL=self._placeholder,
            action_tokenizer=module.action_tokenizer,
            processor=module.processor,
        )

    def infer(self, jpeg: bytes, instruction: str) -> List[List[float]]:
        module = self._module
        from PIL import Image
        import numpy as np

        current_image = Image.open(BytesIO(jpeg)).convert("RGB")
        goal_pose = np.asarray([0.0, 0.0, 1.0, 0.0], dtype=np.float64)
        batch = self._inference.data_transformer_omnivla(
            current_image,
            instruction,
            self._placeholder,
            goal_pose,
            prompt_builder=module.PurePromptBuilder,
            action_tokenizer=module.action_tokenizer,
            processor=module.processor,
        )
        actions, modality_id = self._inference.run_forward_pass(
            vla=module.vla.eval(),
            action_head=module.action_head.eval(),
            noisy_action_projector=None,
            pose_projector=module.pose_projector.eval(),
            batch=batch,
            action_tokenizer=module.action_tokenizer,
            device_id=module.device_id,
            use_l1_regression=True,
            use_diffusion=False,
            use_film=False,
            num_patches=module.NUM_PATCHES,
            compute_diffusion_l1=False,
            num_diffusion_steps_train=None,
            mode="train",
            idrun=self._inference.count_id,
        )
        self._inference.count_id += 1
        modality = int(modality_id.detach().cpu().numpy()[0])
        if modality != 7:
            raise RuntimeError("language-only modality id must be 7, got %d" % modality)
        trajectory = actions.float().detach().cpu().numpy()
        if trajectory.shape != (1, 8, 4):
            raise RuntimeError("unexpected model output shape: %r" % (trajectory.shape,))
        return trajectory[0].astype(float).tolist()


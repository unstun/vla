"""Contact safety must not change the pinned policy's privileged inputs."""
import ast
from pathlib import Path
from types import SimpleNamespace

import torch

ROOT = Path(__file__).resolve().parents[3]
V12 = ROOT / "references/locomotion/2026-08-13_v12_model149999/source/v12_runtime_20260718_recovered"


def test_native_contact_feature_shape_and_runner_history_preservation():
    path = V12 / "source/robot_lab/robot_lab/tasks/go2/mdp/observations.py"
    function = next(n for n in ast.parse(path.read_text()).body
                    if isinstance(n, ast.FunctionDef) and n.name == "foot_contact_force_norm")
    function.returns = None
    for arg in function.args.args:
        arg.annotation = None
    namespace = {"torch": torch}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])),
                 str(path), "exec"), namespace)
    sensor_cfg = SimpleNamespace(name="contact_forces", body_ids=[0, 1, 2, 3])
    dimensions = []
    for history in (3, 4):
        sensor = SimpleNamespace(data=SimpleNamespace(net_forces_w_history=torch.zeros(1, history, 8, 3)))
        env = SimpleNamespace(scene=SimpleNamespace(sensors={"contact_forces": sensor}))
        dimensions.append(namespace["foot_contact_force_norm"](env, sensor_cfg).shape[-1])
    assert dimensions == [16, 20]  # The failed run added four privileged features.
    runner = ROOT / "integration/lite3_sim_bridge/lite3_sim_bridge/run_pct_scan_building.py"
    assignments = [target for node in ast.walk(ast.parse(runner.read_text()))
                   if isinstance(node, ast.Assign) for target in node.targets]
    assert not any(isinstance(target, ast.Attribute) and target.attr == "history_length"
                   for target in assignments)

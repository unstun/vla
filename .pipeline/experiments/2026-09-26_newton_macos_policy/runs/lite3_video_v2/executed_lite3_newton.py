"""Pinned Lite3 controller on Newton's supported native MuJoCo CPU solver."""
import hashlib
import json
from pathlib import Path
import sys

import mujoco
import numpy as np
import onnxruntime as ort
import warp as wp
import newton

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "references"))
from lite3_reference.robots.lite3 import (
    EFFORT, History, JOINT_NAMES, POLICY_DT, POLICY_SHA256, Q0, SIM_DT, SPEED, rotation_matrix,
)


def verify_inputs():
    identity = json.loads((BASE / "setup/lite3_inputs.json").read_text())
    for item in identity["records"]:
        if hashlib.sha256((BASE / item["path"]).read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"Pinned input changed: {item['path']}")
    return identity


def make_session():
    policy = BASE / "policy/policy_stateless_h10.onnx"
    if hashlib.sha256(policy.read_bytes()).hexdigest() != POLICY_SHA256:
        raise ValueError("Policy hash mismatch")
    options = ort.SessionOptions()
    options.intra_op_num_threads = options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(policy), sess_options=options, providers=["CPUExecutionProvider"])
    inp, out = session.get_inputs()[0], session.get_outputs()[0]
    if inp.shape != [1, 450] or inp.type != "tensor(float)" or out.shape != [1, 12]:
        raise ValueError("Lite3 ONNX interface mismatch")
    return session, inp.name, out.name


class Lite3Newton:
    def __init__(self):
        self.input_identity = verify_inputs()
        self.session, self.input_name, self.output_name = make_session()
        builder = newton.ModelBuilder(up_axis=newton.Axis.Z)
        newton.solvers.SolverMuJoCo.register_custom_attributes(builder)
        builder.add_mjcf(str(BASE / "assets/lite3/lite3.xml"), floating=True,
                         enable_self_collisions=False, collapse_fixed_joints=True, ctrl_direct=True)
        builder.add_ground_plane(cfg=newton.ModelBuilder.ShapeConfig(mu=1.0))
        labels = builder.joint_label
        self.joints = []
        for name in JOINT_NAMES:
            matches = [i for i, label in enumerate(labels) if label.rsplit("/", 1)[-1] == name]
            if len(matches) != 1:
                raise ValueError(f"Expected one Newton joint for {name}; labels={labels}")
            self.joints.append(matches[0])
        self.q_indices = np.array([builder.joint_q_start[i] for i in self.joints])
        self.qd_indices = np.array([builder.joint_qd_start[i] for i in self.joints])
        if len(builder.joint_q) != 19 or len(builder.joint_qd) != 18:
            raise ValueError(f"Expected a free base and 12 hinges, got nq={len(builder.joint_q)}, nv={len(builder.joint_qd)}")
        builder.joint_q[:7] = [0.0, 0.0, .35, 0.0, 0.0, 0.0, 1.0]
        for index, value in zip(self.q_indices, Q0, strict=True):
            builder.joint_q[index] = float(value)
        self.model = builder.finalize(device="cpu")
        self.model.set_gravity((0, 0, -9.81))
        # This is an explicit solver choice, distinct from the Go2 MuJoCo-Warp trial.
        self.solver = newton.solvers.SolverMuJoCo(self.model, use_mujoco_cpu=True,
                                                solver="newton", nconmax=100, njmax=300,
                                                update_data_interval=0)
        self.state = self.model.state()
        self.next_state = self.model.state()
        self.control = self.model.control()
        newton.eval_fk(self.model, self.state.joint_q, self.state.joint_qd, self.state)
        # Public reset synchronizes immediately when update_data_interval != 1.
        # Afterwards native MuJoCo retains its own coordinates between steps.
        self.solver.reset(self.state)
        self.history = History()
        self.last_action = np.zeros(12, np.float32)
        self.target = Q0.copy()
        self.steps = 0
        self.observation = np.zeros(45, np.float32)
        self.policy_input = np.zeros((1, 450), np.float32)
        self.torque = np.zeros(12, np.float32)
        mjmodel = self.solver.mj_model
        self.mj_joints = np.array([mjmodel.joint(labels[i].replace("/", "_")).id for i in self.joints])
        self.mj_q_indices = mjmodel.jnt_qposadr[self.mj_joints]
        self.mj_qd_indices = mjmodel.jnt_dofadr[self.mj_joints]
        # Newton v1.6 exports direct actuators without names. Resolve transmission
        # targets and require a one-to-one mapping instead of guessing by position.
        actuator_ids = []
        for joint in self.mj_joints:
            matches = np.flatnonzero(mjmodel.actuator_trnid[:, 0] == joint)
            if len(matches) != 1:
                raise ValueError(f"Expected one actuator for native joint {joint}, got {matches}")
            actuator_ids.append(int(matches[0]))
        self.actuators = np.array(actuator_ids)
        if mjmodel.nu != 12 or not np.array_equal(mjmodel.actuator_trnid[self.actuators, 0], self.mj_joints):
            raise ValueError("Lite3 actuator/joint mapping mismatch")
        if not np.array_equal(self.actuators, np.arange(12)):
            raise ValueError("Direct-control import changed the declared MJCF actuator order")
        self.max_observation_mapping_error = 0.0
        self.max_applied_torque_error = 0.0

    def infer(self, command):
        command = np.asarray(command, dtype=np.float32)
        if command.shape != (3,) or not np.isfinite(command).all():
            raise ValueError("Finite vx, vy, yaw-rate required")
        q = self.state.joint_q.numpy()
        qd = self.state.joint_qd.numpy()
        rotation = rotation_matrix(q[[6, 3, 4, 5]])
        angular_body = rotation.T @ qd[3:6]
        observation = np.concatenate([
            np.clip(angular_body, -100, 100) * .25,
            rotation.T @ np.array([0., 0., -1.]), command,
            np.clip(q[self.q_indices] - Q0, -100, 100),
            np.clip(qd[self.qd_indices], -100, 100) * .05,
            np.clip(self.last_action, -100, 100),
        ]).astype(np.float32)
        # Independent native MuJoCo coordinates guard Newton's xyzw/world-angular conversion.
        data = self.solver.mj_data
        native_rotation = rotation_matrix(data.qpos[3:7])
        native_obs = np.concatenate([
            np.clip(data.qvel[3:6], -100, 100) * .25,
            native_rotation.T @ np.array([0., 0., -1.]), command,
            np.clip(data.qpos[self.mj_q_indices] - Q0, -100, 100),
            np.clip(data.qvel[self.mj_qd_indices], -100, 100) * .05,
            np.clip(self.last_action, -100, 100),
        ]).astype(np.float32)
        error = float(np.max(np.abs(observation - native_obs)))
        self.max_observation_mapping_error = max(error, self.max_observation_mapping_error)
        if error > 1e-4:
            raise ValueError(f"Newton-to-native observation mismatch: {error}")
        self.observation = observation
        self.policy_input = self.history.push(observation)
        action = self.session.run([self.output_name], {self.input_name: self.policy_input})[0]
        if action.shape != (1, 12) or not np.isfinite(action).all():
            raise ValueError("Invalid Lite3 policy output")
        self.last_action = action[0].astype(np.float32)
        self.target = Q0 + .25 * self.last_action

    def step(self, command):
        self.infer(command)
        for _ in range(round(POLICY_DT / SIM_DT)):
            q = self.state.joint_q.numpy()[self.q_indices]
            qd = self.state.joint_qd.numpy()[self.qd_indices]
            requested = 20.0 * (self.target - q) - .5 * qd
            high = np.clip(EFFORT * (1.0 - qd / SPEED), 0.0, EFFORT)
            low = np.clip(EFFORT * (-1.0 - qd / SPEED), -EFFORT, 0.0)
            self.torque = np.clip(requested, low, high)
            self.control.mujoco.ctrl.assign(self.torque)
            self.state.clear_forces()
            self.solver.step(self.state, self.next_state, self.control, None, SIM_DT)
            self.state, self.next_state = self.next_state, self.state
            self.steps += 1
            applied = self.solver.mj_data.qfrc_actuator[self.mj_qd_indices]
            error = float(np.max(np.abs(applied - self.torque)))
            self.max_applied_torque_error = max(error, self.max_applied_torque_error)
            if error > 1e-4 or not np.isfinite(self.solver.mj_data.qpos).all():
                raise ValueError(f"Invalid applied force/state at physics step {self.steps}")

    def telemetry(self):
        q = self.state.joint_q.numpy()
        qd = self.state.joint_qd.numpy()
        data = self.solver.mj_data
        arrays = (q, qd, self.policy_input, self.last_action, self.torque)
        if not all(np.isfinite(a).all() for a in arrays):
            raise ValueError("Nonfinite Lite3 telemetry")
        rotation = rotation_matrix(q[[6, 3, 4, 5]])
        return {"physics_steps": self.steps, "physics_time_s": float(data.time),
                "joint_q": q.tolist(), "joint_qd": qd.tolist(),
                "base_up_z": float(rotation[2, 2]), "contacts": int(data.ncon),
                "observation": self.observation.tolist(), "policy_input": self.policy_input[0].tolist(),
                "action": self.last_action.tolist(), "target": self.target.tolist(),
                "torque": self.torque.tolist(),
                "applied_torque": data.qfrc_actuator[self.mj_qd_indices].tolist(),
                "observation_mapping_max_abs": self.max_observation_mapping_error,
                "applied_torque_max_abs": self.max_applied_torque_error}


def check_golden_policy():
    verify_inputs()
    session, inp, out = make_session()
    golden = np.load(BASE / "policy/parity_golden_trace.npz")
    history = History()
    maximum = 0.0
    for observation, expected in zip(golden["single_observations"], golden["expected_actions"], strict=True):
        actual = session.run([out], {inp: history.push(observation)})[0][0]
        if not np.isfinite(actual).all():
            raise ValueError("Nonfinite golden policy output")
        maximum = max(maximum, float(np.max(np.abs(actual - expected))))
    if maximum > .01:
        raise ValueError(f"Pinned golden-trace tolerance exceeded: {maximum}")
    return {"frames": len(golden["single_observations"]), "max_abs_error": maximum, "limit": .01,
            "history_layout": "term-major oldest-to-newest, repeated first frame", "passed": True}

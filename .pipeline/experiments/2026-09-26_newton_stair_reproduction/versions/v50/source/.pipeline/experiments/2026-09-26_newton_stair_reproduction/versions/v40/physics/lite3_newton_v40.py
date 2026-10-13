"""Pinned Lite3 controller with explicit CPU/CUDA physics model selection."""
import hashlib
import json
from pathlib import Path
import sys

import mujoco
import numpy as np
import onnxruntime as ort
import warp as wp
import newton

BASE = Path(__file__).resolve().parents[4] / "2026-09-26_newton_macos_policy"
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
    def __init__(self, *, robot_source=None, scene_builder=None, spawn_xyz=(0., 0., .35),
                 spawn_yaw=0.0, newton_contacts=False, automatic_contact_capacity=False,
                 contact_observer=None, startup_mode="policy", stance_hold=False,
                 model_device="cpu", use_solver_graph=False):
        if not isinstance(use_solver_graph, bool):
            raise ValueError("use_solver_graph must be bool")
        if use_solver_graph and model_device != "cpu":
            raise ValueError("This numerically qualified graph candidate requires cpu")
        if model_device not in ("cpu", "cuda:0"):
            raise ValueError("model_device must be cpu or cuda:0")
        if model_device != "cpu" and not newton_contacts:
            raise ValueError("CUDA requires the selected MuJoCo-Warp/Newton-contact path")
        if startup_mode not in ("policy", "pd_stand", "factory_pd"):
            raise ValueError("Unknown startup mode: " + str(startup_mode))
        self.startup_mode = startup_mode
        self.startup = None
        if startup_mode == "pd_stand":
            from pd_startup import PDStartup, SDK_PREPARE
            self.startup = PDStartup(Q0)
        if startup_mode == "factory_pd":
            from pd_startup import SDK_PREPARE
            if not stance_hold:
                raise ValueError("Factory startup requires PD stance hold")
        self.factory_startup_complete = startup_mode != "factory_pd"
        initial_q = SDK_PREPARE if startup_mode in ("pd_stand", "factory_pd") else Q0
        self.input_identity = verify_inputs()
        self.session, self.input_name, self.output_name = make_session()
        builder = newton.ModelBuilder(up_axis=newton.Axis.Z)
        newton.solvers.SolverMuJoCo.register_custom_attributes(builder)
        robot_source = Path(robot_source) if robot_source is not None else BASE / "assets/lite3/lite3.xml"
        self.direct_joint_forces = robot_source.suffix == ".urdf"
        if self.direct_joint_forces:
            builder.add_urdf(str(robot_source), floating=True,
                             enable_self_collisions=False, collapse_fixed_joints=True)
        else:
            builder.add_mjcf(str(robot_source), floating=True,
                             enable_self_collisions=False, collapse_fixed_joints=True, ctrl_direct=True)
        if scene_builder is None:
            builder.add_ground_plane(cfg=newton.ModelBuilder.ShapeConfig(mu=1.0))
        else:
            scene_builder(builder)
        labels = builder.joint_label
        self.joints = []
        for name in JOINT_NAMES:
            matches = [i for i, label in enumerate(labels) if label.rsplit("/", 1)[-1] == name]
            if len(matches) != 1:
                raise ValueError(f"Expected one Newton joint for {name}; labels={labels}")
            self.joints.append(matches[0])
        self.q_indices = np.array([builder.joint_q_start[i] for i in self.joints])
        self.qd_indices = np.array([builder.joint_qd_start[i] for i in self.joints])
        if self.direct_joint_forces:
            # URDF import chooses POSITION drives despite URDF containing no
            # policy gains. The archived controller supplies saturated torques.
            for index in self.qd_indices:
                builder.joint_target_mode[index] = int(newton.JointTargetMode.NONE)
                builder.joint_target_ke[index] = 0.0
                builder.joint_target_kd[index] = 0.0
        if len(builder.joint_q) != 19 or len(builder.joint_qd) != 18:
            raise ValueError(f"Expected a free base and 12 hinges, got nq={len(builder.joint_q)}, nv={len(builder.joint_qd)}")
        builder.joint_q[:7] = [*spawn_xyz, 0.0, 0.0, float(np.sin(spawn_yaw / 2)), float(np.cos(spawn_yaw / 2))]
        for index, value in zip(self.q_indices, initial_q, strict=True):
            builder.joint_q[index] = float(value)
        self.model = builder.finalize(device=model_device)
        self.model.set_gravity((0, 0, -9.81))
        # This is an explicit solver choice, distinct from the Go2 MuJoCo-Warp trial.
        self.solver = newton.solvers.SolverMuJoCo(self.model, use_mujoco_cpu=not newton_contacts,
                                                use_mujoco_contacts=not newton_contacts,
                                                solver="newton",
                                                nconmax=None if automatic_contact_capacity else 100,
                                                njmax=None if automatic_contact_capacity else 300,
                                                update_data_interval=0)
        self.collision_pipeline = newton.CollisionPipeline(self.model) if newton_contacts else None
        self.contacts = self.collision_pipeline.contacts() if newton_contacts else None
        self.contact_capacity = self.solver.get_max_contact_count() if newton_contacts else None
        self.contact_observer = contact_observer
        self.physics_observer = None
        self.state = self.model.state()
        self.next_state = self.model.state()
        self.control = self.model.control()
        newton.eval_fk(self.model, self.state.joint_q, self.state.joint_qd, self.state)
        # Public reset synchronizes immediately when update_data_interval != 1.
        # Afterwards native MuJoCo retains its own coordinates between steps.
        self.solver.reset(self.state)
        self.history = History()
        self.last_action = np.zeros(12, np.float32)
        self.target = initial_q.copy()
        self.policy_target = Q0.copy()
        self.target_velocity = np.zeros(12, np.float32)
        self.motor_kp, self.motor_kd = (20., .5) if self.startup is None else (0., .7)
        self.policy_calls = 0
        self.effective_command = np.zeros(3, np.float32)
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
        if not self.direct_joint_forces:
            for joint in self.mj_joints:
                matches = np.flatnonzero(mjmodel.actuator_trnid[:, 0] == joint)
                if len(matches) != 1:
                    raise ValueError(f"Expected one actuator for native joint {joint}, got {matches}")
                actuator_ids.append(int(matches[0]))
        self.actuators = np.array(actuator_ids)
        if self.direct_joint_forces and mjmodel.nu != 0:
            raise ValueError("Unexpected implicit actuators in the original URDF")
        if not self.direct_joint_forces and (mjmodel.nu != 12 or not np.array_equal(mjmodel.actuator_trnid[self.actuators, 0], self.mj_joints)):
            raise ValueError("Lite3 actuator/joint mapping mismatch")
        if not self.direct_joint_forces and not np.array_equal(self.actuators, np.arange(12)):
            raise ValueError("Direct-control import changed the declared MJCF actuator order")
        self.max_observation_mapping_error = 0.0
        self.max_applied_torque_error = 0.0
        self.stance = None
        if stance_hold:
            from newton_stance import NewtonStance
            self.stance = NewtonStance(self)
        if use_solver_graph:
            from solver_graph_step import SolverGraphStep
            self.solver_graph = SolverGraphStep(self.solver, self.state, self.next_state,
                                                self.control, self.contacts)
            self.solver.step = self.solver_graph

    def native_array(self, name):
        if self.solver.use_mujoco_cpu:
            return np.asarray(getattr(self.solver.mj_data, name))
        return getattr(self.solver.mjw_data, name).numpy()[0]

    def physics_time(self):
        if self.solver.use_mujoco_cpu:
            return float(self.solver.mj_data.time)
        return float(self.solver.mjw_data.time.numpy()[0])

    def applied_torque(self):
        return self.native_array("qfrc_applied" if self.direct_joint_forces else "qfrc_actuator")[self.mj_qd_indices]

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
        native_q, native_qd = self.native_array("qpos"), self.native_array("qvel")
        native_rotation = rotation_matrix(native_q[3:7])
        native_obs = np.concatenate([
            np.clip(native_qd[3:6], -100, 100) * .25,
            native_rotation.T @ np.array([0., 0., -1.]), command,
            np.clip(native_q[self.mj_q_indices] - Q0, -100, 100),
            np.clip(native_qd[self.mj_qd_indices], -100, 100) * .05,
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
        self.policy_target = self.target.copy()
        self.policy_calls += 1

    def step(self, command):
        command = np.asarray(command, dtype=np.float32)
        if command.shape != (3,) or not np.isfinite(command).all():
            raise ValueError("Finite vx, vy, yaw-rate required")
        if not self.factory_startup_complete:
            raise RuntimeError("Factory initialization must finish before navigation updates")
        if self.startup is not None:
            q, qd = self.state.joint_q.numpy(), self.state.joint_qd.numpy()
            self.startup.advance(self.steps * SIM_DT, q[self.q_indices], qd[self.qd_indices],
                                 float(q[2]), float(rotation_matrix(q[[6, 3, 4, 5]])[2, 2]),
                                 float(np.linalg.norm(qd[:3])), float(np.linalg.norm(qd[3:6])))
        self.effective_command = command.copy() if self.navigation_ready else np.zeros(3, np.float32)
        previous_target = self.target.copy()
        previous_kp, previous_kd = np.copy(self.motor_kp), np.copy(self.motor_kd)
        if self.startup is None or self.startup.phase in ("handoff", "policy"):
            self.infer(self.effective_command)
        hold_active = self.stance is not None and self.navigation_ready
        if hold_active:
            self.stance.update(self.effective_command, previous_target, previous_kp, previous_kd)
        for _ in range(round(POLICY_DT / SIM_DT)):
            if self.startup is not None and not hold_active:
                self.target, self.target_velocity, self.motor_kp, self.motor_kd = self.startup.motor_command(
                    self.steps * SIM_DT, self.policy_target)
            self._motor_substep()

    @property
    def navigation_ready(self):
        return self.factory_startup_complete and (self.startup is None or self.startup.ready)

    def _motor_substep(self, *, feedforward_torque=None):
        q = self.state.joint_q.numpy()[self.q_indices]
        qd = self.state.joint_qd.numpy()[self.qd_indices]
        requested = self.motor_kp * (self.target - q) + self.motor_kd * (self.target_velocity - qd)
        if feedforward_torque is not None:
            feedforward_torque = np.asarray(feedforward_torque, dtype=np.float64)
            if feedforward_torque.shape != (12,) or not np.isfinite(feedforward_torque).all():
                raise ValueError("Expected twelve finite feedforward joint torques")
            requested = requested + feedforward_torque
        high = np.clip(EFFORT * (1.0 - qd / SPEED), 0.0, EFFORT)
        low = np.clip(EFFORT * (-1.0 - qd / SPEED), -EFFORT, 0.0)
        self.torque = np.clip(requested, low, high)
        if self.direct_joint_forces:
            forces = np.zeros(self.model.joint_dof_count, dtype=np.float32)
            forces[self.qd_indices] = self.torque
            self.control.joint_f.assign(forces)
        else:
            self.control.mujoco.ctrl.assign(self.torque)
        self.state.clear_forces()
        if self.collision_pipeline is not None:
            self.collision_pipeline.collide(self.state, self.contacts)
            contact_count = int(self.contacts.rigid_contact_count.numpy()[0])
            if contact_count > min(self.contact_capacity, self.contacts.rigid_contact_max):
                raise RuntimeError(f"Contact capacity exceeded before solver step: {contact_count} > {self.contact_capacity}")
            if self.contact_observer is not None:
                self.contact_observer(self.state, self.contacts)
        elif self.contact_observer is not None:
            self.contact_observer(self.state, None)
        self.solver.step(self.state, self.next_state, self.control, self.contacts, SIM_DT)
        self.state, self.next_state = self.next_state, self.state
        self.steps += 1
        applied = self.applied_torque()
        error = float(np.max(np.abs(applied - self.torque)))
        self.max_applied_torque_error = max(error, self.max_applied_torque_error)
        if error > 1e-4 or not np.isfinite(self.native_array("qpos")).all():
            raise ValueError(f"Invalid applied force/state at physics step {self.steps}")
        if self.physics_observer is not None:
            self.physics_observer(self)

    def telemetry(self):
        q = self.state.joint_q.numpy()
        qd = self.state.joint_qd.numpy()
        arrays = (q, qd, self.policy_input, self.last_action, self.torque)
        if not all(np.isfinite(a).all() for a in arrays):
            raise ValueError("Nonfinite Lite3 telemetry")
        rotation = rotation_matrix(q[[6, 3, 4, 5]])
        contacts = int(self.solver.mj_data.ncon) if self.solver.use_mujoco_cpu else int(self.contacts.rigid_contact_count.numpy()[0])
        return {"physics_steps": self.steps, "physics_time_s": self.physics_time(),
                "startup_mode": self.startup_mode,
                "controller_phase": "policy" if self.startup is None else self.startup.phase,
                "navigation_ready": self.navigation_ready, "policy_calls": self.policy_calls,
                "effective_command": self.effective_command.tolist(),
                "motor_kp": np.asarray(self.motor_kp).tolist(), "motor_kd": np.asarray(self.motor_kd).tolist(),
                **({} if self.stance is None else self.stance.row),
                "target_velocity": self.target_velocity.tolist(),
                "joint_q": q.tolist(), "joint_qd": qd.tolist(),
                "base_up_z": float(rotation[2, 2]), "contacts": contacts,
                "observation": self.observation.tolist(), "policy_input": self.policy_input[0].tolist(),
                "action": self.last_action.tolist(), "target": self.target.tolist(),
                "torque": self.torque.tolist(),
                "applied_torque": self.applied_torque().tolist(),
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

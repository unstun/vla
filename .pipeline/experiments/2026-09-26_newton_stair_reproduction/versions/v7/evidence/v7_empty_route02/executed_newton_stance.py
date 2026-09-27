"""Newton sensor adapter around the existing VLA PD/RL state machine."""
import hashlib
import importlib.util
from pathlib import Path

import newton
import mujoco
import numpy as np

SOURCE = Path(__file__).resolve().parents[2] / "2026-09-16_pi_cortex_harnessvln/isaac_runner/stance_hold.py"
SOURCE_SHA256 = "9a97879a5d5ed2f7c9c3e327c1193b1c42cf079eaaf073a855afad53a7dbc306"
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise ValueError("Existing PD hold source identity changed")
spec = importlib.util.spec_from_file_location("vla_existing_stance_hold", SOURCE)
hold_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hold_module)


class NewtonStance:
    def __init__(self, robot):
        self.robot = robot
        feet = []
        bodies = robot.model.shape_body.numpy()
        kinds = robot.model.shape_type.numpy()
        scales = robot.model.shape_scale.numpy()
        for leg in hold_module.STANCE_HOLD_FOOT_ORDER:
            # Original fixed foot joints collapse into their SHANK bodies.
            # Resolve the unique authored 22 mm collision sphere, not shape IDs.
            matches = [i for i in range(robot.model.shape_count)
                       if bodies[i] >= 0 and robot.model.body_label[bodies[i]].rsplit("/", 1)[-1] == leg + "_SHANK"
                       and kinds[i] == int(newton.GeoType.SPHERE) and np.isclose(scales[i, 0], .022) and
                       robot.model.shape_flags.numpy()[i] & int(newton.ShapeFlags.COLLIDE_SHAPES)]
            if len(matches) != 1:
                raise ValueError(f"Expected one collision foot for {leg}: {matches}")
            feet.extend(matches)
        self.native_cpu = robot.solver.use_mujoco_cpu
        if self.native_cpu:
            mapping = robot.solver.mjc_geom_to_newton_shape.numpy()[0]
            self.geom_to_leg = {}
            for leg, shape in enumerate(feet):
                matches = np.flatnonzero(mapping == shape)
                if len(matches) != 1:
                    raise ValueError("Native foot geometry mapping is ambiguous")
                self.geom_to_leg[int(matches[0])] = leg
        else:
            self.sensor = newton.sensors.SensorContact(robot.model, sensing_shapes=feet)
        # Separate observation buffer: update_contacts must not overwrite the
        # collision pipeline's pre-step geometry/scoring buffer.
            self.contacts = newton.Contacts(robot.solver.get_max_contact_count(), 0,
                                           requested_attributes={"force"})
        self.hold = hold_module.StanceHold("auto", entry_kd="xfade1s",
            joint_lower=robot.model.joint_limit_lower.numpy()[robot.qd_indices],
            joint_upper=robot.model.joint_limit_upper.numpy()[robot.qd_indices])
        self.forces = np.zeros(4)
        self.row = {"stance_mode": "RL", "policy_owns_joints": True}
        self.boot_record = None

    def measure(self):
        if self.native_cpu:
            # Reuse the existing local MuJoCo _foot_contact_forces semantics.
            # Foot bodies are fixed-joint collapsed here, so match their unique
            # native sphere geometries instead of including SHANK contacts.
            model, data = self.robot.solver.mj_model, self.robot.solver.mj_data
            self.forces = np.zeros(4)
            wrench = np.zeros(6)
            for index in range(data.ncon):
                contact = data.contact[index]
                for geom in (contact.geom1, contact.geom2):
                    leg = self.geom_to_leg.get(int(geom))
                    if leg is not None:
                        mujoco.mj_contactForce(model, data, index, wrench)
                        self.forces[leg] += float(np.linalg.norm(wrench[:3]))
                        break
        else:
            self.robot.solver.update_contacts(self.contacts, self.robot.state)
            self.sensor.update(self.robot.state, self.contacts)
            self.forces = np.linalg.norm(self.sensor.total_force.numpy(), axis=1)
        if self.forces.shape != (4,) or not np.isfinite(self.forces).all():
            raise ValueError("Invalid FL/FR/HL/HR force measurement")
        return self.forces

    def boot_standing(self, target):
        """Port MJ boot_stand's existing-state hold, after measured factory stand.

        Unlike MJ's free-spawn boot, the seed is torque matched to the already
        loaded factory controller. This method does not move or reset physics.
        """
        target = np.asarray(target, dtype=np.float64)
        if target.shape != (12,) or not np.isfinite(target).all():
            raise ValueError("Invalid standing hold target")
        clipped = self.hold._clip_target(target)
        if not np.array_equal(clipped, target):
            raise ValueError("Factory-to-PD seed exceeds original joint limits")
        self.hold._hold_target = target.copy()
        self.hold._set_mode("FIXED_STAND", "measured_factory_stand", self.robot.physics_time())
        self.hold.progress = 1.0
        self.hold.counters["fixed_stand"] += 1
        self.robot.target = target.copy()
        self.robot.motor_kp = np.full(12, hold_module.HOLD_KP)
        self.robot.motor_kd = np.full(12, hold_module.HOLD_KD)
        self.robot.target_velocity = np.zeros(12)
        self.row = {"stance_mode": "FIXED_STAND", "policy_owns_joints": False,
                    "stance_reason": "measured_factory_stand"}
        self.boot_record = {"time_s": self.robot.physics_time(), "target": target.tolist()}

    def update(self, command, previous_target, previous_kp, previous_kd):
        from lite3_newton import Q0, rotation_matrix
        robot = self.robot
        q, qd = robot.state.joint_q.numpy(), robot.state.joint_qd.numpy()
        up = rotation_matrix(q[[6, 3, 4, 5]])[2, 2]
        output = self.hold.update(hold_module.HoldInput(
            now_s=robot.physics_time(), command=command,
            joint_pos=q[robot.q_indices], joint_vel=qd[robot.qd_indices],
            policy_target=robot.policy_target, applied_target=previous_target,
            applied_kp=np.broadcast_to(previous_kp, (12,)), applied_kd=np.broadcast_to(previous_kd, (12,)),
            linear_speed=float(np.linalg.norm(qd[:3])), angular_speed=float(np.linalg.norm(qd[3:6])),
            tilt_deg=float(np.degrees(np.arccos(np.clip(up, -1, 1)))), foot_forces=self.measure()))
        robot.target, robot.motor_kp, robot.motor_kd = output.target, output.kp, output.kd
        robot.target_velocity = np.zeros(12)
        # Match the original Isaac port: the next policy frame observes the
        # applied action, including PD hold/rejoin, not its unused policy output.
        if not output.policy_owns_joints:
            robot.last_action = ((robot.target - Q0) / .25).astype(np.float32)
        self.row = {"stance_mode": output.mode, "stance_reason": output.reason,
                    "stance_progress": output.progress, "policy_owns_joints": output.policy_owns_joints,
                    "foot_forces_n": self.forces.tolist()}

    def status(self):
        return {"source": str(SOURCE), "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                "contact_api": "MuJoCo mj_contactForce" if self.native_cpu else "Newton SensorContact + SolverMuJoCo.update_contacts",
                "boot": self.boot_record, "hold": self.hold.status()}

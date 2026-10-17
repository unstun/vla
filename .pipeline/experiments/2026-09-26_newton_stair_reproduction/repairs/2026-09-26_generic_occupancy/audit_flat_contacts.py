"""Replay recorded configurations through Newton collision queries, no stepping."""
import itertools
import json
import math
import os
from pathlib import Path
import sys

from materialize import BASE
sys.path.insert(0, str(BASE / "scripts"))
import numpy as np
from scipy.spatial.transform import Rotation
import warp as wp
wp.config.kernel_cache_dir = os.environ["WARP_CACHE_PATH"]
wp.init()
wp.set_device("cpu")
import newton
from newton._src.sim.contacts import contact_surface_separation
from flat_scene import FlatSceneRobot, FlatStaticHuman


def main():
    out = Path(os.environ["NEWTON_RUN_DIR"])
    source = BASE / "runs/flat_static_human_live_v3"
    rows = [json.loads(line) for line in (source / "telemetry.jsonl").open()]
    contact_index = next(i for i, row in enumerate(rows) if row["actor_contacts_scoring_only"])
    human = FlatStaticHuman(out)
    robot = FlatSceneRobot(human)
    shape_bodies = robot.model.shape_body.numpy()
    shape_flags = robot.model.shape_flags.numpy()
    collision_mask = (shape_bodies >= 0) & ((shape_flags & int(newton.ShapeFlags.COLLIDE_SHAPES)) != 0)
    records = []
    first_surface_contact = None
    for index in list(range(0, contact_index, 10)) + list(range(contact_index, len(rows))):
        row = rows[index]
        robot.state.joint_q.assign(np.asarray(row["joint_q"], dtype=np.float32))
        robot.state.joint_qd.assign(np.asarray(row["joint_qd"], dtype=np.float32))
        newton.eval_fk(robot.model, robot.state.joint_q, robot.state.joint_qd, robot.state)
        robot.collision_pipeline.collide(robot.state, robot.contacts)
        # Native broadphase expands each bound by the detection gap, which is
        # not the physical shape surface. Keep shape margin, remove gap only.
        gap = robot.model.shape_gap.numpy()[collision_mask, None]
        lower = robot.collision_pipeline.narrow_phase.shape_aabb_lower.numpy()[collision_mask] + gap
        upper = robot.collision_pipeline.narrow_phase.shape_aabb_upper.numpy()[collision_mask] - gap
        corners = np.concatenate([np.array(list(itertools.product(*zip(lo, hi)))) for lo, hi in zip(lower, upper)])
        pose = row["body_sensor"]
        q = pose["quaternion"]
        rotation = Rotation.from_quat(q[1:] + q[:1]).as_matrix()
        local = (corners - pose["position"]) @ rotation
        dx = np.minimum(np.abs(local[:, 0] - .18), np.abs(local[:, 0] + .18))
        required_radius = np.sqrt(dx * dx + local[:, 1] ** 2).max()
        record = {"state_sequence": row["state_sequence"], "physics_time_s": row["physics_time_s"],
                  "body_position": pose["position"], "local_aabb_min": local.min(axis=0).tolist(),
                  "local_aabb_max": local.max(axis=0).tolist(), "two_circle_radius_bound_m": float(required_radius),
                  "recorded_actor_contacts": row["actor_contacts_scoring_only"],
                  "replayed_actor_contacts": robot.actor_contact_count()}
        if index >= contact_index:
            count = int(robot.contacts.rigid_contact_count.numpy()[0])
            shape0 = robot.contacts.rigid_contact_shape0.numpy()[:count]
            shape1 = robot.contacts.rigid_contact_shape1.numpy()[:count]
            points0 = robot.contacts.rigid_contact_point0.numpy()[:count]
            points1 = robot.contacts.rigid_contact_point1.numpy()[:count]
            normals = robot.contacts.rigid_contact_normal.numpy()[:count]
            margin0 = robot.contacts.rigid_contact_margin0.numpy()[:count]
            margin1 = robot.contacts.rigid_contact_margin1.numpy()[:count]
            shape_margin = robot.model.shape_margin.numpy()
            contacts = []
            body_q = robot.state.body_q.numpy()
            for i in np.flatnonzero((shape0 == robot.human_contact_shape) | (shape1 == robot.human_contact_shape)):
                ids = [int(shape0[i]), int(shape1[i])]
                world_points = []
                for shape, point in zip(ids, (points0[i], points1[i])):
                    body = shape_bodies[shape]
                    world_points.append(point.tolist() if body < 0 else
                                        list(wp.transform_point(wp.transform(*body_q[body]), wp.vec3(*point))))
                contacts.append({"shapes": ids, "labels": [robot.model.shape_label[s] for s in ids],
                                 "world_points": world_points,
                                 "surface_separation_m": float(contact_surface_separation(
                                     wp.vec3(*world_points[0]), wp.vec3(*world_points[1]), wp.vec3(*normals[i]),
                                     float(margin0[i] - shape_margin[ids[0]]),
                                     float(margin1[i] - shape_margin[ids[1]])))})
            record["minimum_surface_separation_m"] = min((c["surface_separation_m"] for c in contacts), default=None)
            if index == contact_index or any(c["surface_separation_m"] <= 0. for c in contacts):
                record["contact_pairs"] = contacts
            if any(c["surface_separation_m"] <= 0. for c in contacts):
                first_surface_contact = record
        records.append(record)
        if first_surface_contact is not None:
            break
    result = {"physics_steps": robot.steps, "source": str(source), "records": records,
              "configured_radius_m": .25, "configured_offset_m": .18,
              "ceil_measured_radius_m": math.ceil(max(r["two_circle_radius_bound_m"] for r in records) / .05) * .05,
              "first_surface_contact": first_surface_contact,
              "claim": "Native Newton surface-separation helper distinguishes speculative contacts from touching/penetration. Geometry AABBs remove the native detection gap. Recorded poses only, not a universal articulation bound."}
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"first_speculative_contact_sim_s": rows[contact_index]["physics_time_s"],
                      "first_surface_contact_sim_s": None if first_surface_contact is None else first_surface_contact["physics_time_s"],
                      "radius_bound_m": result["ceil_measured_radius_m"],
                      "contact_pairs": records[-1].get("contact_pairs"), "physics_steps": robot.steps}, indent=2))


if __name__ == "__main__":
    main()

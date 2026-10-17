"""Flat continuous-physics control using existing Newton and Lite3 components."""
import hashlib
import json
import numpy as np
from pxr import UsdGeom
import newton
import warp as wp
from newton._src.sim.contacts import contact_surface_separation

from scene_assets import BASE, OfficialHuman
from robot_scene import Lite3Newton, StairRobot, fixed_frame_transform


class FlatStaticHuman(OfficialHuman):
    def __init__(self, out):
        super().__init__(out)
        vertices, _ = super().vertices(0., fixed_frame=0, fixed_root=(0., 0., 0.))
        faces, offset = [], 0
        for path, _, original, part in self.meshes:
            if UsdGeom.Imageable(self.stage.GetPrimAtPath(path)).ComputeVisibility() != "invisible":
                faces.append(part + offset)
            offset += len(original)
        self.visible_faces = np.concatenate(faces)
        selected = vertices[np.unique(self.visible_faces)]
        self.translation = np.r_[np.array([1.6, 0.]) - (selected[:, :2].min(axis=0) + selected[:, :2].max(axis=0)) / 2,
                                 -selected[:, 2].min()]

    def vertices(self, elapsed, **_):
        vertices, source = super().vertices(0., fixed_frame=0, fixed_root=(0., 0., 0.))
        vertices = (vertices + self.translation).astype(np.float32)
        return vertices, {"condition": "stationary_official_visible_mesh",
                          "clip": source["clip"], "frame": 0,
                          "vertices_sha256_scoring_only": hashlib.sha256(vertices.tobytes()).hexdigest()}


class FlatSceneRobot(StairRobot):
    def __init__(self, human, *, automatic_contact_capacity=True, obstacle_kind="human"):
        if obstacle_kind not in ("human", "box") or (obstacle_kind == "human" and human is None):
            raise ValueError("Expected an explicit human or box control scene")
        self.obstacle_kind = obstacle_kind
        self.contact_scoring = {"physics_substeps_checked": 0, "maximum_candidate_count": 0,
                                "touching_substeps": 0, "minimum_surface_separation_m": None}
        self.scenario = json.loads((BASE / "repairs/2026-09-26_generic_occupancy/flat_inputs_v2/scene.json").read_text())
        source = BASE / "inputs/sensor_rig/lite3_pro_sensor_rig_real_with_interface.urdf"
        self.sensor_mount = fixed_frame_transform(source, "mid360_scan_frame")
        vertices = human.vertices(0.)[0] if human is not None else None

        def add_scene(builder):
            floor = newton.Mesh(np.array([[-5.5,-5.5,0.],[5.5,-5.5,0.],[5.5,5.5,0.],[-5.5,5.5,0.]], dtype=np.float32),
                                np.array([0,1,2,0,2,3], dtype=np.int32), compute_inertia=False)
            self.building_shape = builder.add_shape_mesh(-1, mesh=floor,
                cfg=newton.ModelBuilder.ShapeConfig(mu=1.), label="flat_floor", color=(.58,.62,.67))
            for x,y,hx,hy in ((4.5,0.,.1,5.),(-4.5,0.,.1,5.),(0.,4.5,4.5,.1),(0.,-4.5,4.5,.1)):
                builder.add_shape_box(-1, xform=wp.transform(wp.vec3(x,y,1.5)), hx=hx,hy=hy,hz=1.5,
                                      cfg=newton.ModelBuilder.ShapeConfig(mu=1.), color=(.65,.67,.7))
            # Exactly the visible USD triangles are used for physical contact.
            # Rendering and geometric sensing use the same separately skinned
            # vertices, so this duplicate contact shape is not drawn/ray-tested.
            if obstacle_kind == "human":
                mesh = newton.Mesh(vertices, human.visible_faces.reshape(-1), compute_inertia=False)
                self.human_contact_shape = builder.add_shape_mesh(-1, mesh=mesh,
                    cfg=newton.ModelBuilder.ShapeConfig(mu=1., is_visible=False), label="official_human_exact_contact")
            else:
                self.human_contact_shape = builder.add_shape_box(-1,
                    xform=wp.transform(wp.vec3(1.6, 0., .35)), hx=.275, hy=.275, hz=.35,
                    cfg=newton.ModelBuilder.ShapeConfig(mu=1.), label="unclassified_box",
                    color=(.55,.32,.12))

        Lite3Newton.__init__(self, robot_source=source, scene_builder=add_scene,
                            spawn_xyz=(0.,0.,.35), spawn_yaw=0., newton_contacts=True,
                            automatic_contact_capacity=automatic_contact_capacity,
                            contact_observer=self._score_contacts)

    def _score_contacts(self, state, contacts):
        """Read-only scoring before every 1 ms solver step; never a control input."""
        metrics = self.contact_scoring
        metrics["physics_substeps_checked"] += 1
        count = int(contacts.rigid_contact_count.numpy()[0])
        first = contacts.rigid_contact_shape0.numpy()[:count]
        second = contacts.rigid_contact_shape1.numpy()[:count]
        selected = np.flatnonzero((first == self.human_contact_shape) | (second == self.human_contact_shape))
        metrics["maximum_candidate_count"] = max(metrics["maximum_candidate_count"], len(selected))
        if not len(selected):
            return
        body_ids = self.model.shape_body.numpy()
        shape_margin = self.model.shape_margin.numpy()
        body_q = state.body_q.numpy()
        p0, p1 = contacts.rigid_contact_point0.numpy(), contacts.rigid_contact_point1.numpy()
        normals = contacts.rigid_contact_normal.numpy()
        m0, m1 = contacts.rigid_contact_margin0.numpy(), contacts.rigid_contact_margin1.numpy()
        distances = []
        for i in selected:
            world = []
            for shape, point in ((first[i], p0[i]), (second[i], p1[i])):
                body = body_ids[shape]
                world.append(wp.vec3(*point) if body < 0 else wp.transform_point(wp.transform(*body_q[body]), wp.vec3(*point)))
            distances.append(float(contact_surface_separation(world[0], world[1], wp.vec3(*normals[i]),
                float(m0[i]-shape_margin[first[i]]), float(m1[i]-shape_margin[second[i]]))))
        nearest = min(distances)
        prior = metrics["minimum_surface_separation_m"]
        metrics["minimum_surface_separation_m"] = nearest if prior is None else min(prior, nearest)
        metrics["touching_substeps"] += int(nearest <= 0.)

    def actor_contact_count(self):
        count = int(self.contacts.rigid_contact_count.numpy()[0])
        first = self.contacts.rigid_contact_shape0.numpy()[:count]
        second = self.contacts.rigid_contact_shape1.numpy()[:count]
        return int(((first == self.human_contact_shape) | (second == self.human_contact_shape)).sum())

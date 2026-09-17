#!/usr/bin/env python3
"""Phase D.1b: stage audit of one InteriorAgent scene in Isaac Sim 5.1. No robot, no VLA, no ROS.

Runs inside `e01-walking-isaaclab:20260905` (driver: scripts/phase_d1_run_stage_audit.sh). Authorised by Dr Sun
2026-09-15 as the single D.1b Isaac start. Thresholds and validity controls are frozen in
phase_d/stage_audit_thresholds_d1b.json; this script records measurements and the in-run gate, and the host summary
adds the per-process GPU peak.

Order (each section records its own error and the next still runs, unless the scene or the simulation cannot start):
 1. static USD audit on a separate pxr stage: dependencies, layer units, objects and their physics authoring;
 2. Kit stage: SimulationContext (dt 0.005, render interval 4, one-robot PhysX buffers, scene queries on), the scene
    referenced at /World/Scene, the physics readout probe cube far from the scene, a level rig at pose A with the four
    D.0f cameras;
 3. sim.reset(); camera pose readback at A;
 4. PhysX scene queries: own-hit overlap per object, floor rays, footprint overlap and 16 rays per pose;
 5. physics: body poses through a rigid-body view (and get_rigidbody_transformation), 200 steps, poses again; the
    probe cube must fall for the readout to count;
 6. 120 render iterations at pose A (clock from the end of reset), move to B with readback, 120 at pose B;
 7. result JSON written atomically, then STAGE_AUDIT_COMPLETE (sha256 of the result). The exit code is not evidence.
"""
import argparse
import gc
import hashlib
import json
import math
import os
import pathlib
import sys
import time
import traceback


def utc():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def write_atomic(path, text):
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(text)
    os.replace(tmp, path)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--scene-usd', type=pathlib.Path, required=True)
    ap.add_argument('--episodes', type=pathlib.Path, required=True)
    ap.add_argument('--thresholds', type=pathlib.Path, required=True)
    ap.add_argument('--fusion-config', type=pathlib.Path, required=True)
    ap.add_argument('--chase-episode', type=pathlib.Path, required=True)
    ap.add_argument('--tools-dir', type=pathlib.Path, required=True)
    ap.add_argument('--output-dir', type=pathlib.Path, required=True)
    ap.add_argument('--device', default='cuda:0')
    args = ap.parse_args(argv)

    out = args.output_dir
    (out / 'frames').mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(args.tools_dir))
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import phase_b_camera_probe as probe
    import stage_audit_lib as lib

    thr_bytes = args.thresholds.read_bytes()
    thr = json.loads(thr_bytes)
    result = {'started_utc': utc(), 'thresholds_sha256': hashlib.sha256(thr_bytes).hexdigest(),
              'thresholds': thr, 'args': {k: str(v) for k, v in vars(args).items()}, 'marks': [],
              'static_errors': {}, 'section_errors': {}}
    t_origin = time.monotonic()
    marks_file = open(out / 'marks.jsonl', 'a', buffering=1)

    def mark(name, **extra):
        try:
            gpu = probe.gpu_used_mib()
        except Exception:  # noqa: BLE001 - a missing nvidia-smi must not stop the audit
            gpu = None
        row = {'mark': name, 'utc': utc(), 't_s': round(time.monotonic() - t_origin, 3), 'unix_s': time.time(),
               'device_used_mib': gpu, **extra}
        result['marks'].append(row)
        marks_file.write(json.dumps(row) + '\n')
        print('[stage_audit] {} t={:.1f}s gpu={}'.format(name, row['t_s'], gpu), flush=True)

    def save_result():
        write_atomic(out / 'stage_audit_result.json', json.dumps(result, indent=1, default=str) + '\n')

    from isaaclab.app import AppLauncher
    simulation_app = AppLauncher(headless=True, enable_cameras=True, device=args.device).app
    mark('app_started')
    state = {}
    try:
        run(args, thr, result, mark, save_result, probe, lib, out, state)
        result['finished_utc'] = utc()
        save_result()
        digest = hashlib.sha256((out / 'stage_audit_result.json').read_bytes()).hexdigest()
        (out / 'STAGE_AUDIT_COMPLETE').write_text(digest + '\n')
        mark('complete')
    except Exception:  # noqa: BLE001 - record, then close Kit rather than leave it holding the GPU
        result['error'] = traceback.format_exc()
        (out / 'STAGE_AUDIT_ERROR').write_text(result['error'])
        print(result['error'], flush=True)
        save_result()
    finally:
        marks_file.close()
        cleanup = shutdown(state)
        write_atomic(out / 'cleanup.json', json.dumps(cleanup, indent=1) + '\n')
        simulation_app.close()
    return 0


def shutdown(state):
    """The order Isaac Lab's ManagerBasedEnv.close uses: sensors first, then callbacks, then the context instance."""
    steps = []
    cams = state.get('cams')
    if cams is not None:
        try:
            cams.clear()
            state.pop('cams', None)
            gc.collect()
            steps.append('cameras deleted')
        except Exception as exc:  # noqa: BLE001
            steps.append('cameras: {!r}'.format(exc))
    sim = state.pop('sim', None)
    if sim is not None:
        for name in ('clear_all_callbacks', 'clear_instance'):
            try:
                getattr(sim, name)()
                steps.append(name)
            except Exception as exc:  # noqa: BLE001
                steps.append('{}: {!r}'.format(name, exc))
    return {'utc': utc(), 'steps': steps}


def run(args, thr, result, mark, save_result, probe, lib, out, state):
    import numpy as np
    import torch
    from PIL import Image
    from pxr import Usd, UsdGeom

    def section(store, name, fn):
        try:
            return fn()
        except Exception:  # noqa: BLE001 - one broken section must not cost the others
            store[name] = traceback.format_exc()
            print(store[name], flush=True)
            return None

    scene_root = args.scene_usd.parent
    episodes = json.loads(args.episodes.read_text())['episodes']

    # 1. Static audit on its own stage, so nothing Kit adds can hide a scene defect.
    static = result['static'] = {}
    serr = result['static_errors']
    dep = section(serr, 'dependencies', lambda: lib.dependency_report(str(args.scene_usd), str(scene_root)))
    if dep:
        static['dependencies'] = {k: v for k, v in dep.items() if k != 'layer_paths'}
        units = section(serr, 'layer_units', lambda: lib.layer_units(dep['layer_paths']))
        if units is not None:
            static['layer_units'] = units
    static_stage = section(serr, 'open_stage', lambda: Usd.Stage.Open(str(args.scene_usd)))
    rows = []
    static_root = '/Root'
    if static_stage:
        static['stage_meters_per_unit'] = UsdGeom.GetStageMetersPerUnit(static_stage)
        static['stage_up_axis'] = str(UsdGeom.GetStageUpAxis(static_stage))
        default = static_stage.GetDefaultPrim()
        static_root = static['default_prim'] = str(default.GetPath()) if default else None
        prims = section(serr, 'prims', lambda: lib.scene_prims_report(static_stage))
        if prims is not None:
            static['prims'] = prims
        rows = section(serr, 'objects', lambda: lib.object_inventory(static_stage, thr)) or []
        static['objects'] = rows
        static['excluded_children'] = section(serr, 'exclusions',
                                              lambda: lib.inventory_exclusions(static_stage, static_root))
        static['group_counts'] = _counts(r['group'] for r in rows)
        ext = lib.extents(rows) if rows else None
        static['extents'] = ext
        static['episode_points'] = lib.episode_points_inside(ext, episodes) if ext else None
    del static_stage
    save_result()
    mark('static_audit_done', objects=len(rows), layers=(dep or {}).get('layers'), assets=(dep or {}).get('assets'))

    # 2. Kit stage with the task's physics settings. A failure here ends the run (recorded by main).
    import isaaclab.sim as sim_utils
    from isaaclab.sensors import Camera, CameraCfg

    phys = thr['physics']
    vc = thr['validity_controls']
    serr2 = result['section_errors']
    sim = sim_utils.SimulationContext(sim_utils.SimulationCfg(
        dt=phys['physics_dt_s'], render_interval=thr['render']['physics_steps_per_render'], device=args.device,
        enable_scene_query_support=True, physx=sim_utils.PhysxCfg(**probe.PHYSX_BUFFER_PRESETS['one_env'])))
    state['sim'] = sim
    mark('sim_context')
    kit_root = '/World/Scene'
    sim_utils.create_prim(kit_root, 'Xform', usd_path=str(args.scene_usd))
    stage = sim_utils.get_current_stage()
    scene_prim = stage.GetPrimAtPath(kit_root)
    result['kit_stage'] = {
        'scene_prim_xform_ops': {op.GetOpName(): str(op.Get()) for op in UsdGeom.Xformable(scene_prim).GetOrderedXformOps()},
        'meters_per_unit': UsdGeom.GetStageMetersPerUnit(stage), 'up_axis': str(UsdGeom.GetStageUpAxis(stage)),
    }
    mark('scene_referenced')

    probe_cfg = vc['physics_readout_probe']
    probe_path = '/World/ReadoutProbe'

    def spawn_probe():
        size = float(probe_cfg['size_m'])
        cfg = sim_utils.CuboidCfg(size=(size, size, size), rigid_props=sim_utils.RigidBodyPropertiesCfg(),
                                  mass_props=sim_utils.MassPropertiesCfg(mass=float(probe_cfg['mass_kg'])),
                                  collision_props=sim_utils.CollisionPropertiesCfg())
        cfg.func(probe_path, cfg, translation=tuple(probe_cfg['position']))
        return True
    section(serr2, 'probe_spawn', spawn_probe)

    poses = thr['poses']
    height = poses['torso_height_m']
    fusion = json.loads(args.fusion_config.read_text())
    virtual = fusion['virtual']
    specs = [
        ('head_eval', {k: virtual[k] for k in ('width', 'height', 'hfov', 'pitch_up', 'pos')}, ['rgb', 'distance_to_image_plane']),
        ('chase', json.loads(args.chase_episode.read_text())['chase_camera'], ['rgb']),
        (fusion['head']['name'], fusion['head'], ['rgb']),
        (fusion['d435']['name'], fusion['d435'], ['rgb', 'distance_to_image_plane']),
    ]
    pose_a = poses['A']
    cams = state['cams'] = {}

    def spawn_cameras():
        qa = lib.yaw_quat_wxyz(pose_a['yaw_deg'])
        sim_utils.create_prim('/World/Rig', 'Xform', translation=(pose_a['xy'][0], pose_a['xy'][1], height), orientation=qa)
        record = {}
        for name, spec, data_types in specs:
            quat, _ = probe.camera_rotation(float(spec['pitch_up']))
            focal = probe.focal_for_hfov(float(spec['hfov']))
            cams[name] = Camera(CameraCfg(
                prim_path='/World/Rig/' + name, update_period=0.0,
                height=int(spec['height']), width=int(spec['width']), data_types=list(data_types),
                spawn=sim_utils.PinholeCameraCfg(focal_length=focal, horizontal_aperture=20.955, clipping_range=(0.05, 30.0)),
                offset=CameraCfg.OffsetCfg(pos=tuple(spec['pos']), rot=quat, convention='ros'),
            ))
            record[name] = {'width': spec['width'], 'height': spec['height'], 'hfov': spec['hfov'],
                            'pitch_up': spec['pitch_up'], 'pos': spec['pos'], 'data_types': data_types,
                            'focal_length_mm': focal, 'quat_wxyz_ros': quat}
        return record
    result['cameras'] = section(serr2, 'cameras', spawn_cameras)
    mark('cameras_spawned', cameras=len(cams))

    # Object inventory again on the Kit stage: the collision probes use these AABBs, and any difference from the
    # static stage (for example a units fix by the metrics assembler) shows up here.
    kit_rows = section(serr2, 'kit_inventory', lambda: lib.object_inventory_at(stage, kit_root, thr)) or []
    if kit_rows and rows:
        result['kit_stage']['objects_match_static'] = _compare_rows(rows, kit_rows, static_root, kit_root)
    save_result()

    t_reset = time.monotonic()
    sim.reset()
    t_reset_end = time.monotonic()
    kit_report = lib.scene_prims_report(stage)
    result['kit_stage'].update({'reset_s': round(t_reset_end - t_reset, 2), 'physics_scenes': kit_report['physics_scenes'],
                                'ground_planes': kit_report['ground_planes'], 'lights': kit_report['lights'],
                                'prims': kit_report['prims']})
    save_result()
    mark('sim_reset_done', reset_s=result['kit_stage']['reset_s'])

    max_readback = vc['camera_pose_readback']['max_error_m']

    def world_targets(pos, yaw_deg):
        q = lib.yaw_quat_wxyz(yaw_deg)
        return {name: dict(zip(('pos', 'quat_wxyz_ros'), lib.compose(pos, q, tuple(spec['pos']),
                                                                      probe.camera_rotation(float(spec['pitch_up']))[0])))
                for name, spec, _ in specs}

    def readback(targets):
        got = {}
        for name, cam in cams.items():
            positions, _ = cam._view.get_world_poses()
            got[name] = [float(v) for v in positions[0].tolist()]
        check = lib.readback_check(got, {n: t['pos'] for n, t in targets.items()}, max_readback)
        check['readback'] = got
        return check

    render = result['render'] = {'poses': {}, 'poses_check': {}}
    targets_a = world_targets((pose_a['xy'][0], pose_a['xy'][1], height), pose_a['yaw_deg'])
    render['poses']['A'] = {**pose_a, 'torso_z': height, 'cameras_world': targets_a}
    render['poses_check']['A'] = section(serr2, 'readback_A', lambda: readback(targets_a))

    # 4. PhysX scene queries.
    import carb
    from omni.physx import get_physx_interface, get_physx_scene_query_interface

    sq, px = get_physx_scene_query_interface(), get_physx_interface()
    ccfg, sub = thr['collision'], vc['overlap_subdivision']
    pad = ccfg['overlap_box_padding_m']
    identity = carb.Float4(0.0, 0.0, 0.0, 1.0)

    def own_query(center, half, owner):
        seen = {'hits': 0, 'own': None}

        def report(hit):
            seen['hits'] += 1
            path = str(hit.collision)
            if lib.is_under(path, owner):
                seen['own'] = path
                return False
            return True
        sq.overlap_box(carb.Float3(*half), carb.Float3(*center), identity, report, False)
        return seen['hits'], seen['own']

    def collect_overlap(center, half, quat_xyzw, cap=2048):
        hits = []

        def report(hit):
            hits.append(str(hit.collision))
            return len(hits) < cap
        sq.overlap_box(carb.Float3(*half), carb.Float3(*center), carb.Float4(*quat_xyzw), report, False)
        return hits, len(hits) >= cap

    def ray_all(origin, direction, length):
        hits = []

        def report(hit):
            hits.append({'collision': str(hit.collision), 'distance': float(hit.distance)})
            return True
        sq.raycast_all(carb.Float3(*origin), carb.Float3(*direction), length, report, bool(vc['floor_ray']['both_sides']))
        return hits

    def ray_closest(origin, direction, length, both):
        r = sq.raycast_closest(carb.Float3(*origin), carb.Float3(*direction), length, both)
        if not (r and bool(r.get('hit', bool(r.get('collision'))))):
            return {'hit': False}
        row = lib.object_for_path(str(r['collision']), kit_rows)
        return {'hit': True, 'distance': float(r['distance']), 'collision': str(r['collision']),
                'object': row['path'] if row else None, 'class': row['class'] if row else None}

    def collision_probes():
        col = result['collision'] = {'objects': [], 'floor_rays': {}, 'footprint_overlap': {}, 'horizontal_rays': {}}
        for row in kit_rows:
            base = {'path': row['path'], 'class': row['class'], 'group': row['group'],
                    'authored_colliders': len(row['colliders'])}
            if row['aabb_min'] is None:
                col['objects'].append({**base, 'effective': False, 'inconclusive': False, 'reason': 'empty bounds'})
                continue
            center = [(a + b) / 2 for a, b in zip(row['aabb_min'], row['aabb_max'])]
            half = [(b - a) / 2 + pad for a, b in zip(row['aabb_min'], row['aabb_max'])]
            q = lib.own_hit_query(own_query, center, half, row['path'], sub['trigger_hits'], sub['max_depth'], pad)
            col['objects'].append({**base, **q})
        for label in ('A', 'B'):
            pose = poses[label]
            x, y = pose['xy']
            z0 = ccfg['floor_ray_origin_z_m']
            floor = lib.floor_ray_summary(ray_all((x, y, z0), (0.0, 0.0, -1.0), ccfg['floor_ray_length_m']), kit_rows,
                                          z0, ccfg['floor_ray_must_hit_class'], ccfg['floor_hit_z_tolerance_m'])
            front = ray_closest((x, y, z0), (0.0, 0.0, -1.0), ccfg['floor_ray_length_m'], False)
            if front.get('hit'):
                front['z'] = z0 - front['distance']
            floor['closest_front_face'] = front
            col['floor_rays'][label] = floor
            yaw = math.radians(pose['yaw_deg'])
            q = lib.yaw_quat_wxyz(pose['yaw_deg'])
            hits, capped = collect_overlap((x + 0.005 * math.cos(yaw), y + 0.005 * math.sin(yaw), 0.25),
                                           (0.274 + 0.05, 0.182 + 0.05, 0.20), (q[1], q[2], q[3], q[0]))
            objs = {}
            for collision in hits:
                row = lib.object_for_path(collision, kit_rows)
                objs[row['path'] if row else collision] = row['class'] if row else None
            col['footprint_overlap'][label] = {
                'box': 'leg-width footprint (x -0.269..0.279, y +-0.182) padded 0.05 m, z 0.05-0.45 m', 'capped': capped,
                'objects': objs, 'non_floor': {k: v for k, v in objs.items() if (v or '').lower() != 'floor'}}
            col['horizontal_rays'][label] = [
                dict(ray_closest((x, y, 0.25), (math.cos(yaw + k * math.pi / 8), math.sin(yaw + k * math.pi / 8), 0.0),
                                 10.0, True), bearing_deg=round(math.degrees(k * math.pi / 8), 1)) for k in range(16)]
        return True
    section(serr2, 'collision', collision_probes)
    save_result()
    mark('collision_probes_done')

    # 5. Physics: does the static scene stay put, and can the readout see motion at all?
    dt = phys['physics_dt_s']
    need = int(math.ceil(phys['settle_seconds'] / dt - 1e-9))

    def physics_check():
        groups = {b['path']: {'object': row['path'], 'class': row['class'], 'group': row['group'],
                              'kinematic': b['kinematic']}
                  for row in kit_rows for b in row['rigid_bodies']}
        paths = sorted(groups) + [probe_path]
        views, view_error = [], None   # [(view, [prim paths in row order])]

        def make_view(pattern):
            view = sim.physics_sim_view.create_rigid_body_view(pattern)
            if view is None or getattr(view, '_backend', None) is None or view.count < 1:
                raise RuntimeError('no rigid bodies for {!r}'.format(pattern if isinstance(pattern, str) else len(pattern)))
            return view, [str(p) for p in view.prim_paths]

        try:
            views.append(make_view(paths))
        except Exception:  # noqa: BLE001 - one body PhysX rejected must not hide the others: one view per body
            view_error = traceback.format_exc()
            for p in paths:
                try:
                    views.append(make_view([p]))
                except Exception:  # noqa: BLE001 - that body is simply not found
                    pass

        def read_view():
            got = {}
            for view, view_paths in views:
                data = view.get_transforms()
                arr = (data.detach().cpu().numpy() if hasattr(data, 'detach') else np.asarray(data)).astype(np.float64)
                arr = arr.reshape(len(view_paths), 7)
                got.update({p: (arr[i, :3].tolist(), arr[i, 3:7].tolist()) for i, p in enumerate(view_paths)})
            return got

        def read_px():
            got = {}
            for p in paths:
                t = px.get_rigidbody_transformation(p)
                if t and t.get('ret_val'):
                    pos, rot = t['position'], t['rotation']
                    try:
                        got[p] = ([float(pos[0]), float(pos[1]), float(pos[2])],
                                  [float(rot[0]), float(rot[1]), float(rot[2]), float(rot[3])])
                    except TypeError:
                        got[p] = ([float(pos.x), float(pos.y), float(pos.z)],
                                  [float(rot.x), float(rot.y), float(rot.z), float(rot.w)])
            return got

        before = {'rigid_body_view': read_view(), 'get_rigidbody_transformation': read_px()}
        for _ in range(need):
            sim.step(render=False)
        after = {'rigid_body_view': read_view(), 'get_rigidbody_transformation': read_px()}
        probes = {name: lib.probe_drop(before[name], after[name], probe_path, probe_cfg) for name in before}
        chosen = next((name for name in ('rigid_body_view', 'get_rigidbody_transformation') if probes[name]['ok']), None)
        bodies_by = {name: lib.body_motion(before[name], after[name], groups) for name in before}
        result['physics'] = {
            'physics_steps': need, 'simulated_s': round(need * dt, 4), 'readout': chosen,
            'readout_probe': probes[chosen] if chosen else probes['rigid_body_view'], 'probes_by_readout': probes,
            'views': len(views), 'view_bodies': sum(len(vp) for _, vp in views), 'view_error': view_error,
            'bodies': bodies_by[chosen] if chosen else bodies_by['rigid_body_view'],
            'found_by_readout': {name: len(before[name]) for name in before},
        }
        return True
    section(serr2, 'physics', physics_check)
    save_result()
    mark('physics_checked', readout=(result.get('physics') or {}).get('readout'))

    # 6. Rendering.
    rcfg = thr['render']
    gated = set(thr['cameras']['gated'])
    steps_per_render = rcfg['physics_steps_per_render']

    def save_frames(label, tag):
        for name, cam in cams.items():
            data = cam.data.output
            Image.fromarray(data['rgb'][0][..., :3].to(torch.uint8).cpu().numpy()).save(
                out / 'frames' / '{}_{}_{}.png'.format(label, tag, name))
            if 'distance_to_image_plane' in data:
                np.save(out / 'frames' / '{}_{}_{}_depth.npy'.format(label, tag, name),
                        data['distance_to_image_plane'][0][..., 0].to(torch.float32).cpu().numpy())

    def render_pose(label, t0):
        rec = render[label] = {'iterations': 0, 'first_valid_iteration': None, 'first_valid_s': None,
                               'consecutive_valid_max': 0, 'clock_origin': 'end of sim.reset()' if label == 'A'
                               else 'after the cameras were moved', 'per_iteration': []}
        consecutive = 0
        for i in range(rcfg['max_render_iterations_per_pose']):
            for _ in range(steps_per_render):
                sim.step(render=False)
            sim.render()
            metrics, all_valid = {}, True
            for name, cam in cams.items():
                cam.update(dt=steps_per_render * dt)
                data = cam.data.output
                m = {'rgb': lib.rgb_metrics(data['rgb'][0][..., :3].cpu().numpy(), rcfg['rgb_dark_max_channel'])}
                ok = lib.rgb_valid(m['rgb'], rcfg)
                if 'distance_to_image_plane' in data:
                    m['depth'] = lib.depth_metrics(data['distance_to_image_plane'][0][..., 0].cpu().numpy())
                    if name in rcfg['depth_cameras']:
                        ok = ok and lib.depth_valid(m['depth'], rcfg)
                m['valid'] = ok
                metrics[name] = m
                if name in gated and not ok:
                    all_valid = False
            if not gated.issubset(metrics):
                all_valid = False
            elapsed = time.monotonic() - t0
            rec['iterations'] = i + 1
            rec['per_iteration'].append({'i': i, 's': round(elapsed, 3), 'valid': all_valid, 'metrics': metrics})
            if i == 0:
                save_frames(label, 'iter000')
            if all_valid:
                consecutive += 1
                if rec['first_valid_iteration'] is None:
                    rec['first_valid_iteration'], rec['first_valid_s'] = i, round(elapsed, 3)
                    save_frames(label, 'firstvalid')
            else:
                consecutive = 0
            rec['consecutive_valid_max'] = max(rec['consecutive_valid_max'], consecutive)
            if rec['first_valid_iteration'] is None and elapsed > rcfg['first_valid_frame_timeout_s']:
                rec['timed_out'] = True
                break
        save_frames(label, 'last')
        rec['last_metrics'] = rec['per_iteration'][-1]['metrics'] if rec['per_iteration'] else None
        rec['wall_s'] = round(time.monotonic() - t0, 2)
        return True

    if cams:
        if section(serr2, 'render_A', lambda: render_pose('A', t_reset_end)) is None:
            render.setdefault('A', {})['error'] = serr2.get('render_A')
        save_result()
        mark('render_A_done', first_valid_s=(render.get('A') or {}).get('first_valid_s'))

        pose_b = poses['B']
        targets_b = world_targets((pose_b['xy'][0], pose_b['xy'][1], height), pose_b['yaw_deg'])
        render['poses']['B'] = {**pose_b, 'torso_z': height, 'cameras_world': targets_b}

        def move_to_b():
            for name, cam in cams.items():
                pos, quat = targets_b[name]['pos'], targets_b[name]['quat_wxyz_ros']
                cam.set_world_poses(positions=torch.tensor([list(pos)], dtype=torch.float32, device=sim.device),
                                    orientations=torch.tensor([list(quat)], dtype=torch.float32, device=sim.device),
                                    convention='ros')
            sim.render()
            return readback(targets_b)
        render['poses_check']['B'] = section(serr2, 'move_to_B', move_to_b)
        t_b = time.monotonic()
        if section(serr2, 'render_B', lambda: render_pose('B', t_b)) is None:
            render.setdefault('B', {})['error'] = serr2.get('render_B')
        save_result()
        mark('render_B_done', first_valid_s=(render.get('B') or {}).get('first_valid_s'))

    result['gate_in_run'] = lib.evaluate(result, thr, isaac_peak_mib=None)


def _counts(values):
    out = {}
    for v in values:
        out[v] = out.get(v, 0) + 1
    return dict(sorted(out.items()))


def _compare_rows(rows, kit_rows, static_root, kit_root):
    by_path = {r['path'][len(static_root):]: r for r in rows}
    mismatches, worst = [], 0.0
    for k in kit_rows:
        s = by_path.get(k['path'][len(kit_root):])
        if s is None or s['class'] != k['class'] or s['group'] != k['group']:
            mismatches.append(k['path'])
            continue
        if s['aabb_min'] and k['aabb_min']:
            worst = max(worst, max(abs(a - b) for a, b in zip(s['aabb_min'] + s['aabb_max'], k['aabb_min'] + k['aabb_max'])))
    return {'static_objects': len(rows), 'kit_objects': len(kit_rows), 'mismatched': mismatches[:20],
            'max_aabb_difference_m': worst}


if __name__ == '__main__':
    sys.exit(main())

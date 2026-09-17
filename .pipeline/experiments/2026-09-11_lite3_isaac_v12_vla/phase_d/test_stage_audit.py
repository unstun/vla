#!/usr/bin/env python3
"""Local tests for the D.1b stage audit (no Kit, no GPU).

    <python with usd-core> phase_d/test_stage_audit.py     # USD inventory, geometry, gate
    <python with numpy>    phase_d/test_stage_audit.py     # image metrics, geometry, gate

Sections whose module is missing are skipped and reported, so run it under both interpreters. The synthetic scene
copies the InteriorAgent authoring pattern read from kujiale_0021/kujiale_0003 samples: per-object Xform with
semantics, kinematic RigidBodyAPI, CollisionAPI + MeshCollisionAPI on the Xform (not the Mesh), and a door whose
collidable group is a dynamic body nested under a kinematic one.
"""
import copy
import importlib.util
import json
import math
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'scripts'))
import stage_audit_lib as lib  # noqa: E402

THR = json.loads((HERE / 'stage_audit_thresholds_d1b.json').read_text())
RESULTS = []


def check(name, cond, detail=''):
    RESULTS.append((name, bool(cond)))
    print('{} {}{}'.format('PASS' if cond else 'FAIL', name, ' - ' + str(detail) if detail and not cond else ''))


# ---------------------------------------------------------------------------------------------------------------
def write_object(meshes_dir, name, cls, size, approx='convexHull', kinematic=True, door=False, mpu=1.0, semantics=True):
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics

    path = meshes_dir / (name + '.usd')
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageMetersPerUnit(stage, mpu)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    root = UsdGeom.Xform.Define(stage, '/Root')
    stage.SetDefaultPrim(root.GetPrim())
    UsdGeom.Scope.Define(stage, '/Root/Meshes')
    obj = UsdGeom.Xform.Define(stage, '/Root/Meshes/' + name).GetPrim()
    if semantics:
        obj.CreateAttribute('semantic:Semantics:params:semanticData', Sdf.ValueTypeNames.String).Set(cls)
        obj.CreateAttribute('semantic:Semantics:params:semanticType', Sdf.ValueTypeNames.String).Set('class')
    sx, sy, sz = size

    def box(prim_path):
        mesh = UsdGeom.Mesh.Define(stage, prim_path)
        pts = [Gf.Vec3f(x * sx / 2, y * sy / 2, (z + 1) * sz / 2) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
        mesh.CreatePointsAttr(pts)
        mesh.CreateFaceVertexCountsAttr([4] * 6)
        mesh.CreateFaceVertexIndicesAttr([0, 1, 3, 2, 4, 6, 7, 5, 0, 4, 5, 1, 2, 3, 7, 6, 0, 2, 6, 4, 1, 5, 7, 3])
        return mesh

    if door:
        UsdPhysics.RigidBodyAPI.Apply(obj).CreateKinematicEnabledAttr(True)
        group = UsdGeom.Xform.Define(stage, '/Root/Meshes/{}/group_0000'.format(name)).GetPrim()
        UsdPhysics.RigidBodyAPI.Apply(group)            # kinematicEnabled not authored: dynamic
        UsdPhysics.CollisionAPI.Apply(group)
        UsdPhysics.MeshCollisionAPI.Apply(group).CreateApproximationAttr('none')
        box('/Root/Meshes/{}/group_0000/leaf'.format(name))
    else:
        UsdPhysics.RigidBodyAPI.Apply(obj).CreateKinematicEnabledAttr(kinematic)
        UsdPhysics.CollisionAPI.Apply(obj)
        UsdPhysics.MeshCollisionAPI.Apply(obj).CreateApproximationAttr(approx)
        box('/Root/Meshes/{}/body'.format(name))
    stage.GetRootLayer().Save()
    return path


def build_scene(tmp, missing_texture=False, cm_layer=False):
    from pxr import Sdf, Usd, UsdGeom, UsdShade

    scene = tmp / 'kujiale_test'
    (scene / 'Meshes').mkdir(parents=True)
    (scene / 'Materials' / 'Textures').mkdir(parents=True)
    (scene / 'Materials' / 'Textures' / 'wood.png').write_bytes(b'\x89PNG fake')
    objects = [  # name, class, size, translate, extra
        ('floor_0000', 'floor', (8.0, 6.0, 0.02), (0.0, 0.0, -0.02), {'approx': 'none'}),
        ('wall_0000', 'wall', (8.0, 0.1, 2.8), (0.0, 3.0, 0.0), {'approx': 'none', 'mpu': 0.01 if cm_layer else 1.0}),
        ('sofa_0000', 'sofa', (2.0, 0.9, 0.8), (1.0, 1.0, 0.0), {'approx': 'convexDecomposition'}),
        ('table_0000', 'dining_table', (1.2, 0.8, 0.75), (-1.0, -1.0, 0.0), {}),
        ('lamp_0000', 'lamp', (0.2, 0.2, 0.4), (-1.0, -1.0, 0.75), {}),
        ('rug_0000', 'rug', (2.0, 1.5, 0.01), (0.0, 0.0, 0.0), {}),
        ('curtain_0000', 'curtain', (1.5, 0.05, 2.5), (3.0, 2.9, 0.0), {}),
        ('door_0000', 'door', (0.9, 0.05, 2.1), (-3.0, 3.0, 0.0), {'door': True}),
        ('doorsill_0000', 'doorsill', (0.9, 0.1, 0.02), (-3.0, 3.0, 0.0), {'semantics': False}),
    ]
    for name, cls, size, _, extra in objects:
        write_object(scene / 'Meshes', name, cls, size, **extra)
    stage = Usd.Stage.CreateNew(str(scene / 'kujiale_test.usda'))
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    root = UsdGeom.Xform.Define(stage, '/Root')
    stage.SetDefaultPrim(root.GetPrim())
    UsdGeom.Scope.Define(stage, '/Root/Meshes')
    UsdGeom.Scope.Define(stage, '/Root/Meshes/living_1')
    for name, _, _, translate, _ in objects:
        prim = UsdGeom.Xform.Define(stage, '/Root/Meshes/living_1/' + name)
        prim.GetPrim().GetReferences().AddReference('./Meshes/{}.usd'.format(name))
        prim.AddTranslateOp().Set(translate)
    # Excluded by the default predicate: a deactivated object and an over-only (never defined) object.
    inactive = UsdGeom.Xform.Define(stage, '/Root/Meshes/living_1/wall_0001')
    inactive.GetPrim().GetReferences().AddReference('./Meshes/wall_0000.usd')
    inactive.GetPrim().SetActive(False)
    stage.OverridePrim('/Root/Meshes/living_1/ghost_0000')
    UsdGeom.Scope.Define(stage, '/Root/Looks')
    mat = UsdShade.Material.Define(stage, '/Root/Looks/wood')
    shader = UsdShade.Shader.Define(stage, '/Root/Looks/wood/Shader')
    shader.GetPrim().CreateAttribute('info:mdl:sourceAsset', Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath('OmniUe4Base.mdl'))
    unreal = UsdShade.Shader.Define(stage, '/Root/Looks/wood/UnrealShader')
    unreal.GetPrim().CreateAttribute('info:unreal:sourceAsset', Sdf.ValueTypeNames.Asset).Set(
        Sdf.AssetPath('/Engine/EngineMaterials/WorldGridMaterial.WorldGridMaterial'))
    tex = './Materials/Textures/missing.png' if missing_texture else './Materials/Textures/wood.png'
    shader.CreateInput('diffuse_texture', Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath(tex))
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), 'out')
    stage.GetRootLayer().Save()
    return scene


def usd_tests():
    try:
        import pxr  # noqa: F401
    except ImportError:
        print('SKIP usd tests (no pxr)')
        return
    from pxr import Usd, UsdGeom, UsdPhysics

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = pathlib.Path(tmpdir).resolve()
        scene = build_scene(tmp / 'good')
        usda = scene / 'kujiale_test.usda'
        dep = lib.dependency_report(str(usda), str(scene))
        check('dep: no local unresolved in the good scene', dep['local_unresolved'] == [], dep['local_unresolved'])
        check('dep: bare MDL module listed, not counted', 'OmniUe4Base.mdl' in dep['bare_mdl_unresolved'], dep)
        check('dep: Unreal content path on info:unreal:sourceAsset reported, not counted',
              dep['unreal_metadata_unresolved_count'] == 1
              and dep['unreal_metadata_examples'] == ['/Engine/EngineMaterials/WorldGridMaterial.WorldGridMaterial'], dep)
        check('dep: nothing non-local', dep['non_local'] == [], dep['non_local'])
        units = lib.layer_units(dep['layer_paths'])
        check('units: 10 USD layers read', len(units) == 10, len(units))
        check('units: all metres and Z', all(u['meters_per_unit'] == 1.0 and u['up_axis'] == 'Z' for u in units), units)

        bad = build_scene(tmp / 'bad', missing_texture=True, cm_layer=True)
        dep_bad = lib.dependency_report(str(bad / 'kujiale_test.usda'), str(bad))
        check('dep: missing texture counted as local unresolved',
              any(u.endswith('missing.png') for u in dep_bad['local_unresolved']), dep_bad['local_unresolved'])
        units_bad = lib.layer_units(dep_bad['layer_paths'])
        check('units: centimetre wall layer detected',
              any(u['meters_per_unit'] == 0.01 and u['layer'].endswith('wall_0000.usd') for u in units_bad), units_bad)

        stage = Usd.Stage.Open(str(usda))
        rows = lib.object_inventory(stage, THR)
        by = {r['name']: r for r in rows}
        expect = {'floor_0000': 'floor', 'wall_0000': 'wall', 'sofa_0000': 'floor_standing_obstacle',
                  'table_0000': 'floor_standing_obstacle', 'lamp_0000': 'other', 'rug_0000': 'other',
                  'curtain_0000': 'soft_exempt', 'door_0000': 'opening', 'doorsill_0000': 'opening'}
        check('inventory: groups', {n: by[n]['group'] for n in expect} == expect, {n: by[n]['group'] for n in by})
        check('inventory: class from semantics and from name',
              by['table_0000']['class'] == 'dining_table' and by['table_0000']['class_source'] == 'semantics'
              and by['doorsill_0000']['class'] == 'doorsill' and by['doorsill_0000']['class_source'] == 'name')
        check('inventory: collider on an Xform is not a Gprim',
              by['sofa_0000']['colliders'] and not by['sofa_0000']['colliders'][0]['gprim']
              and by['sofa_0000']['colliders'][0]['approximation'] == 'convexDecomposition', by['sofa_0000']['colliders'])
        door = by['door_0000']
        check('inventory: door nested dynamic body found (object file defaultPrim /Root composes under the object)',
              door['nested_rigid_bodies'] == [door['path'] + '/Meshes/door_0000/group_0000']
              and [b['kinematic'] for b in door['rigid_bodies']] == [True, False], door)
        check('inventory: lamp AABB sits on the table', abs(by['lamp_0000']['aabb_min'][2] - 0.75) < 1e-6,
              by['lamp_0000']['aabb_min'])
        check('inventory: triangles counted', by['sofa_0000']['meshes'] == 1 and by['sofa_0000']['triangles'] == 12)
        check('inventory: inactive and over-only children are not objects',
              len(rows) == 9 and 'wall_0001' not in by and 'ghost_0000' not in by, sorted(by))
        excluded = {e['path'].rsplit('/', 1)[-1]: e for e in lib.inventory_exclusions(stage, '/Root')}
        check('inventory: exclusions listed with the reason',
              set(excluded) == {'wall_0001', 'ghost_0000'} and excluded['wall_0001']['active'] is False
              and excluded['ghost_0000']['defined'] is False, excluded)
        check('dep: file: scheme stripped before comparing', lib.norm_path('file:///workspace/a.usd') == '/workspace/a.usd'
              and lib.norm_path('file:/workspace/a.usd') == '/workspace/a.usd' and lib.norm_path('/x') == '/x')

        ext = lib.extents(rows)
        check('extents: floor XY box', ext['floor_xy_min'] == [-4.0, -3.0] and ext['floor_xy_max'] == [4.0, 3.0], ext)
        episodes = [{'episode_id': 1, 'start_position': [0.5, 0.5, 0], 'goals': {'position': [3.9, -2.9, 0]}},
                    {'episode_id': 2, 'start_position': [4.5, 0.0, 0], 'goals': {'position': [0.0, 0.0, 0]}}]
        inside = lib.episode_points_inside(ext, episodes)
        check('extents: outside point found', inside['inside_fraction'] == 0.75 and inside['outside'][0][1] == 2, inside)
        prims = lib.scene_prims_report(stage)
        check('prims: no physics scene, no ground plane', prims['physics_scenes'] == [] and prims['ground_planes'] == [])

        # The same scene referenced under /World/Scene (as in Kit): same objects, same bounds.
        kit = Usd.Stage.CreateInMemory()
        UsdGeom.SetStageMetersPerUnit(kit, 1.0)
        UsdGeom.SetStageUpAxis(kit, UsdGeom.Tokens.z)
        UsdGeom.Xform.Define(kit, '/World')
        kit.DefinePrim('/World/Scene', 'Xform').GetReferences().AddReference(str(usda))
        UsdPhysics.Scene.Define(kit, '/physicsScene')
        kit_rows = lib.object_inventory_at(kit, '/World/Scene', THR)
        spec = importlib.util.spec_from_file_location('stage_audit', HERE / 'stage_audit.py')
        sa = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sa)
        cmp_rows = sa._compare_rows(rows, kit_rows, '/Root', '/World/Scene')
        check('kit copy: objects and bounds match', cmp_rows['mismatched'] == [] and cmp_rows['max_aabb_difference_m'] < 1e-9
              and cmp_rows['kit_objects'] == 9, cmp_rows)
        check('kit copy: one physics scene', len(lib.scene_prims_report(kit)['physics_scenes']) == 1)
        hit = lib.object_for_path('/World/Scene/Meshes/living_1/door_0000/group_0000/leaf', kit_rows)
        check('object_for_path: longest prefix', hit and hit['name'] == 'door_0000')
        check('object_for_path: no false prefix match',
              lib.object_for_path('/World/Scene/Meshes/living_1/sofa_00001', kit_rows) is None)


# ---------------------------------------------------------------------------------------------------------------
def geometry_tests():
    q = lib.yaw_quat_wxyz(90.0)
    pos, quat = lib.compose((1.0, 2.0, 0.3), q, (0.27, 0.0, 0.05), (1.0, 0.0, 0.0, 0.0))
    check('compose: forward offset turns with yaw 90', all(abs(a - b) < 1e-9 for a, b in zip(pos, (1.0, 2.27, 0.35))), pos)
    check('compose: yaw composes', abs(lib.quat_angle_deg((q[1], q[2], q[3], q[0]), (quat[1], quat[2], quat[3], quat[0]))) < 1e-6)
    check('angle: 0.1 deg detected', abs(lib.quat_angle_deg((0, 0, 0, 1), (0, 0, math.sin(math.radians(0.05)),
                                                                           math.cos(math.radians(0.05)))) - 0.1) < 1e-6)
    import struct
    f32 = lambda q: tuple(struct.unpack('4f', struct.pack('4f', *q)))   # noqa: E731
    q_yaw = (0.0, 0.0, math.sin(math.radians(17.3)), math.cos(math.radians(17.3)))
    worst = max(lib.quat_angle_deg(f32(q_yaw), f32(q_yaw)), lib.quat_angle_deg(f32((0.5, 0.5, 0.5, 0.5)), f32((0.5, 0.5, 0.5, 0.5))))
    check('angle: identical float32 quaternions give ~0 (not the 0.047 deg float noise)', worst < 1e-3, worst)


def decision_tests():
    """Scene-query and physics decisions with fake queries: the logic that runs after sim.reset() in Kit."""
    sub = THR['validity_controls']['overlap_subdivision']
    owner = '/World/Scene/Meshes/r/cabinet_0000'

    def fake(own_after, foreign, cap=None, own_region=None):
        calls = []

        def query(center, half, own):
            calls.append((tuple(center), tuple(half)))
            inside = own_region is None or all(abs(c - o) <= h for c, o, h in zip(center, own_region, half))
            hits = 0
            for i in range(foreign + 1):
                if cap is not None and hits >= cap:
                    return hits, None
                hits += 1
                if inside and i == own_after:
                    return hits, own + '/Meshes/cabinet_0000'
            return hits, None
        return query, calls

    query, calls = fake(own_after=600, foreign=700)
    r = lib.own_hit_query(query, (0, 0, 0.5), (1, 1, 0.5), owner, sub['trigger_hits'], sub['max_depth'])
    check('overlap: own hit after 600 foreign hits is found (no cap in our callback)',
          r['effective'] and r['queries'] == 1 and r['max_hits'] == 601, r)
    # Spatial fake: 125 foreign colliders on a grid inside the box, the own collider at one point; every query reports
    # the foreign colliders inside its box first and stops at an internal cap of 64 (the worst case for us).
    grid = [(-0.8 + 0.4 * i, -0.8 + 0.4 * j, 0.1 + 0.2 * k) for i in range(5) for j in range(5) for k in range(5)]
    own_point = (0.55, 0.45, 0.72)

    def spatial(center, half, own):
        def inside(p):
            return all(abs(pc - cc) <= hh for pc, cc, hh in zip(p, center, half))
        hits = sum(1 for p in grid if inside(p))
        if hits >= 64:
            return 64, None
        return (hits + 1, own + '/Meshes/cabinet_0000') if inside(own_point) else (hits, None)
    r = lib.own_hit_query(spatial, (0, 0, 0.5), (1, 1, 0.5), owner, sub['trigger_hits'], sub['max_depth'])
    check('overlap: a capped query is subdivided until the own collider shows',
          r['effective'] and 1 < r['queries'] <= 9 and not r['inconclusive'], r)
    query, calls = fake(own_after=10 ** 6, foreign=100, cap=64)
    r = lib.own_hit_query(query, (0, 0, 0.5), (1, 1, 0.5), owner, sub['trigger_hits'], sub['max_depth'])
    check('overlap: capped at every depth and no own hit is inconclusive, not effective',
          not r['effective'] and r['inconclusive'] and r['queries'] == 1 + 8 + 64, r)
    query, calls = fake(own_after=10 ** 6, foreign=10)
    r = lib.own_hit_query(query, (0, 0, 0.5), (1, 1, 0.5), owner, sub['trigger_hits'], sub['max_depth'])
    check('overlap: few hits and none own is simply not effective', not r['effective'] and not r['inconclusive']
          and r['queries'] == 1, r)
    check('overlap: prefix match needs a path boundary',
          lib.is_under(owner + '/Meshes/x', owner) and not lib.is_under(owner + '1/Meshes/x', owner))

    rows = [{'path': '/W/Meshes/r/floor_0000', 'class': 'floor'}, {'path': '/W/Meshes/r/carpet_0000', 'class': 'carpet'},
            {'path': '/W/Meshes/r/table_0000', 'class': 'table'}]
    hits = [{'collision': '/W/Meshes/r/floor_0000/Meshes/floor_0000', 'distance': 1.0},
            {'collision': '/W/Meshes/r/carpet_0000/Meshes/carpet_0000', 'distance': 0.99}]
    s = lib.floor_ray_summary(hits, rows, 1.0, 'floor', 0.02)
    check('floor ray: a carpet above the floor does not hide the floor collider',
          s['closest']['class'] == 'carpet' and s['floor_hit']['class'] == 'floor' and abs(s['floor_hit']['z']) < 1e-9, s)
    s = lib.floor_ray_summary([hits[1]], rows, 1.0, 'floor', 0.02)
    check('floor ray: only a carpet, no floor collider: no floor hit', s['floor_hit'] is None, s)
    s = lib.floor_ray_summary([{'collision': '/W/Meshes/r/floor_0000', 'distance': 1.3}], rows, 1.0, 'Floor', 0.02)
    check('floor ray: floor 0.30 m low is outside the tolerance, class match ignores case',
          s['floor_hit'] is None and s['nearest_floor_class_hit']['class'] == 'floor', s)

    probe_cfg = THR['validity_controls']['physics_readout_probe']
    before = {'/p': ([200.0, 200.0, 10.0], [0, 0, 0, 1]), '/b': ([1.0, 2.0, 0.0], [0, 0, 0, 1])}
    fell = {'/p': ([200.0, 200.0, 10.0 - 4.93], [0, 0, 0, 1]), '/b': ([1.0, 2.0, 0.0], [0, 0, 0, 1])}
    stale = {'/p': ([200.0, 200.0, 10.0], [0, 0, 0, 1]), '/b': ([1.0, 2.0, 0.0], [0, 0, 0, 1])}
    check('probe: a 4.93 m drop validates the readout', lib.probe_drop(before, fell, '/p', probe_cfg)['ok'])
    check('probe: a stale readout (no drop) is invalid', not lib.probe_drop(before, stale, '/p', probe_cfg)['ok'])
    check('probe: missing probe is invalid', not lib.probe_drop({}, {}, '/p', probe_cfg)['ok'])
    motion = lib.body_motion(before, {'/b': ([1.0, 2.002, 0.0], [0, 0, 0, 1])},
                             {'/b': {'group': 'wall'}, '/gone': {'group': 'wall'}})
    by = {m['path']: m for m in motion}
    check('motion: displacement measured, missing body not found',
          abs(by['/b']['displacement_m'] - 0.002) < 1e-9 and by['/gone']['found'] is False, motion)

    max_err = THR['validity_controls']['camera_pose_readback']['max_error_m']
    targets = {'head_eval': (1.0, 2.0, 0.35), 'chase': (0.0, 0.0, 1.2)}
    check('readback: 27 mm bias passes', lib.readback_check({'head_eval': (1.0, 2.027, 0.35), 'chase': (0, 0, 1.2)},
                                                            targets, max_err)['ok'])
    check('readback: camera left at pose A fails', not lib.readback_check(
        {'head_eval': (-1.8, 3.9, 0.35), 'chase': (0, 0, 1.2)}, targets, max_err)['ok'])
    check('readback: a missing camera fails', not lib.readback_check({'head_eval': (1.0, 2.0, 0.35)}, targets, max_err)['ok'])
    try:
        import phase_b_camera_probe as probe
    except Exception as exc:  # noqa: BLE001
        print('SKIP camera composition test ({})'.format(exc))
        return
    for yaw, pitch in ((-18.413, 16.7), (90.0, -20.0), (0.0, 0.0)):
        cam_q, _ = probe.camera_rotation(pitch)
        _, world_q = lib.compose((0, 0, 0), lib.yaw_quat_wxyz(yaw), (0, 0, 0), cam_q)
        optical_z = lib.quat_rotate(world_q, (0.0, 0.0, 1.0))
        want = (math.cos(math.radians(pitch)) * math.cos(math.radians(yaw)),
                math.cos(math.radians(pitch)) * math.sin(math.radians(yaw)), math.sin(math.radians(pitch)))
        check('camera world pose: optical axis for yaw {} pitch {}'.format(yaw, pitch),
              all(abs(a - b) < 1e-6 for a, b in zip(optical_z, want)), (optical_z, want))


def image_tests():
    try:
        import numpy as np
    except ImportError:
        print('SKIP image tests (no numpy)')
        return
    r = THR['render']
    black = np.zeros((72, 128, 3), np.uint8)
    m = lib.rgb_metrics(black, r['rgb_dark_max_channel'])
    check('rgb: black frame invalid', not lib.rgb_valid(m, r) and m['dark_fraction'] == 1.0, m)
    rng = np.random.default_rng(0)
    noisy = rng.integers(20, 230, size=(72, 128, 3), dtype=np.uint8)
    m = lib.rgb_metrics(noisy, r['rgb_dark_max_channel'])
    check('rgb: textured frame valid', lib.rgb_valid(m, r), m)
    flat = np.full((72, 128, 3), 128, np.uint8)
    check('rgb: flat grey frame invalid (std)', not lib.rgb_valid(lib.rgb_metrics(flat, r['rgb_dark_max_channel']), r))
    half = noisy.copy()
    half[:40] = 0
    check('rgb: over half dark invalid', not lib.rgb_valid(lib.rgb_metrics(half, r['rgb_dark_max_channel']), r))
    depth = np.full((48, 64), 2.5, np.float32)
    depth[:10] = np.inf
    dm = lib.depth_metrics(depth)
    check('depth: valid fraction and median', abs(dm['valid_fraction'] - 38 / 48) < 1e-6 and dm['median_m'] == 2.5, dm)
    check('depth: passes', lib.depth_valid(dm, r))
    depth[:30] = np.inf
    check('depth: too many holes fails', not lib.depth_valid(lib.depth_metrics(depth), r))
    check('depth: all-inf gives no median', lib.depth_metrics(np.full((4, 4), np.inf))['median_m'] is None)


# ---------------------------------------------------------------------------------------------------------------
def fake_result():
    good_units = [{'layer': 'a.usda', 'meters_per_unit': 1.0, 'up_axis': 'Z'}]
    objects = [{'path': '/W/f', 'class': 'floor', 'group': 'floor', 'effective': True},
               {'path': '/W/w', 'class': 'wall', 'group': 'wall', 'effective': True},
               {'path': '/W/s', 'class': 'sofa', 'group': 'floor_standing_obstacle', 'effective': True},
               {'path': '/W/c', 'class': 'curtain', 'group': 'soft_exempt', 'effective': False},
               {'path': '/W/d', 'class': 'door', 'group': 'opening', 'effective': False}]
    body = {'path': '/W/s', 'group': 'floor_standing_obstacle', 'found': True, 'displacement_m': 0.0, 'rotation_deg': 0.0}
    frames = {'iterations': 120, 'first_valid_iteration': 0, 'first_valid_s': 1.0, 'consecutive_valid_max': 120}
    return {
        'static': {'dependencies': {'local_unresolved': [], 'non_local': [], 'bare_mdl_unresolved': ['OmniUe4Base.mdl']},
                   'layer_units': good_units, 'prims': {'physics_scenes': []},
                   'extents': {'floor_xy_min': [-5, -3], 'floor_xy_max': [8, 12], 'scene_z': [-0.1, 2.9]},
                   'episode_points': {'points': 66, 'outside': [], 'inside_fraction': 1.0}},
        'kit_stage': {'physics_scenes': ['/physicsScene'], 'ground_planes': []},
        'collision': {'objects': objects,
                      'floor_rays': {'A': {'floor_hit': {'class': 'floor', 'z': 0.0}},
                                     'B': {'floor_hit': {'class': 'floor', 'z': 0.001}}}},
        'physics': {'simulated_s': 1.0, 'readout': 'rigid_body_view', 'readout_probe': {'ok': True, 'drop_m': 4.93},
                    'bodies': [body, {'path': '/W/d/g', 'group': 'opening', 'found': True,
                                      'displacement_m': 0.3, 'rotation_deg': 40.0}]},
        'render': {'A': dict(frames), 'B': dict(frames), 'poses_check': {'A': {'ok': True}, 'B': {'ok': True}}},
    }


def gate_tests():
    ok = lib.evaluate(fake_result(), THR, isaac_peak_mib=4800)
    check('gate: good run admitted', ok['admit_to_d1c'] and ok['failed'] == [], ok['failed'])
    check('gate: moving door is reported, not gated',
          [c for c in ok['checks'] if c['check'] == 'P1_static_scene_stays_put'][0]['detail']['reported_moving'])

    def failed_with(mutate, peak=4800):
        res = fake_result()
        mutate(res)
        return lib.evaluate(res, THR, isaac_peak_mib=peak)

    cases = {
        'S1_local_paths_resolve': lambda r: r['static']['dependencies'].update(local_unresolved=['./Materials/x.png']),
        'S2_metres_and_z_up': lambda r: r['static']['layer_units'].append({'layer': 'b.usd', 'meters_per_unit': 0.01, 'up_axis': 'Z'}),
        'S3_one_physics_scene': lambda r: r['kit_stage'].update(physics_scenes=['/physicsScene', '/Root/PhysicsScene']),
        'S4_no_extra_ground_plane': lambda r: r['kit_stage'].update(ground_planes=['/World/GroundPlane']),
        'S5_metre_scale_and_episode_frame': lambda r: r['static']['extents'].update(floor_xy_max=[-4.9, -2.9]),
        'C2_colliders_effective_in_physx': lambda r: r['collision']['objects'][2].update(effective=False),
        'C3_floor_under_both_poses': lambda r: r['collision']['floor_rays']['B']['floor_hit'].update(z=0.05),
        'P1_static_scene_stays_put': lambda r: r['physics']['bodies'][0].update(displacement_m=0.002),
        'R_frames_valid_pose_B': lambda r: r['render'].update(B={'error': 'set_world_poses failed'}),
    }
    cases_more = {
        'C3 no floor hit at A': ('C3_floor_under_both_poses', lambda r: r['collision']['floor_rays']['A'].update(floor_hit=None)),
        'P1 readout probe did not fall': ('P1_static_scene_stays_put', lambda r: r['physics'].update(
            readout=None, readout_probe={'ok': False, 'drop_m': 0.0})),
        'P1 NaN rotation': ('P1_static_scene_stays_put', lambda r: r['physics']['bodies'][0].update(rotation_deg=float('nan'))),
        'R pose B cameras not moved': ('R_frames_valid_pose_B', lambda r: r['render']['poses_check'].update(B={'ok': False})),
        'R pose A readback missing': ('R_frames_valid_pose_A', lambda r: r['render']['poses_check'].pop('A')),
    }
    for label, (name, mutate) in cases_more.items():
        res = failed_with(mutate)
        check('gate: {} fails {} alone'.format(label, name), res['failed'] == [name], res['failed'])
    for name, mutate in cases.items():
        res = failed_with(mutate)
        check('gate: {} fails alone'.format(name), res['failed'] == [name] and not res['admit_to_d1c'], res['failed'])
    res = failed_with(lambda r: r['collision']['objects'].pop(1))
    check('gate: missing wall group fails C2', res['failed'] == ['C2_colliders_effective_in_physx'], res['failed'])
    res = failed_with(lambda r: r['physics']['bodies'][0].update(found=False))
    check('gate: no gated body found in PhysX fails P1', res['failed'] == ['P1_static_scene_stays_put'], res['failed'])
    res = failed_with(lambda r: r['render']['A'].update(first_valid_s=601.0))
    check('gate: first valid frame after 600 s fails', res['failed'] == ['R_frames_valid_pose_A'], res['failed'])
    res = failed_with(lambda r: r['render']['A'].update(consecutive_valid_max=2))
    check('gate: two consecutive valid frames fail', res['failed'] == ['R_frames_valid_pose_A'], res['failed'])
    res = failed_with(lambda r: None, peak=5462)
    check('gate: 5462 MiB is PASS', res['admit_to_d1c'] and res['checks'][-1]['verdict'] == 'PASS')
    res = failed_with(lambda r: None, peak=5463)
    check('gate: 5463 MiB is MARGINAL and still admitted', res['admit_to_d1c'] and res['checks'][-1]['verdict'] == 'MARGINAL'
          and res['checks'][-1]['detail']['projected_d1d_device_peak_mib'] == 17728 + 5463 + 300 + 50)
    res = failed_with(lambda r: None, peak=6487)
    check('gate: 6487 MiB is FAIL', not res['admit_to_d1c'] and res['failed'] == ['M1_isaac_gpu_peak'])
    res = lib.evaluate(fake_result(), THR, isaac_peak_mib=None)
    check('gate: missing GPU peak blocks admission', not res['admit_to_d1c'] and 'M1_isaac_gpu_peak' in res['failed'])
    empty = lib.evaluate({}, THR, isaac_peak_mib=4000)
    check('gate: empty record fails every non-memory check', len(empty['failed']) == 10, empty['failed'])


SKIPPED = []

if __name__ == '__main__':
    for section, needs in ((usd_tests, 'pxr'), (geometry_tests, None), (decision_tests, None), (image_tests, 'numpy'),
                           (gate_tests, None)):
        if needs and importlib.util.find_spec(needs) is None:
            SKIPPED.append(section.__name__)
        section()
    failed = [n for n, ok in RESULTS if not ok]
    print('{}/{} checks passed; skipped sections: {}'.format(len(RESULTS) - len(failed), len(RESULTS),
                                                              ', '.join(SKIPPED) or 'none'))
    sys.exit(1 if failed else 0)

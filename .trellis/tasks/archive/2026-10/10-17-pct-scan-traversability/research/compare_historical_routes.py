"""Read closed captures only; compare PCT geometry without advancing physics.

Run with the Newton worker Python on gpu5070ti. Output is compact and returns
to the local task. No planner setting or frozen experiment is modified.
"""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json
import math
import subprocess
import zipfile
import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def region(points):
    return ((points[:, 0] >= 6.7) & (points[:, 0] <= 8.8) &
            (points[:, 1] >= -4.8) & (points[:, 1] <= -2.8) &
            (points[:, 2] >= 1.3) & (points[:, 2] <= 2.3))


def xyz(pose):
    return [pose['position'][key] for key in ('x', 'y', 'z')]


def yaw(pose):
    q=pose['orientation']
    return math.atan2(2*(q['w']*q['z']+q['x']*q['y']), 1-2*(q['y']**2+q['z']**2))


def interpolate(points, poses):
    result = []
    for index, (a, b) in enumerate(zip(points[:-1], points[1:])):
        count = max(1, int(np.ceil(np.linalg.norm(b-a)/.025)))
        angle=yaw(poses[index]);delta=math.remainder(yaw(poses[index+1])-angle, 2*math.pi)
        result.extend([*(a+u*(b-a)), angle+u*delta] for u in np.arange(count)/count)
    result.append([*points[-1], yaw(poses[-1])])
    return np.asarray(result)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('/data/sun/vla_mppi_20261009'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    records, arrays = {}, {}
    for version in ('v210', 'v212', 'v217', 'v219'):
        run = f'{version}_linux_full_attempt01'
        directory = args.root/'trials'/run/'runs'/run
        archive = directory/'raw_capture.zip'
        with zipfile.ZipFile(archive) as handle:
            routes, bodies = [], []
            observations_hash = hashlib.sha256()
            with handle.open('artifacts/reactive_observations.jsonl') as stream:
                for line in stream:
                    observations_hash.update(line)
                    event = json.loads(line)
                    if event['event'] == 'pct_route':
                        poses = [p['pose'] for p in event['data']['poses']]
                        points = np.asarray([xyz(p) for p in poses])
                        samples = interpolate(points, poses)
                        geometry = hashlib.sha256(json.dumps(poses, sort_keys=True).encode()).hexdigest()
                        routes.append(dict(time=event['clock_ns']*1e-9, poses=poses,
                                           points=points, samples=samples, geometry=geometry))
                    elif event['event'] == 'body_pose_observer':
                        pose=event['data']['pose']['pose']
                        bodies.append([event['clock_ns']*1e-9, *xyz(pose), yaw(pose)])
            body = np.asarray(bodies)
            route_report = []
            for route in routes:
                selected = route['samples'][region(route['samples'])]
                sections = {}
                if len(selected):
                    for x in (7., 7.25, 7.5, 7.75, 8., 8.25):
                        p = selected[np.argmin(abs(selected[:, 0]-x))]
                        if abs(p[0]-x) < .04:
                            sections[str(x)] = p[:3].tolist()
                route_report.append(dict(physics_s=route['time'], pose_count=len(route['poses']),
                                         geometry_sha256=route['geometry'], stair_sections=sections))
            distances = []
            stair_body = body[(body[:, 0] >= 45.) & (body[:, 0] <= 55.) & region(body[:, 1:])]
            for row in stair_body:
                active = [r for r in routes if r['time'] <= row[0]]
                if active:
                    delta = active[-1]['samples'][:, :2]-row[1:3]
                    distances.append(float(np.sqrt(np.sum(delta*delta, axis=1)).min()))
            active45 = [r for r in routes if r['time'] <= 45.][-1]
            active50 = [r for r in routes if r['time'] <= 50.][-1]
            arrays[version] = dict(initial=routes[0]['samples'], active45=active45['samples'],
                                   active50=active50['samples'], body=stair_body)
            records[version] = dict(
                archive=str(archive), archive_bytes=archive.stat().st_size,
                observations_sha256=observations_hash.hexdigest(),
                deliveries=route_report, deliveries_45_55=sum(45 <= r['time'] <= 55 for r in routes),
                unique_geometries=len(Counter(r['geometry'] for r in routes)),
                active45_first_pose=active45['points'][0].tolist(),
                active45_delivered_s=active45['time'],
                body_to_active_reference_xy_m=dict(samples=len(distances),
                    median=float(np.median(distances)) if distances else None,
                    p95=float(np.quantile(distances, .95)) if distances else None,
                    maximum=max(distances) if distances else None))

    maps = {}
    for name in ('command_continuity_v206_20261015', 'event_planning_v212',
                 'starvation_recovery_v217', 'starvation_recovery_v219'):
        folder = args.root/name/'fixtures/building'
        if not folder.exists():
            continue
        manifest = json.loads((folder/'terrain.json').read_text())
        maps[name] = dict(terrain_manifest_sha256=sha(folder/'terrain.json'),
                         pct_sha256=sha(folder/manifest['pct']['file']),
                         gap_sha256=sha(folder/manifest['support_gap']['file']))

    # Quantify only extra support-gap clearance using the original native
    # predicate. This is not a wall-distance or full live-collision assessment.
    helper=args.root/'global_coverage_v135_foxy/query_mask'
    mask=args.root/'starvation_recovery_v219/fixtures/building/support_gap.txt'
    probes, spans, cursor=[], {}, 0
    for version, items in arrays.items():
        for key, points in items.items():
            points=points[:, 1:] if key=='body' else points
            points=points[region(points)]
            if not len(points):
                continue
            centers=[]
            for sign in (-1., 1.):
                center=points[:, :3].copy()
                center[:, 0]+=sign*.18*np.cos(points[:, 3])
                center[:, 1]+=sign*.18*np.sin(points[:, 3])
                center[:, 2]-=.3
                centers.append(center)
            batch=np.concatenate(centers)
            probes.append(batch);spans[f'{version}_{key}']=(cursor, len(points));cursor+=len(batch)
    query=np.concatenate(probes).astype('<f8').tobytes()
    margins={}
    for radius in (.35, .4, .45, .5, .6):
        result=subprocess.run([str(helper),str(mask),'10479033888964413526',str(radius),
                               '/dev/stdin','/dev/stdout'],input=query,check=True,capture_output=True,timeout=45)
        blocked=np.frombuffer(result.stdout,dtype=np.uint8)
        assert len(blocked)==cursor
        for key,(offset,count) in spans.items():
            hit=blocked[offset:offset+count] | blocked[offset+count:offset+2*count]
            margins.setdefault(key, {'samples':count,'blocked_fraction_by_added_margin_m':{}})[
                'blocked_fraction_by_added_margin_m'][f'{radius-.35:.2f}']=float(np.mean(hit))
    report = dict(physics_steps=0, source_sha256=sha(Path(__file__)),
                  maps=maps, versions=records,
                  support_gap_clearance=dict(helper_sha256=sha(helper),mask_sha256=sha(mask),
                      cylinder_offset_m=.18,baseline_cylinder_radius_m=.35,body_ground_offset_m=.3,
                      results=margins,
                      meaning='Fraction rejected after adding a soft diagnostic margin to the unchanged native gap-mask radius. This is not solid-obstacle clearance.'),
                  initial_geometry_equal=len({r['deliveries'][0]['geometry_sha256'] for r in records.values()}) == 1,
                  limits='Route/body geometry and static input identity only. Body-to-route distance is not obstacle clearance and is not a causal replay.')
    (args.output/'historical_route_comparison.json').write_text(json.dumps(report, indent=2)+'\n')

    surface = np.fromfile(args.root/'starvation_recovery_v219/fixtures/building/surface.f32', dtype='<f4').reshape(-1, 4)
    surface = surface[(surface[:, 0] > 6.3) & (surface[:, 0] < 9.) &
                      (surface[:, 1] > -5.) & (surface[:, 1] < -2.5) &
                      (surface[:, 2] > .8) & (surface[:, 2] < 2.4)]
    compact = {'surface': surface}
    for version, items in arrays.items():
        for key, points in items.items():
            if key != 'body':
                mask = ((points[:, 0] > 6.3) & (points[:, 0] < 9.) &
                        (points[:, 1] > -5.) & (points[:, 1] < -2.5))
                points = points[mask]
            compact[f'{version}_{key}'] = points
    np.savez_compressed(args.output/'plot_data.npz', **compact)
    print(json.dumps(dict(initial_geometry_equal=report['initial_geometry_equal'], maps=maps,
                         versions={v:{k:val for k,val in r.items() if k not in ('deliveries','archive')}
                                   for v,r in records.items()}), indent=2))


if __name__ == '__main__':
    main()

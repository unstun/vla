"""Extract actually published clouds from the immutable v110 physical capture."""
from pathlib import Path
import argparse, hashlib, io, json, shutil, zipfile
import numpy as np
from scipy.spatial.transform import Rotation

def main():
    parser=argparse.ArgumentParser();parser.add_argument('capture',type=Path);parser.add_argument('support',type=Path);parser.add_argument('output',type=Path);a=parser.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((a.capture/'raw_capture_manifest.json').read_text())['members']
    archive=zipfile.ZipFile(a.capture/'raw_capture.zip')
    def raw(name):
        p=a.capture/name;data=p.read_bytes() if p.exists() else archive.read(name)
        if name in manifest:assert hashlib.sha256(data).hexdigest()==manifest[name]['sha256'],name
        return data
    published={r['timestamp_ns']:r for r in map(json.loads,raw('bridge_scan_audit.jsonl').splitlines())}
    rows=[r for r in map(json.loads,raw('sensor.jsonl').splitlines()) if r['stamp_ns'] in published]
    for name in ['navigation.f32','surface.f32','physical_floor.f32']:shutil.copyfile(a.support/name,a.output/name)
    listing=[];errors=[]
    for index,row in enumerate(rows):
        data=raw(row['file'])
        with np.load(io.BytesIO(data)) as arrays:points=arrays['sensor_points'];world=arrays['world_points']
        b=row['body_sensor'];q=b['sensor_quaternion'];reconstructed=Rotation.from_quat(q[1:]+q[:1]).apply(points)+b['sensor_position']
        error=float(np.max(np.linalg.norm(reconstructed-world,axis=1)));assert error<1e-4;errors.append(error)
        audit=published[row['stamp_ns']];assert len(points)==audit['raw_point_count']==audit['planning_point_count']
        files=[f'{index:04d}.body',f'{index:04d}.sensor',f'{index:04d}.cloud']
        for name,prefix in zip(files[:2],['','sensor_']):
            q=b[prefix+'quaternion'];(a.output/name).write_text(' '.join(format(float(x),'.17g') for x in b[prefix+'position']+q[1:]+q[:1])+'\n')
        (a.output/files[2]).write_bytes(points.astype('<f4').tobytes());listing.append(f'{index} {row["stamp_ns"]} '+' '.join(files))
    (a.output/'scans.txt').write_text('\n'.join(listing)+'\n')
    result={'source_capture':str(a.capture),'source_zip_sha256':hashlib.sha256((a.capture/'raw_capture.zip').read_bytes()).hexdigest(),
      'scans':len(rows),'maximum_sensor_world_reconstruction_error_m':max(errors),'all_points_equal_original_published_counts':True,
      'scope':'intrinsic ordered cloud processing; original captured body/sensor pose per cloud; no physics or higher-rate body stream',
      'files':{str(p.relative_to(a.output)):hashlib.sha256(p.read_bytes()).hexdigest() for p in a.output.iterdir() if p.is_file()}}
    (a.output/'identity.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='files'}))
if __name__=='__main__':main()

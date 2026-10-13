"""Apply the actual native veto to an isolated PCT traversal-cost copy."""
from pathlib import Path
import hashlib,json,pickle,subprocess
import numpy as np
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1];TASK=Path('/data/sun/vla_mppi_20261009')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    out=TASK/'global_coverage_v135_foxy';out.mkdir(exist_ok=False)
    original=BASE/'inputs/new_building.pickle';assert sha(original)=='ab5499ff100fe233f6cfabb59ce7592290cddd042c92ead5e37e9e2b593d24da'
    source=pickle.loads(original.read_bytes());data=source['data'];coords=np.nonzero(np.isfinite(data[3]))
    center=np.asarray(source['center']);offset=np.array(data.shape[2:])//2
    xyz=np.c_[(coords[1]-offset[0])*.1+center[0],(coords[2]-offset[1])*.1+center[1],data[3][coords]].astype('<f8')
    xyz.tofile(out/'queries.f64')
    subprocess.run(['g++','-std=c++17','-O2','-I'+str(HERE.parent/'v134/src/plan_env/include'),str(HERE/'query_mask.cpp'),'-o',str(out/'query_mask')],check=True)
    coverage=json.loads((HERE.parent/'v134/support_coverage_input.json').read_text())
    mask=TASK/Path(coverage['file']).relative_to('/task');assert sha(mask)==coverage['sha256']
    subprocess.run([str(out/'query_mask'),str(mask),coverage['fnv64'],'.53',str(out/'queries.f64'),str(out/'blocked.u8')],check=True)
    blocked=np.fromfile(out/'blocked.u8',dtype=np.uint8).astype(bool);assert len(blocked)==len(xyz)
    copy=data.copy();before=copy[0].astype(np.float32);indices=tuple(c[blocked] for c in coords)
    copy[0][indices]=np.maximum(copy[0][indices],50)
    delta=copy[0].astype(np.float32)-before
    gx=np.zeros_like(delta);gy=np.zeros_like(delta)
    gx[:,1:-1,:]=delta[:,2:,:]-delta[:,:-2,:]
    gy[:,:,1:-1]=delta[:,:,2:]-delta[:,:,:-2]
    copy[1]=(copy[1].astype(np.float32)+gx).astype(data.dtype)
    copy[2]=(copy[2].astype(np.float32)+gy).astype(data.dtype)
    assert np.array_equal(data[3:],copy[3:],equal_nan=True)
    assert np.all(copy[0]>=data[0])
    result=dict(source,data=copy)
    with (out/'map.pickle').open('wb') as f:pickle.dump(result,f)
    report={'source_map_sha256':sha(original),'coverage_sha256':sha(mask),'map_sha256':sha(out/'map.pickle'),
        'radius_m':.53,'cells_considered':len(xyz),'vetoed':int(blocked.sum()),'newly_blocked_traversable':int(((before<=20)&(copy[0]>20)).sum()),
        'elevations_unchanged':True,'costs_never_lowered':True,'generator_sha256':sha(Path(__file__)),
        'query_helper_sha256':sha(HERE/'query_mask.cpp')}
    (out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()

"""Read-only identity gate for the actual installed native execution copy."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def verify():
    m=json.loads((HERE/'manifest.json').read_text())
    assert m['frozen']
    assert sha(HERE.parent/'v272/manifest.json')==m['parent_manifest_sha256']
    for rel,h in m['source_files'].items():assert sha(HERE/rel)==h,rel
    for name,h in m['inventories'].items():
        p=HERE/'results'/(name+'.json');assert sha(p)==h,name
        root=BASE/('source_free_index_v278/evaluation' if name=='evaluator_files' else 'source_free_index_v278/native')
        for rel,value in json.loads(p.read_text()).items():assert sha(root/rel)==value,rel
    p=BASE/'repo/.pipeline/experiments/2026-09-26_newton_macos_policy/policy/policy_stateless_h10.onnx'
    assert sha(p)==m['policy_sha256']
    return dict(passed=True,native_manifest_sha256=sha(HERE/'manifest.json'),
                policy_sha256=m['policy_sha256'],hard_radius_m=.35,sensor_period_s=.1)
if __name__=='__main__':print(json.dumps(verify()),flush=True)

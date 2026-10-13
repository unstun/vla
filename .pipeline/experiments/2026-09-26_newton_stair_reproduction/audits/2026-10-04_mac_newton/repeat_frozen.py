"""Repeat unchanged v68 with a prepared cache; never refreeze existing source."""
from pathlib import Path
import hashlib,importlib.util,json,shutil,sys

HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1];ROOT=BASE.parents[2]
VERSION=BASE/'versions/v68'
manifest=json.loads((VERSION/'manifest.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert all(sha(ROOT/name)==h and sha(ROOT/manifest['snapshot_locations'][name])==h
           for name,h in manifest['source_files'].items())
sys.path.insert(0,str(VERSION))
spec=importlib.util.spec_from_file_location('frozen_v68_trial',VERSION/'mac_trial.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
def verified_existing_manifest(receipt):
    assert sha(receipt)==manifest['mac_build_receipt_sha256']
    assert json.loads(receipt.read_text())['native_source_sha256']==manifest['native_source_sha256']
    return manifest
module.freeze=verified_existing_manifest
original_mkdtemp=module.tempfile.mkdtemp
cache=Path('/private/tmp/vla_newton_v68_mahxfuzu/runtime/warp-cache/1.17.0')
assert cache.is_dir()
def prepared_root(*args,**kwargs):
    root=Path(original_mkdtemp(*args,**kwargs))
    shutil.copytree(cache,root/'runtime/warp-cache/1.17.0')
    (root/'cache_preparation.json').write_text(json.dumps({
        'source':str(cache),'copied_before_simulator_process':True,
        'physics_or_sensor_period_change':False,'wrapper_sha256':sha(Path(__file__)),
    },indent=2)+'\n')
    return str(root)
module.tempfile.mkdtemp=prepared_root
sys.argv=[str(VERSION/'mac_trial.py'),'--attempt','2','--trials','1','--seconds','90',
    '--reuse-workspace','/private/tmp/vla_newton_v67__xr5p654/native_workspace']
module.main()

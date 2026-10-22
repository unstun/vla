"""Unscored adapter parity, installed identity and positive/stale controls."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess,sys,time
from run_matrix import summarize

HERE=Path(__file__).resolve().parent
OUT=Path('/data/sun/vla_mppi_20261009/generalization_v242')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    old=OUT/'development/historical_baseline/shared_admitted.csv'
    new=OUT/'development/historical_adapter/route.csv'
    assert old.read_bytes()==new.read_bytes()
    linked=(OUT/'linked_libraries.txt').read_text()
    assert 'libscan_native_core.so => /work/install/scan_planner/lib/' in linked
    spec=importlib.util.spec_from_file_location('parent_identity',HERE.parent/'v241/launch.py')
    parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
    identity=parent.verify_sources()
    dest=OUT/'development/A02cold02';dest.mkdir(exist_ok=False)
    began=time.monotonic()
    with (dest/'stdout.log').open('x') as log:
        code=subprocess.run([sys.executable,str(HERE/'build_remote.py'),'/evaluation/cases/A02',
            '/evaluation/development/A02cold02'],stdout=log,stderr=subprocess.STDOUT,timeout=120).returncode
    result=summarize(dest,code,time.monotonic()-began)
    assert result['end_to_end_pass'],result
    record=dict(passed=True,historical_component_byte_equal=True,historical_route_sha256=sha(old),
        parent_identity=identity,cold_case=result,probe_binary_sha256=sha(OUT/'build/native_probe'),
        linked_libraries_sha256=sha(OUT/'linked_libraries.txt'),physics_steps=0,
        controls='Original rebuilt v232 probe vs adapter, same legacy component parameters; actual runtime matrix uses explicit yaw, .3 reference height and native inferred terminal heading.')
    (OUT/'adapter_controls.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({k:record[k] for k in ('passed','historical_component_byte_equal','historical_route_sha256','physics_steps')}))

if __name__=='__main__':main()

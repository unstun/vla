"""Read-only container binding check; no planning call or physics step."""
from common import *
from probe import base_command
import subprocess
binding=verify_inputs();R=HERE/'results';R.mkdir(exist_ok=True)
script='test -x /evaluation/build/native_probe && test -f /work/fixtures/source_surface.env && test -f /work/fixtures/source_triangles.f64 && test -f /task/space_coverage_v257/cases/A04/endpoints.txt && test -f /task/mesh_benchmark_v262/cases/CU06/endpoints.txt'
with (R/'bindings_preflight.log').open('x') as log:
    result=subprocess.run(base_command('v273-bindings-preflight')+['-c',script],stdout=log,stderr=subprocess.STDOUT)
assert result.returncode==0
write(R/'bindings_preflight.json',dict(passed=True,native_manifest_sha256=binding['native']['native_manifest_sha256'],source_inputs_verified=True,planning_calls=0,physics_steps=0))
print(json.dumps(dict(passed=True,planning_calls=0,physics_steps=0)),flush=True)

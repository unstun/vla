"""The original v286 ABI/interface gate with current rebuild prefixes."""
from pathlib import Path

ROOT = Path('/home/ubuntu/sun/vla_v286_20261020')
FROZEN = ROOT / 'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v286/preflight.py'
source = FROZEN.read_text()
old = "reference = json.loads((HERE.parent/'v237/results/preflight01/native_preflight.json').read_text())['packages']"
assert source.count(old) == 1
source = source.replace(old, 'reference = {}')
old = "expected = '/work/install/'+name if name in rebuilt else '/task/physical_traversability_v248/native/install/lite3_nav2_bridge' if name=='lite3_nav2_bridge' else '/task/callback_failure_v232/install/'+name if name in inherited else reference[name]"
assert source.count(old) == 1
source = source.replace(old, "expected = '/task/bridge248/native/install/lite3_nav2_bridge' if name=='lite3_nav2_bridge' else '/work/install/'+name")
source = source.replace('/task/physical_traversability_v248/native/', '/task/bridge248/native/')
namespace = dict(__file__=str(FROZEN), __name__='new_host_original_preflight')
exec(compile(source, str(FROZEN), 'exec'), namespace)
